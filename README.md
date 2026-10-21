![PlateRecognizer](https://github.com/user-attachments/assets/b85edee1-d559-4a58-ab78-b369f0a405a5)

![GitHub Repo stars](https://img.shields.io/github/stars/zubir2k/homeassistant-platerecognizer?style=social)
[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://github.com/hacs/default)
[![hacs_badge](https://img.shields.io/badge/HACS-Integration-41BDF5.svg)](https://github.com/hacs/integration)
![GitHub all releases](https://img.shields.io/badge/dynamic/json?color=41BDF5&logo=home-assistant&label=Download%20Count&suffix=%20installs&cacheSeconds=15600&url=https://analytics.home-assistant.io/custom_integrations.json&query=$.platerecognizer.total)
[![Buy](https://img.shields.io/badge/Belanja-Coffee-yellow.svg)](https://zubirco.de/buymecoffee)
![GitHub manifest version (path)](https://img.shields.io/github/manifest-json/v/zubir2k/homeassistant-platerecognizer?filename=custom_components%2Fplaterecognizer%2Fmanifest.json)

A modern Home Assistant integration for [Plate Recognizer](https://platerecognizer.com/) — detect and read vehicle license plates from any HA camera using the [Snapshot Cloud API](https://guides.platerecognizer.com/docs/snapshot/api-reference) or a self-hosted On-Premise SDK. No Docker required.

> Talks directly to the Plate Recognizer API. The idea of a Plate Recognizer integration for Home Assistant was pioneered by [@robmarkcole](https://github.com/robmarkcole/HASS-plate-recognizer); this integration is a separate implementation built on config entries.

---

## Features

- ✅ **UI setup** — config flow and options flow, no YAML, no restart
- ✅ **Scan button** — `button.press` from any automation (e.g. on a Frigate car event)
- ✅ **Last plate sensor** — best plate as state, every read (score, country, vehicle, box) in attributes
- ✅ **Last frame image** — the scanned frame with plates outlined
- ✅ **Remaining calls sensor** — cloud API allowance left this month
- ✅ **Watchlist** — near-match (up to 2 characters off), plus `on_watchlist` in the event
- ✅ **`platerecognizer_plate_read` event** fired for every plate
- ✅ **Cloud API or local SDK**, make/model/colour for eligible plans
- ✅ **Multi-camera** — one device per camera

---

## Entities

Each camera gets a device, **Plate Recognizer &lt;camera name&gt;**, with:

| Entity | Example | What it does |
|---|---|---|
| Button | `button.plate_recognizer_front_gate_scan` | Grab a frame and read plates |
| Sensor | `sensor.plate_recognizer_front_gate_last_plate` | Best plate from the last scan |
| Image | `image.plate_recognizer_front_gate_last_frame` | Last scanned frame, plates outlined |
| Sensor | `sensor.plate_recognizer_front_gate_remaining_calls` | Cloud calls left (cloud only) |

Last plate attributes:

```yaml
plates_found: 1
reads:
  - plate: ABC123
    score: 0.912
    country: my
    vehicle: Sedan
    box: {xmin: 410, ymin: 220, xmax: 502, ymax: 250}
scanned_at: "2026-10-19T12:30:00+00:00"
watchlist:
  ABC123: true
```

---

## Installation

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=zubir2k&repository=homeassistant-platerecognizer&category=integration)

### Via HACS (recommended)

1. In HACS → **Custom Repositories** → add `https://github.com/zubir2k/homeassistant-platerecognizer` (category: **Integration**)
2. Install **Plate Recognizer** from the HACS list
3. Restart Home Assistant

### Manual

Copy `custom_components/platerecognizer/` into your HA `config/custom_components/` folder and restart.

---

## Setup

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=platerecognizer)

1. Go to **Settings → Integrations → Add Integration**
2. Search for **Plate Recognizer**
3. Enter your API token from [app.platerecognizer.com](https://app.platerecognizer.com/service/snapshot-cloud/) and select a source camera
4. Click **Submit** — HA validates your token live before saving

For **On-Premise SDK**: enable the toggle, leave the API token blank, and enter your local server URL (default `http://localhost:8080`).

To add a second camera, click **Add service** on the integration page and repeat the setup.

![Setup](https://github.com/user-attachments/assets/e65c34c6-eede-49e3-a304-d66f64f69a7f)

---

## Options

Click **Configure** on the integration to set:

| Option | Description |
|---|---|
| Country hints | Codes such as `my, sg` — see [country codes](https://guides.platerecognizer.com/docs/tech-references/country-codes) |
| Watchlist | Plates to watch, e.g. `ABC123, XYZ456` |
| Ignore plates not on a vehicle | Drop plates found outside a vehicle |
| Only accept hinted country formats | Reject plates that don't fit the hinted countries |
| Make, model and colour | Eligible paid plans only |
| Snapshot folder | e.g. `/media/platerecognizer`; blank turns saving off. Must be allowed by Home Assistant (media folders are by default). Folders under `/config/www` are refused because they are public at `/local/` without login; use the **Last frame** image entity to show the latest frame on a dashboard |
| Keep history | Timestamped copy of every frame with a plate |
| Save every scan | Update `<camera>_last.jpg` even when nothing is found |

Changing options reloads the entry; your entity names, areas and history are kept.

---

## Scanning

Scans run only when you ask:

```yaml
action: button.press
target:
  entity_id: button.plate_recognizer_front_gate_scan
```

### Example — notify on a plate

```yaml
alias: "LPR - Notify on plate"
triggers:
  - trigger: event
    event_type: platerecognizer_plate_read
actions:
  - action: notify.mobile_app_your_phone
    data:
      title: "🚗 {{ trigger.event.data.plate }}"
      message: >
        {{ (trigger.event.data.score * 100) | round(1) }}% ·
        {{ trigger.event.data.vehicle }}
```

### Example — open the gate for a watchlist plate

```yaml
alias: "LPR - Open gate for watchlist"
triggers:
  - trigger: event
    event_type: platerecognizer_plate_read
    event_data:
      on_watchlist: true
actions:
  - action: switch.turn_on
    target:
      entity_id: switch.driveway_gate
```

## Event

```yaml
event_type: platerecognizer_plate_read
data:
  config_entry_id: 01J...
  camera: camera.front_gate
  plate: ABC123
  score: 0.912
  country: my
  vehicle: Sedan
  box: {xmin: 410, ymin: 220, xmax: 502, ymax: 250}
  on_watchlist: false
```

---

## Upgrading from 2.x

- The `image_processing` entity is gone; use the **Scan** button (`button.press`) instead of `image_processing.scan`.
- The event is now `platerecognizer_plate_read`; `confidence` is `score`, `region_code` is `country`, `vehicle_type` is `vehicle`, and the box is a full `box`.
- Your options are migrated automatically, and the stats/image entities keep their customisations.

---

## Country / Region Codes

See the full list at [guides.platerecognizer.com](https://guides.platerecognizer.com/docs/tech-references/country-codes).

Common codes: `my` (Malaysia), `sg` (Singapore), `gb` (UK), `au` (Australia), `us` (USA).

---

## Credits

- Plate Recognizer API: [platerecognizer.com](https://platerecognizer.com/)
- Thanks to [@robmarkcole](https://github.com/robmarkcole/HASS-plate-recognizer) for the original YAML integration that inspired this one

---

## License

MIT License — see [LICENSE](LICENSE)
