# The Things Stack (MQTT)

Bringt Geräte und **Live-Daten** aus **The Things Stack** / **The Things
Network (TTN)** direkt in Home Assistant — über den nativen MQTT-Broker von TTS.
Geräte und Messwerte werden **automatisch erkannt** und als HA-Devices mit
Sensor-Entities angelegt.

## Highlights

- MQTT-Anbindung (TLS) an TTN Community oder eigene TTS-/TTI-Cloud-Instanz.
- Auto-Discovery: pro Gerät ein HA-Device, pro Messwert eine Sensor-Entity.
- Diagnose-Sensoren: RSSI, SNR, Frame-Counter, Spreading Factor, Frequenz,
  Gateway-Anzahl, Airtime.
- **Downlinks** per Service `ttn_mqtt.send_downlink` (z. B. Milesight WS523).
- Einrichtung komplett über die HA-Oberfläche (Config-Flow).

## Voraussetzung

Für echte Messwerte muss im TTS ein **Payload-Formatter (Decoder)** für das
Gerät hinterlegt sein. Details, Setup und Beispiele in der
[README](https://github.com/alpha-omega-technology/ha-ttn-mqtt).
