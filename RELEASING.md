# Veröffentlichung als HACS-Integration

Diese Anleitung führt vom aktuellen Repo zu einer Integration, die sich per HACS
installieren lässt — erst als **Custom Repository** (sofort möglich), dann
optional als Eintrag im **HACS-Default-Store** (auffindbar für alle, mit
Review-Prozess).

> **Vor allem: zwei Platzhalter ersetzen.** Im Projekt steht überall
> `alpha-omega-technology/ha-ttn-mqtt` als Owner/Repo. Falls euer echtes
> GitHub-Repo anders heißt, in diesen Dateien anpassen:
> `custom_components/ttn_mqtt/manifest.json` (`documentation`, `issue_tracker`,
> `codeowners`), `info.md`, `README.md`, `hacs.json`.

---

## Stufe 1 — Repo veröffentlichen (Custom Repository)

Damit kann es jeder sofort über HACS → „Custom repositories" installieren.

1. **Öffentliches GitHub-Repo anlegen** (z. B. `alpha-omega-technology/ha-ttn-mqtt`)
   und den Inhalt dieses Ordners pushen. Struktur muss so sein:

   ```
   ha-ttn-mqtt/
   ├── custom_components/
   │   └── ttn_mqtt/
   │       ├── __init__.py
   │       ├── manifest.json
   │       ├── config_flow.py
   │       ├── const.py
   │       ├── mqtt_client.py
   │       ├── sensor.py
   │       ├── services.py
   │       ├── services.yaml
   │       ├── strings.json
   │       └── translations/{de,en}.json
   ├── .github/workflows/validate.yml
   ├── hacs.json
   ├── info.md
   ├── README.md
   ├── RELEASING.md
   ├── LICENSE
   └── .gitignore
   ```

2. **Repo-Description setzen** (GitHub → About): kurzer Satz, z. B.
   *„Home Assistant integration for The Things Stack / TTN via MQTT"*.
   HACS zeigt diese Beschreibung an — sie ist **Pflicht**.

3. **Topics setzen** (GitHub → About → Topics): z. B. `home-assistant`,
   `hacs`, `lorawan`, `the-things-stack`, `ttn`, `mqtt`, `iot`. Wird für die
   Suche im HACS-Store genutzt.

4. **Validierung grün bekommen.** Der mitgelieferte Workflow
   `.github/workflows/validate.yml` prüft bei jedem Push:
   - **HACS Action** (`hacs/action@main`, category `integration`)
   - **Hassfest** (`home-assistant/actions/hassfest`)
   Beide müssen ohne Fehler durchlaufen. Häufige Stolpersteine: `version` im
   `manifest.json` fehlt/veraltet, `documentation`/`issue_tracker` ungültig,
   `codeowners` kein echter GitHub-Handle.

5. **Release/Tag erstellen** (empfohlen): SemVer-Tag wie `v0.2.0` und ein
   GitHub-Release dazu. HACS bietet dann die letzten 5 Releases zur Auswahl an;
   ohne Release wird der Default-Branch installiert. Bei jeder neuen Version:
   `version` im `manifest.json` **hochzählen** und neues Release taggen.

6. **Testinstallation:** HACS → drei Punkte → *Custom repositories* → Repo-URL
   eintragen, Kategorie *Integration* → installieren → HA neu starten →
   Integration hinzufügen. Wenn das sauber läuft, ist Stufe 1 fertig.

---

## Stufe 2 — In den HACS-Default-Store (optional)

Damit ist die Integration in HACS **ohne** Custom-Repository-Eintrag auffindbar.
Zwei Voraussetzungen zusätzlich zu Stufe 1:

### 2a. Brand/Icon im `home-assistant/brands`-Repo

Ohne Brand-Eintrag akzeptiert der Default-Store die Integration nicht.

Die fertigen Icons liegen bereits im Repo unter [`icons/`](icons/):
`icon.png` (256×256), `icon@2x.png` (512×512) und die Quelldatei `icon.svg`
(im AOT-CD: Primärblau `#10537E`, Grün `#62B22E`, Teal `#04A098`).

1. Fork von `github.com/home-assistant/brands`.
2. Ordner `custom_integrations/ttn_mqtt/` anlegen und dort ablegen:
   - `icon.png` ← aus `icons/icon.png` (256×256, transparenter Hintergrund)
   - `icon@2x.png` ← aus `icons/icon@2x.png` (512×512)
   - optional `logo.png` / `logo@2x.png` (horizontales Logo)
3. Pull Request gegen `home-assistant/brands` stellen und mergen lassen.

> Hinweis: Das `icons/`-Verzeichnis im Integrations-Repo dient als Quelle und
> für die Anzeige in der README. Für die Icon-Anzeige **in Home Assistant selbst**
> ist der Brands-PR nötig — HACS/HA laden das Icon aus dem `brands`-Repo.

### 2b. PR gegen `hacs/default`

1. Fork von `github.com/hacs/default`.
2. In der Datei `integration` das Repo im Format `owner/repo` (z. B.
   `alpha-omega-technology/ha-ttn-mqtt`) an der alphabetisch richtigen Stelle
   ergänzen.
3. Pull Request stellen. Der HACS-Bot prüft automatisch alle Anforderungen
   (öffentlich, Description, Topics, Struktur, Validierung, Brand vorhanden).
   Erst wenn alle Checks grün sind, wird gemergt.

---

## Wartung / gute Praxis

- **Versionierung:** SemVer. Breaking Changes = Major, Features = Minor,
  Fixes = Patch. Jede Veröffentlichung mit Tag + Release.
- **CHANGELOG:** Änderungen je Release dokumentieren (z. B. `CHANGELOG.md` oder
  GitHub-Release-Notes).
- **HA-Kompatibilität:** In `hacs.json` steht `homeassistant: "2024.1.0"` als
  Mindestversion — anheben, falls neuere HA-APIs genutzt werden.
- **Secrets:** Niemals API-Keys/Zugangsdaten committen (die `.gitignore` deckt
  Testdaten ab; die Integration speichert Keys ohnehin nur in der HA-Config).

---

## Schnell-Checkliste

- [ ] Platzhalter `alpha-omega-technology/ha-ttn-mqtt` überall ersetzt
- [ ] Öffentliches Repo mit korrekter Ordnerstruktur
- [ ] Repo-Description + Topics gesetzt
- [ ] `validate.yml` läuft grün (HACS + Hassfest)
- [ ] `manifest.json`: `version`, `documentation`, `issue_tracker`, `codeowners` korrekt
- [ ] Tag + GitHub-Release erstellt
- [ ] Als Custom Repository getestet installiert
- [ ] (Default-Store) Brand-PR in `home-assistant/brands` gemergt
- [ ] (Default-Store) PR in `hacs/default` gestellt
