"""Konstanten für die The Things Stack (MQTT) Integration."""

from __future__ import annotations

from homeassistant.const import (
    CONCENTRATION_PARTS_PER_MILLION,
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    UnitOfElectricPotential,
    UnitOfPressure,
    UnitOfTemperature,
)

DOMAIN = "ttn_mqtt"

# --- Konfigurations-Keys ---------------------------------------------------
CONF_HOST = "host"
CONF_PORT = "port"
CONF_APP_ID = "application_id"
CONF_TENANT_ID = "tenant_id"
CONF_API_KEY = "api_key"
CONF_USE_TLS = "use_tls"

# --- Defaults --------------------------------------------------------------
DEFAULT_HOST = "eu1.cloud.thethings.network"
DEFAULT_PORT = 8883
DEFAULT_TENANT_ID = "ttn"
DEFAULT_USE_TLS = True

# --- Dispatcher-Signale ----------------------------------------------------
# Neues, bisher unbekanntes (Gerät, Messwert) aufgetaucht -> Entity anlegen.
SIGNAL_NEW_ENTITY = f"{DOMAIN}_new_entity"
# Neuer Wert für ein bestehendes Gerät -> Entities aktualisieren.
SIGNAL_UPDATE = f"{DOMAIN}_update"

# --- Diagnose-Messwerte aus den Metadaten ----------------------------------
# Diese Keys werden aus uplink_message-Metadaten erzeugt (nicht aus dem Decoder).
META_KEYS = (
    "rssi",
    "snr",
    "f_cnt",
    "f_port",
    "spreading_factor",
    "bandwidth",
    "frequency",
    "gateway_count",
    "consumed_airtime",
)

# --- Heuristik: Einheit / device_class / state_class je Messwert-Name ------
# Wird per "Substring im kleingeschriebenen Key" ausgewertet.
# Reihenfolge = Priorität (erster Treffer gewinnt).
KEY_HINTS: tuple[tuple[str, dict], ...] = (
    (
        "temperature",
        {
            "unit": UnitOfTemperature.CELSIUS,
            "device_class": "temperature",
            "state_class": "measurement",
        },
    ),
    (
        "humidity",
        {
            "unit": PERCENTAGE,
            "device_class": "humidity",
            "state_class": "measurement",
        },
    ),
    (
        "co2",
        {
            "unit": CONCENTRATION_PARTS_PER_MILLION,
            "device_class": "carbon_dioxide",
            "state_class": "measurement",
        },
    ),
    (
        "pressure",
        {
            "unit": UnitOfPressure.HPA,
            "device_class": "pressure",
            "state_class": "measurement",
        },
    ),
    (
        "battery",
        {
            "unit": PERCENTAGE,
            "device_class": "battery",
            "state_class": "measurement",
        },
    ),
    (
        "voltage",
        {
            "unit": UnitOfElectricPotential.VOLT,
            "device_class": "voltage",
            "state_class": "measurement",
        },
    ),
)

# Feste Einstellungen für die Diagnose-Messwerte.
META_HINTS: dict[str, dict] = {
    "rssi": {
        "unit": SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        "device_class": "signal_strength",
        "state_class": "measurement",
    },
    "snr": {
        "unit": SIGNAL_STRENGTH_DECIBELS,
        "state_class": "measurement",
    },
    "f_cnt": {"state_class": "total_increasing"},
    "f_port": {},
    "spreading_factor": {},
    "bandwidth": {"unit": "Hz"},
    "frequency": {"unit": "Hz"},
    "gateway_count": {"state_class": "measurement"},
    "consumed_airtime": {"unit": "s"},
}
