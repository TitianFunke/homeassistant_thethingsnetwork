<div align="center">

<img src="icons/icon.png" alt="The Things Stack (MQTT)" width="128" />

# The Things Stack (MQTT) für Home Assistant

**LoRaWAN-Geräte und Live-Daten aus The Things Stack / The Things Network — automatisch in Home Assistant.**

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://hacs.xyz)
[![Release](https://img.shields.io/github/v/release/alpha-omega-technology/ha-ttn-mqtt?style=for-the-badge&color=10537E)](https://github.com/alpha-omega-technology/ha-ttn-mqtt/releases)
[![License](https://img.shields.io/github/license/alpha-omega-technology/ha-ttn-mqtt?style=for-the-badge&color=62B22E)](LICENSE)

[![In HACS öffnen](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=alpha-omega-technology&repository=ha-ttn-mqtt&category=integration)

</div>

---

Verbindet **The Things Stack** bzw. **The Things Network (TTN)** über den nativen
MQTT-Broker mit Home Assistant. Geräte und Messwerte werden **automatisch erkannt**
und als HA-Devices mit Sensor-Entities angelegt — inklusive Downlink-Steuerung.

_Entwickelt von / für **Alpha-Omega Technology**._

## ✨ Funktionen

- 📡 **MQTT-Anbindung (TLS)** an TTN Community oder eigene TTS-/TTI-Cloud-Instanz.
- 🔍 **Auto-Discovery:** pro LoRaWAN-Gerät ein HA-Device, pro Messwert eine Sensor-Entity — aus dem `decoded_payload` des TTS-Decoders.
- 📊 **Diagnose-Sensoren:** RSSI, SNR, Frame-Counter, Spreading Factor, Bandbreite, Frequenz, Gateway-Anzahl, Airtime.
- 🔌 **Downlinks** per Service `ttn_mqtt.send_downlink` (Aktoren, Ventile, z. B. Milesight WS523).
- ⚙️ **Einrichtung komplett über die HA-Oberfläche** (Config-Flow), keine YAML nötig.
- ➕ Neue Geräte erscheinen automatisch, sobald sie das erste Mal senden — ohne Neustart.

## 📑 Inhalt

- [Voraussetzung: Decoder im TTS](#voraussetzung-payload-formatter-decoder-im-ttsttn)
- [Installation](#installation)
- [Einrichtung](#einrichtung)
- [Downlinks senden](#downlinks-senden)
- [Praxisbeispiel: Milesight WS523](#praxisbeispiel-milesight-ws523-smart-socket-schalten)
- [Roadmap](#roadmap)
- [Veröffentlichung als HACS-Modul](#veröffentlichung-als-hacs-modul)

## Voraussetzung: Payload-Formatter (Decoder) im TTS/TTN

> ⚠️ **Ohne Decoder keine Fachwerte.** Damit echte Messwerte (Temperatur,
> Feuchte, Füllstand …) in Home Assistant erscheinen, muss im TTS/TTN für das
> Gerät ein **Payload Formatter (Uplink-Decoder)** hinterlegt sein. Ohne Decoder
> überträgt der Uplink nur `frm_payload` als Base64 — dann gibt es in HA **nur die
> Diagnose-Sensoren** (RSSI, SNR, Frame-Counter …), aber keine dekodierten Fachwerte.

Der Decoder erzeugt im Uplink das Objekt `uplink_message.decoded_payload`, und
genau daraus baut diese Integration die Sensor-Entities. Kein Decoder → kein
`decoded_payload` → keine Fachwerte.

**Wo der Decoder gesetzt wird (von komfortabel nach manuell):**

1. **Über das LoRaWAN Device Repository (empfohlen):** Gerät nicht „blank"
   anlegen, sondern beim End-Device-Setup *„Select the end device in the LoRaWAN
   Device Repository"* wählen (Brand → Model → Profile). TTS bringt den
   Hersteller-Decoder dann automatisch mit — bei den gängigen Marken (Dragino,
   ELSYS, Milesight, Adeunis, Decentlab …) vorhanden.
2. **Pro Anwendung:** *Application → Payload formatters → Uplink* — gilt für alle
   Geräte der App. Typ „Custom Javascript formatter" (Hersteller-`decodeUplink`
   einfügen), „Repository" oder „CayenneLPP".
3. **Pro Gerät:** *End device → Payload formatters → Uplink* — überschreibt die
   App-Einstellung für ein einzelnes Gerät.

**Cayenne LPP:** Sendet der Sensor im Cayenne-LPP-Format, reicht der eingebaute
`CayenneLPP`-Formatter — kein eigenes Skript nötig. Empfehlung ansonsten:
Hersteller-Decoder bevorzugen, sonst Cayenne LPP.

**Wichtiger Praxis-Hinweis:** Ein neu gesetzter oder geänderter Decoder wirkt
erst ab dem **nächsten Uplink** — bereits empfangene Werte werden nicht
rückwirkend dekodiert. Nach dem Setzen also kurz auf das nächste Sende-Intervall
des Geräts (Klasse A) warten, dann erscheinen die Sensoren in HA.

## Installation

### Variante A — HACS (empfohlen)

Am schnellsten über den Button oben („In HACS öffnen") — er öffnet in deiner
HA-Instanz direkt den Dialog zum Hinzufügen dieses Repositories. Alternativ von Hand:

1. HACS → oben rechts die drei Punkte → **Custom repositories**.
2. Repository-URL `https://github.com/alpha-omega-technology/ha-ttn-mqtt` eintragen, Kategorie **Integration**, *Add*.
3. Nach „The Things Stack (MQTT)" suchen → **Download**.
4. Home Assistant neu starten.

### Variante B — manuell

Ordner `custom_components/ttn_mqtt/` in das HA-Konfigurationsverzeichnis
kopieren (neben `configuration.yaml`), sodass
`config/custom_components/ttn_mqtt/manifest.json` existiert. HA neu starten.

## Einrichtung

1. **Einstellungen → Geräte & Dienste → Integration hinzufügen**.
2. „The Things Stack (MQTT)" wählen.
3. Felder ausfüllen:

| Feld           | TTN Community                     | Self-hosted / TTS Cloud            |
|----------------|-----------------------------------|------------------------------------|
| Server/Host    | `eu1.cloud.thethings.network`     | dein TTS-Hostname                  |
| Port           | `8883`                            | `8883` (TLS) / `1883` (unverschl.) |
| Application ID | z. B. `mein-projekt`              | deine Application ID               |
| Tenant ID      | `ttn`                             | dein Tenant, Open-Source: **leer** |
| API-Key        | aus Console → Integrations → MQTT | dito                               |
| TLS verwenden  | an                                | an (empfohlen)                     |

Die Verbindungsdaten stehen in der TTS-Console unter **Application →
Integrations → MQTT**. Dort auch einen **API-Key** erzeugen (Leserechte auf die
Anwendung genügen).

4. Nach dem Speichern testet die Integration die Verbindung. Geräte erscheinen,
   sobald sie das nächste Mal senden (bei Klasse A also mit dem nächsten
   Uplink-Intervall).

## Hinweise zum Betrieb

- **Erst nach dem nächsten Uplink sichtbar:** LoRaWAN-Klasse-A-Geräte senden in
  ihrem eigenen Intervall. Direkt nach der Einrichtung ist ggf. noch nichts da —
  das ist normal.
- **Ein API-Key pro Anwendung.** Für mehrere Anwendungen die Integration
  einfach mehrfach hinzufügen.
- **Sicherheit:** Immer TLS (Port 8883) nutzen. Der API-Key wird in der
  HA-Konfiguration gespeichert; HA-Zugriff entsprechend absichern.
- **DSGVO/GoBD:** Für revisionssichere Historie und Reporting bleibt ThingsBoard
  PE / Odoo die führende Ablage. Diese Integration ist für Visualisierung und
  Automatisierung in HA gedacht, nicht als Archiv.

## Downlinks senden

Die Integration stellt den Service **`ttn_mqtt.send_downlink`** bereit. Damit
lässt sich aus Automationen, Skripten oder den Entwicklertools ein Downlink an
ein Gerät schicken (Aktoren, Ventile, Konfig-Kommandos).

Der Downlink wird über das TTS-Topic `.../down/push` in die Warteschlange des
Geräts gelegt. Bei **Klasse-A-Geräten** (Standard) wird er erst **mit dem
nächsten Uplink** zugestellt — es kann also je nach Sende-Intervall dauern.

> **API-Key-Rechte:** Ein reiner Lese-Key (nur „Read application traffic")
> genügt für Downlinks **nicht**. Der bei der Einrichtung verwendete API-Key
> braucht zusätzlich das Recht **„Write downlink application traffic"**. Fehlt
> es, kommen die Uplink-Sensoren normal an, aber Downlinks werden vom Broker
> abgelehnt. Key in der TTS-Console entsprechend erweitern bzw. neu erzeugen.

**Felder:**

| Feld | Pflicht | Bedeutung |
|---|---|---|
| `device_id` | ja | End-Device-ID wie im Uplink (z. B. `elsys-ers-01`) |
| `f_port` | ja | LoRaWAN FPort 1–223, gemäß Aktor/Decoder |
| `payload` | – | Nutzdaten als **Hex** (`0A0F`, `0a 0f`, `0x0A0F`) |
| `payload_base64` | – | Nutzdaten als Base64 (Vorrang vor `payload`) |
| `confirmed` | – | Confirmed Downlink (Standard: `false`) |
| `priority` | – | `LOWEST … NORMAL … HIGHEST` (Standard: `NORMAL`) |
| `application_id` | – | nur nötig bei mehreren Anwendungen zur Zuordnung |

**Beispiel (Entwicklertools → Aktionen, YAML):**

```yaml
action: ttn_mqtt.send_downlink
data:
  device_id: dragino-relay-01
  f_port: 10
  payload: "01"        # z. B. Relais AN
  confirmed: true
```

**Beispiel in einer Automation:**

```yaml
- alias: Ventil schließen bei Leckage
  triggers:
    - trigger: state
      entity_id: binary_sensor.leckage_keller
      to: "on"
  actions:
    - action: ttn_mqtt.send_downlink
      data:
        device_id: valve-keller
        f_port: 15
        payload: "00"
```

> Die Hex-Bytes und der passende FPort ergeben sich aus dem **Downlink-Format
> des jeweiligen Geräts** (Herstellerdoku). Optional lässt sich im TTS ein
> Downlink-Payload-Formatter hinterlegen — diese Integration sendet die Bytes
> aber direkt, sodass kein Formatter zwingend nötig ist.

### Praxisbeispiel: Milesight WS523 (Smart Socket schalten)

Getestet und verifiziert mit der Milesight **WS523** (schaltbare LoRaWAN-Steckdose).
Der Schaltausgang wird über **FPort 85** angesteuert:

| Aktion | Payload (Hex) | entspricht Base64 |
|---|---|---|
| Steckdose **EIN** | `080100ff` | `CAEA/w==` |
| Steckdose **AUS** | `080000ff` | `CAAA/w==` |

```yaml
action: ttn_mqtt.send_downlink
data:
  device_id: milesight-ws523-89722   # exakt die End-Device-ID aus TTS
  f_port: 85
  payload: "080100ff"                # EIN;  "080000ff" = AUS
  confirmed: false
```

**Wichtig für sofortiges Schalten — Geräteklasse:** Die WS523 ist netzbetrieben
und kann in **Class C** laufen. Nur dann wird der Downlink praktisch sofort
zugestellt. In Class A (Batterie-Standard) wartet der Downlink bis zum nächsten
Uplink des Geräts. Umstellen unter *End device → General settings → Network layer
→ LoRaWAN class → Class C*; zusätzlich das Gerät selbst per Milesight ToolBox auf
Class C konfigurieren, sonst deutet der Network Server den Downlink falsch.

**Kontrolle:** In der TTS-Console beim Gerät unter *Live data* erscheint der
geplante/gesendete Downlink. Der Schaltzustand in HA aktualisiert sich mit dem
nächsten Uplink. Tipp: In der ToolBox „Button Lock" aktivieren, damit der
lokale Taster den ferngeschalteten Zustand nicht überschreibt.

## Roadmap

- Vordefinierte Button-/Switch-Entities pro Gerät (auf Basis des Downlink-Service).
- Options-Flow (Filter-Einstellungen, Diagnose-Sensoren abschaltbar, API-Key ändern).
- Verwertung des Payload-Formatters direkt in HA als Uplink-Fallback.

## Veröffentlichung als HACS-Modul

Wie dieses Repository zu einer installierbaren (und optional im HACS-Store
gelisteten) Integration wird, steht Schritt für Schritt in
[RELEASING.md](RELEASING.md).

## Lizenz

MIT — siehe [LICENSE](LICENSE). © Alpha-Omega Technology.
