"""Services der The Things Stack (MQTT) Integration.

Aktuell: ttn_mqtt.send_downlink — legt einen Downlink in die Warteschlange
eines Geräts. Payload wird als Hex-String angegeben (LoRaWAN-üblich) oder
alternativ direkt als Base64.
"""

from __future__ import annotations

import base64
import binascii
import logging

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN
from .mqtt_client import TTNMqttClient

_LOGGER = logging.getLogger(__name__)

SERVICE_SEND_DOWNLINK = "send_downlink"

ATTR_DEVICE_ID = "device_id"
ATTR_F_PORT = "f_port"
ATTR_PAYLOAD = "payload"
ATTR_PAYLOAD_BASE64 = "payload_base64"
ATTR_CONFIRMED = "confirmed"
ATTR_PRIORITY = "priority"
ATTR_APPLICATION_ID = "application_id"

PRIORITIES = [
    "LOWEST",
    "LOW",
    "BELOW_NORMAL",
    "NORMAL",
    "ABOVE_NORMAL",
    "HIGH",
    "HIGHEST",
]

SEND_DOWNLINK_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE_ID): cv.string,
        vol.Required(ATTR_F_PORT): vol.All(vol.Coerce(int), vol.Range(min=1, max=223)),
        vol.Optional(ATTR_PAYLOAD): cv.string,
        vol.Optional(ATTR_PAYLOAD_BASE64): cv.string,
        vol.Optional(ATTR_CONFIRMED, default=False): cv.boolean,
        vol.Optional(ATTR_PRIORITY, default="NORMAL"): vol.In(PRIORITIES),
        vol.Optional(ATTR_APPLICATION_ID): cv.string,
    }
)


def _hex_to_base64(hex_str: str) -> str:
    """Hex-String ('0A 0F' / '0x0A0F' / '0a0f') -> Base64."""
    clean = hex_str.strip().lower().replace("0x", "").replace(" ", "").replace(":", "")
    try:
        raw = bytes.fromhex(clean)
    except ValueError as err:
        raise ServiceValidationError(
            f"Ungültiger Hex-Payload: {hex_str!r}"
        ) from err
    return base64.b64encode(raw).decode("ascii")


def _validate_base64(b64_str: str) -> str:
    """Base64 auf Gültigkeit prüfen und normalisiert zurückgeben."""
    try:
        raw = base64.b64decode(b64_str, validate=True)
    except (binascii.Error, ValueError) as err:
        raise ServiceValidationError(
            f"Ungültiger Base64-Payload: {b64_str!r}"
        ) from err
    return base64.b64encode(raw).decode("ascii")


def _resolve_client(
    hass: HomeAssistant, device_id: str, application_id: str | None
) -> TTNMqttClient:
    """Passenden MQTT-Client für Gerät/Anwendung finden."""
    clients: list[TTNMqttClient] = list(hass.data.get(DOMAIN, {}).values())
    if not clients:
        raise ServiceValidationError("Keine TTS-Integration eingerichtet.")

    if application_id:
        clients = [c for c in clients if c.application_id == application_id]
        if not clients:
            raise ServiceValidationError(
                f"Keine Anwendung '{application_id}' gefunden."
            )

    # Bevorzugt: Client, der dieses Gerät bereits kennt (Uplink empfangen).
    known = [c for c in clients if c.knows_device(device_id)]
    if len(known) == 1:
        return known[0]
    if len(known) > 1:
        raise ServiceValidationError(
            f"Gerät '{device_id}' existiert in mehreren Anwendungen. "
            "Bitte 'application_id' angeben."
        )

    # Sonst: eindeutig, wenn nur ein Client vorhanden ist.
    if len(clients) == 1:
        return clients[0]

    raise ServiceValidationError(
        f"Gerät '{device_id}' konnte keiner Anwendung eindeutig zugeordnet "
        "werden. Bitte 'application_id' angeben."
    )


async def async_register_services(hass: HomeAssistant) -> None:
    """Services registrieren (nur einmal pro HA-Instanz)."""
    if hass.services.has_service(DOMAIN, SERVICE_SEND_DOWNLINK):
        return

    async def _handle_send_downlink(call: ServiceCall) -> None:
        device_id: str = call.data[ATTR_DEVICE_ID]
        f_port: int = call.data[ATTR_F_PORT]
        confirmed: bool = call.data[ATTR_CONFIRMED]
        priority: str = call.data[ATTR_PRIORITY]
        application_id: str | None = call.data.get(ATTR_APPLICATION_ID)

        b64 = call.data.get(ATTR_PAYLOAD_BASE64)
        if b64:
            frm_payload = _validate_base64(b64)
        elif call.data.get(ATTR_PAYLOAD):
            frm_payload = _hex_to_base64(call.data[ATTR_PAYLOAD])
        else:
            # Leerer Downlink (z. B. nur f_port für Trigger) ist erlaubt.
            frm_payload = ""

        client = _resolve_client(hass, device_id, application_id)

        try:
            await hass.async_add_executor_job(
                client.publish_downlink,
                device_id,
                f_port,
                frm_payload,
                confirmed,
                priority,
            )
        except Exception as err:  # noqa: BLE001
            raise ServiceValidationError(
                f"Downlink an '{device_id}' fehlgeschlagen: {err}"
            ) from err

    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_DOWNLINK,
        _handle_send_downlink,
        schema=SEND_DOWNLINK_SCHEMA,
    )


def async_unregister_services(hass: HomeAssistant) -> None:
    """Services entfernen, wenn keine Config-Entry mehr aktiv ist."""
    if not hass.data.get(DOMAIN):
        if hass.services.has_service(DOMAIN, SERVICE_SEND_DOWNLINK):
            hass.services.async_remove(DOMAIN, SERVICE_SEND_DOWNLINK)
