"""Sensor-Plattform: erzeugt dynamisch Entities für jeden TTS-Messwert."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    KEY_HINTS,
    META_HINTS,
    META_KEYS,
    SIGNAL_NEW_ENTITY,
    SIGNAL_UPDATE,
)
from .mqtt_client import TTNMqttClient


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Sensor-Plattform einrichten und auf neue Messwerte lauschen."""
    client: TTNMqttClient = hass.data[DOMAIN][entry.entry_id]
    known: set[tuple[str, str]] = set()

    @callback
    def _add_entity(device_id: str, key: str) -> None:
        ekey = (device_id, key)
        if ekey in known:
            return
        known.add(ekey)
        async_add_entities([TTNSensor(client, entry.entry_id, device_id, key)])

    # Bereits empfangene Messwerte nachziehen (falls Uplinks vor Setup kamen).
    for device_id, key in list(client.values.keys()):
        _add_entity(device_id, key)

    entry.async_on_unload(
        async_dispatcher_connect(
            hass, f"{SIGNAL_NEW_ENTITY}_{entry.entry_id}", _add_entity
        )
    )


def _hints_for(key: str) -> dict[str, Any]:
    """Einheit / device_class / state_class für einen Messwert bestimmen."""
    if key in META_KEYS:
        return META_HINTS.get(key, {})
    low = key.lower()
    for needle, hints in KEY_HINTS:
        if needle in low:
            return hints
    return {}


class TTNSensor(SensorEntity):
    """Eine Messgröße eines LoRaWAN-Geräts."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        client: TTNMqttClient,
        entry_id: str,
        device_id: str,
        key: str,
    ) -> None:
        self._client = client
        self._entry_id = entry_id
        self._device_id = device_id
        self._key = key

        self._attr_unique_id = f"{entry_id}_{device_id}_{key}"
        self._attr_name = key.replace("_", " ").title()

        hints = _hints_for(key)
        self._attr_native_unit_of_measurement = hints.get("unit")
        if hints.get("device_class"):
            self._attr_device_class = hints["device_class"]
        state_class = hints.get("state_class")
        if state_class:
            self._attr_state_class = SensorStateClass(state_class)
        if key in META_KEYS:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

        device = client.devices.get(device_id)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_{device_id}")},
            name=device_id,
            manufacturer="LoRaWAN via The Things Stack",
            model=(device.dev_eui if device else None),
        )

    @property
    def native_value(self) -> Any:
        val = self._client.values.get((self._device_id, self._key))
        return val.value if val else None

    @property
    def available(self) -> bool:
        return (self._device_id, self._key) in self._client.values

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        val = self._client.values.get((self._device_id, self._key))
        if val and val.last_update:
            return {"last_uplink": val.last_update}
        return {}

    async def async_added_to_hass(self) -> None:
        """Auf Wert-Updates des eigenen Geräts reagieren."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{SIGNAL_UPDATE}_{self._entry_id}_{self._device_id}",
                self._handle_update,
            )
        )

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()
