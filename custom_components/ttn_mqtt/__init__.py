"""The Things Stack (MQTT) – Integration für Home Assistant."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import (
    CONF_API_KEY,
    CONF_APP_ID,
    CONF_HOST,
    CONF_PORT,
    CONF_TENANT_ID,
    CONF_USE_TLS,
    DOMAIN,
)
from .mqtt_client import TTNMqttClient
from .services import async_register_services, async_unregister_services

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Config-Entry einrichten: MQTT-Client verbinden."""
    data = entry.data
    client = TTNMqttClient(
        hass=hass,
        entry_id=entry.entry_id,
        host=data[CONF_HOST],
        port=data[CONF_PORT],
        application_id=data[CONF_APP_ID],
        tenant_id=data.get(CONF_TENANT_ID, ""),
        api_key=data[CONF_API_KEY],
        use_tls=data.get(CONF_USE_TLS, True),
    )

    try:
        await hass.async_add_executor_job(client.connect)
    except Exception as err:  # noqa: BLE001
        raise ConfigEntryNotReady(
            f"Verbindung zu {data[CONF_HOST]} fehlgeschlagen: {err}"
        ) from err

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = client

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await async_register_services(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Config-Entry entladen: Plattformen abbauen, MQTT trennen."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        client: TTNMqttClient = hass.data[DOMAIN].pop(entry.entry_id)
        await hass.async_add_executor_job(client.disconnect)
        async_unregister_services(hass)
    return unload_ok
