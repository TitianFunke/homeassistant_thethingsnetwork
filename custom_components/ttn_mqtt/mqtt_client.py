"""MQTT-Anbindung an einen The Things Stack / The Things Network Broker.

Der Client abonniert das Uplink-Topic der Anwendung, parst die Nachrichten
und stellt die dekodierten Messwerte + Funk-Metadaten für die Sensor-Plattform
bereit. Neue Geräte und neue Messwerte werden automatisch erkannt.
"""

from __future__ import annotations

import base64
import json
import logging
import ssl
from dataclasses import dataclass, field
from typing import Any

import paho.mqtt.client as mqtt

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import SIGNAL_NEW_ENTITY, SIGNAL_UPDATE

_LOGGER = logging.getLogger(__name__)


@dataclass
class TTNValue:
    """Ein einzelner Messwert eines Geräts."""

    value: Any
    unit: str | None = None
    last_update: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class TTNDevice:
    """Metadaten eines LoRaWAN-Geräts aus dem Uplink."""

    device_id: str
    dev_eui: str | None = None
    join_eui: str | None = None
    dev_addr: str | None = None


def _new_paho_client(client_id: str) -> mqtt.Client:
    """paho-mqtt Client erzeugen – kompatibel zu v1.x und v2.x."""
    try:
        # paho-mqtt >= 2.0
        return mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,  # type: ignore[attr-defined]
            client_id=client_id,
        )
    except AttributeError:
        # paho-mqtt < 2.0
        return mqtt.Client(client_id=client_id)


def _best_metadata(uplink: dict[str, Any]) -> dict[str, Any]:
    """Beste Gateway-Metadaten (höchstes RSSI) aus rx_metadata ziehen."""
    rx = uplink.get("rx_metadata") or []
    if not rx:
        return {}
    best = max(rx, key=lambda g: g.get("rssi", -9999))
    return best


