"""Config-Flow für die The Things Stack (MQTT) Integration."""

from __future__ import annotations

import logging
import ssl
from typing import Any

import paho.mqtt.client as mqtt
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import (
    CONF_API_KEY,
    CONF_APP_ID,
    CONF_HOST,
    CONF_PORT,
    CONF_TENANT_ID,
    CONF_USE_TLS,
    DEFAULT_HOST,
    DEFAULT_PORT,
    DEFAULT_TENANT_ID,
    DEFAULT_USE_TLS,
    DOMAIN,
)
from .mqtt_client import _new_paho_client

_LOGGER = logging.getLogger(__name__)


def _validate(data: dict[str, Any]) -> None:
    """Testverbindung zum Broker aufbauen (blockierend, im Executor)."""
    username = (
        f"{data[CONF_APP_ID]}@{data[CONF_TENANT_ID]}"
        if data.get(CONF_TENANT_ID)
        else data[CONF_APP_ID]
    )
    client = _new_paho_client(client_id="ha-ttn-configtest")
    client.username_pw_set(username, data[CONF_API_KEY])
    if data.get(CONF_USE_TLS, True):
        client.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLS)

    result: dict[str, Any] = {}

    def _on_connect(c, userdata, flags, rc, properties=None):
        is_failure = getattr(rc, "is_failure", None)
        result["ok"] = (is_failure is False) or (is_failure is None and rc == 0)
        result["rc"] = rc

    client.on_connect = _on_connect
    try:
        client.connect(data[CONF_HOST], data[CONF_PORT], keepalive=10)
        client.loop_start()
        # kurz auf das CONNACK warten
        import time

        for _ in range(50):
            if "ok" in result:
                break
            time.sleep(0.1)
    except (OSError, ssl.SSLError) as err:
        raise CannotConnect(str(err)) from err
    finally:
        try:
            client.loop_stop()
            client.disconnect()
        except Exception:  # noqa: BLE001
            pass

    if not result:
        raise CannotConnect("Zeitüberschreitung beim Verbindungsaufbau")
    if not result.get("ok"):
        raise InvalidAuth(f"Broker lehnte Verbindung ab (rc={result.get('rc')})")


class TTNConfigFlow(ConfigFlow, domain=DOMAIN):
    """Geführte Einrichtung über die HA-Oberfläche."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            unique_id = (
                f"{user_input[CONF_APP_ID]}@{user_input.get(CONF_TENANT_ID, '')}"
                f"@{user_input[CONF_HOST]}"
            )
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            try:
                await self.hass.async_add_executor_job(_validate, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unerwarteter Fehler bei der Validierung")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=f"{user_input[CONF_APP_ID]} ({user_input[CONF_HOST]})",
                    data=user_input,
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                vol.Required(CONF_APP_ID): str,
                vol.Optional(CONF_TENANT_ID, default=DEFAULT_TENANT_ID): str,
                vol.Required(CONF_API_KEY): str,
                vol.Required(CONF_USE_TLS, default=DEFAULT_USE_TLS): bool,
            }
        )
        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Broker nicht erreichbar."""


class InvalidAuth(HomeAssistantError):
    """Authentifizierung fehlgeschlagen."""