class TTNMqttClient:
    """Kapselt Verbindung, Subscription und Nachrichten-Parsing."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        host: str,
        port: int,
        application_id: str,
        tenant_id: str,
        api_key: str,
        use_tls: bool,
    ) -> None:
        self.hass = hass
        self.entry_id = entry_id
        self._host = host
        self._port = port
        self._application_id = application_id
        self._tenant_id = tenant_id
        self._api_key = api_key
        self._use_tls = use_tls

        # Username-Format: {app-id}@{tenant-id}; ohne Tenant nur {app-id}.
        self._username = (
            f"{application_id}@{tenant_id}" if tenant_id else application_id
        )
        self._topic = f"v3/{self._username}/devices/+/up"

        self.devices: dict[str, TTNDevice] = {}
        # (device_id, key) -> TTNValue
        self.values: dict[tuple[str, str], TTNValue] = {}

        self._client: mqtt.Client | None = None
        self.connected = False

    # -- Öffentliche API ---------------------------------------------------

    def connect(self) -> None:
        """Blockierend verbinden (im Executor aufrufen)."""
        client = _new_paho_client(client_id=f"ha-{self.entry_id[:8]}")
        client.username_pw_set(self._username, self._api_key)
        if self._use_tls:
            client.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLS)
        client.on_connect = self._on_connect
        client.on_disconnect = self._on_disconnect
        client.on_message = self._on_message
        client.connect(self._host, self._port, keepalive=60)
        client.loop_start()
        self._client = client

    def disconnect(self) -> None:
        """Verbindung sauber trennen (im Executor aufrufen)."""
        if self._client is not None:
            try:
                self._client.loop_stop()
                self._client.disconnect()
            except Exception:  # noqa: BLE001
                _LOGGER.debug("Fehler beim Trennen der MQTT-Verbindung", exc_info=True)
            self._client = None
        self.connected = False

    @property
    def application_id(self) -> str:
        """Application-ID dieser Verbindung."""
        return self._application_id

    def knows_device(self, device_id: str) -> bool:
        """True, wenn von diesem Gerät bereits ein Uplink empfangen wurde."""
        return device_id in self.devices

    def publish_downlink(
        self,
        device_id: str,
        f_port: int,
        frm_payload_b64: str,
        confirmed: bool = False,
        priority: str = "NORMAL",
    ) -> None:
        """Downlink in die Warteschlange des Geräts legen (im Executor aufrufen).

        Nutzt das TTS-Topic .../down/push. frm_payload_b64 ist bereits Base64.
        """
        if self._client is None:
            raise RuntimeError("MQTT-Client nicht verbunden")
        topic = f"v3/{self._username}/devices/{device_id}/down/push"
        message = {
            "downlinks": [
                {
                    "f_port": f_port,
                    "frm_payload": frm_payload_b64,
                    "priority": priority,
                    "confirmed": confirmed,
                }
            ]
        }
        info = self._client.publish(topic, json.dumps(message), qos=0)
        # Fehler früh sichtbar machen (z. B. nicht verbunden).
        rc = getattr(info, "rc", 0)
        if rc != 0:
            raise RuntimeError(f"Downlink-Publish fehlgeschlagen (rc={rc})")
        _LOGGER.debug("Downlink an %s (f_port=%s) gesendet", device_id, f_port)

    # -- paho Callbacks (laufen im MQTT-Netzwerk-Thread!) ------------------

    def _on_connect(self, client, userdata, flags, rc, properties=None) -> None:
        is_failure = getattr(rc, "is_failure", None)
        ok = (is_failure is False) or (is_failure is None and rc == 0)
        if ok:
            self.connected = True
            client.subscribe(self._topic, qos=0)
            _LOGGER.info("Mit TTS verbunden, abonniert: %s", self._topic)
        else:
            self.connected = False
            _LOGGER.error("TTS-Verbindung fehlgeschlagen: %s", rc)

    def _on_disconnect(self, client, userdata, *args) -> None:
        self.connected = False
        _LOGGER.warning("TTS-Verbindung getrennt – automatischer Reconnect läuft")

    def _on_message(self, client, userdata, msg) -> None:
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            _LOGGER.debug("Ungültige MQTT-Nachricht verworfen")
            return
        # In den HA-Event-Loop marshallen (Thread-Wechsel!).
        self.hass.add_job(self._process_message, payload)

    # -- Verarbeitung im HA-Event-Loop -------------------------------------

    @callback
    def _process_message(self, payload: dict[str, Any]) -> None:
        ids = payload.get("end_device_ids") or {}
        device_id = ids.get("device_id")
        if not device_id:
            return

        if device_id not in self.devices:
            self.devices[device_id] = TTNDevice(
                device_id=device_id,
                dev_eui=ids.get("dev_eui"),
                join_eui=ids.get("join_eui"),
                dev_addr=ids.get("dev_addr"),
            )

        uplink = payload.get("uplink_message") or {}
        received_at = payload.get("received_at") or uplink.get("received_at")

        readings: dict[str, Any] = {}

        # 1) Dekodierte Nutzdaten (Payload-Formatter des Geräts)
        decoded = uplink.get("decoded_payload") or {}
        for key, value in _flatten(decoded):
            readings[key] = value

        # 2) Funk-Metadaten / Diagnose
        best = _best_metadata(uplink)
        if "rssi" in best:
            readings["rssi"] = best.get("rssi")
        if "snr" in best:
            readings["snr"] = best.get("snr")
        if uplink.get("f_cnt") is not None:
            readings["f_cnt"] = uplink.get("f_cnt")
        if uplink.get("f_port") is not None:
            readings["f_port"] = uplink.get("f_port")

        settings = uplink.get("settings") or {}
        lora = ((settings.get("data_rate") or {}).get("lora")) or {}
        if lora.get("spreading_factor") is not None:
            readings["spreading_factor"] = lora.get("spreading_factor")
        if lora.get("bandwidth") is not None:
            readings["bandwidth"] = lora.get("bandwidth")
        if settings.get("frequency") is not None:
            try:
                readings["frequency"] = int(settings.get("frequency"))
            except (TypeError, ValueError):
                readings["frequency"] = settings.get("frequency")

        rx = uplink.get("rx_metadata") or []
        readings["gateway_count"] = len(rx)

        airtime = uplink.get("consumed_airtime")
        if airtime is not None:
            readings["consumed_airtime"] = _parse_airtime(airtime)

        # Werte speichern + neue Entities melden
        new_entities: list[tuple[str, str]] = []
        for key, value in readings.items():
            ekey = (device_id, key)
            is_new = ekey not in self.values
            self.values[ekey] = TTNValue(value=value, last_update=received_at)
            if is_new:
                new_entities.append(ekey)

        for ekey in new_entities:
            async_dispatcher_send(
                self.hass, f"{SIGNAL_NEW_ENTITY}_{self.entry_id}", ekey[0], ekey[1]
            )

        async_dispatcher_send(
            self.hass, f"{SIGNAL_UPDATE}_{self.entry_id}_{device_id}"
        )


def _flatten(obj: Any, prefix: str = "") -> list[tuple[str, Any]]:
    """decoded_payload flach klopfen; nur skalare Werte behalten."""
    out: list[tuple[str, Any]] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            name = f"{prefix}_{k}" if prefix else str(k)
            out.extend(_flatten(v, name))
    elif isinstance(obj, (int, float, str, bool)) or obj is None:
        out.append((prefix, obj))
    # Listen und verschachtelte Objekte ohne Skalar werden ignoriert.
    return out


def _parse_airtime(value: Any) -> float | Any:
    """Airtime wie '0.061696s' -> Sekunden als float."""
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str) and value.endswith("s"):
        try:
            return float(value[:-1])
        except ValueError:
            return value
    return value
