![PlateRecognizer](https://github.com/user-attachments/assets/b85edee1-d559-4a58-ab78-b369f0a405a5)

![GitHub Repo stars](https://img.shields.io/github/stars/zubir2k/homeassistant-platerecognizer?style=social)
[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://github.com/hacs/default)
[![hacs_badge](https://img.shields.io/badge/HACS-Integration-41BDF5.svg)](https://github.com/hacs/integration)
![GitHub all releases](https://img.shields.io/badge/dynamic/json?color=41BDF5&logo=home-assistant&label=Download%20Count&suffix=%20installs&cacheSeconds=15600&url=https://analytics.home-assistant.io/custom_integrations.json&query=$.platerecognizer.total)
[![Buy](https://img.shields.io/badge/Belanja-Coffee-yellow.svg)](https://zubirco.de/buymecoffee)
![GitHub manifest version (path)](https://img.shields.io/github/manifest-json/v/zubir2k/homeassistant-platerecognizer?filename=custom_components%2Fplaterecognizer%2Fmanifest.json)

A modern Home Assistant integration for [Plate Recognizer](https://platerecognizer.com/) — detect and read vehicle license plates from any HA camera using the [Snapshot Cloud API](https://guides.platerecognizer.com/docs/snapshot/api-reference) or a self-hosted On-Premise SDK. No Docker required.

> **Forked and rewritten from** [robmarkcole/HASS-plate-recognizer](https://github.com/robmarkcole/HASS-plate-recognizer) — modernized with Config Flow UI, image entity with bounding boxes, per-camera statistics sensor, and full HA 2024.x+ compatibility.

---

## Features

- ✅ **Config Flow** — set up entirely through the HA UI, no YAML required
- ✅ **Options Flow** — change regions, watched plates, detection rules without restart
- ✅ **Image entity** — live annotated snapshot with bounding boxes drawn around detected plates
- ✅ **Statistics sensor** — API calls remaining per camera, resets date, usage breakdown
- ✅ **Watched plates** — fuzzy matching (tolerates 1–2 character errors) with `watched_plates` attribute
- ✅ **`platerecognizer.vehicle_detected` event** fired per detection
- ✅ **Multi-camera** — add multiple cameras, each gets its own set of entities
- ✅ **HACS compatible**
- ✅ **Cloud API and On-Premise SDK** support
- ✅ **Make / Model / Colour (MMC)** for eligible paid plans
- ✅ **`camera_id` passthrough** — camera name sent to Plate Recognizer dashboard for filtering

![Platrecognizer](https://github.com/user-attachments/assets/304e8451-1b6d-402b-9c8c-9461d69ff3c6)

---

## Entities Created

Each configured camera produces three entities:

| Entity | Example ID | Description |
|---|---|---|
| `image_processing` | `image_processing.platerecognizer_frontgate` | Core entity — trigger scans, view detection results |
| `image` | `image.platerecognizer_frontgate` | Annotated snapshot with red bounding boxes and plate labels |
| `sensor` | `sensor.platerecognizer_frontgate_stats` | API calls remaining (state) with full usage breakdown (attributes) |

### image_processing attributes

```yaml
vehicles:
  - plate: ABC123
    confidence: 1.0
    region_code: my
    vehicle_type: Sedan
    box_y_centre: 234.5
    box_x_centre: 456.2
watched_plates:
  ABC123: true
  XYZ456: false
statistics:
  total_calls: 2500
  calls_used: 320
  calls_remaining: 2180
  month: 9
  year: 2026
  resets_on: '2026-09-21T07:56:27Z'
last_detection: '2026-09-08_23-10-28'
regions:
  - my
mmc: false
```

### image attributes

```yaml
vehicles:
  - plate: ABC123
    confidence: 1.0
    region_code: my
    vehicle_type: Sedan
watched_plates:
  ABC123: true
  XYZ456: false
```

### sensor attributes

```yaml
total_calls: 2500
calls_used: 320
calls_remaining: 2180
month: 9
year: 2026
resets_on: '2026-09-21T07:56:27Z'
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

After setup, click **Configure** (⚙️) on the integration card to adjust:

| Option | Description |
|---|---|
| `regions` | Comma-separated country codes to hint the engine, e.g. `my, sg` — see [country codes](https://guides.platerecognizer.com/docs/snapshot/api-reference/#region-code) |
| `watched_plates` | Comma-separated plates for fuzzy matching, e.g. `ABC123, XYZ456` |
| `detection_rule` | `none` (default) or `strict` — discard plates not inside a vehicle bounding box |
| `region_mode` | `none` (default) or `strict` — only return plates matching the region template |
| `mmc` | Enable Make / Model / Colour — requires an eligible paid plan |
| `save_file_folder` | Absolute path to save processed images, e.g. `/config/www/platerecognizer/` |
| `save_timestamped_file` | Save a timestamped copy on each detection |
| `always_save_latest_file` | Always overwrite `<camera>_latest.jpg` regardless of detections |

---

## Triggering a Scan

The integration does **not** auto-scan — call the action manually or from an automation:

```yaml
action: image_processing.scan
target:
  entity_id: image_processing.platerecognizer_frontgate
```

### Example — scan on Frigate car detection (MQTT)

```yaml
alias: "LPR - Scan on Frigate car detection"
trigger:
  - platform: mqtt
    topic: frigate/events
condition:
  - condition: template
    value_template: >
      {{ trigger.payload_json.after.camera == 'FrigateFrontGate'
         and trigger.payload_json.type in ['new', 'end']
         and trigger.payload_json.after.label in ['car', 'motorcycle']
         and trigger.payload_json.after.has_snapshot == true
         and trigger.payload_json.after.false_positive == false }}
  - condition: template
    value_template: >
      {{ 'LuarPagar' in trigger.payload_json.after.current_zones
         or 'LuarPagar' in trigger.payload_json.after.entered_zones }}
  - condition: template
    value_template: >
      {{ (as_timestamp(now()) - as_timestamp(
          states.image_processing.platerecognizer_frontgate.last_changed
          | default(0))) > 30 }}
action:
  - delay:
      milliseconds: 500
  - action: image_processing.scan
    target:
      entity_id: image_processing.platerecognizer_frontgate
mode: single
max_exceeded: silent
```

### Example — notify on detection

```yaml
alias: "LPR - Notify on plate detection"
trigger:
  - platform: event
    event_type: platerecognizer.vehicle_detected
action:
  - action: notify.mobile_app_your_phone
    data:
      title: "🚗 Plate Detected"
      message: >
        Plate: {{ trigger.event.data.plate }}
        Confidence: {{ (trigger.event.data.confidence * 100) | round(1) }}%
        Vehicle: {{ trigger.event.data.vehicle_type }}
```

### Example — trigger action on known plate

```yaml
alias: "LPR - Open gate for known plate"
trigger:
  - platform: event
    event_type: platerecognizer.vehicle_detected
condition:
  - condition: template
    value_template: >
      {{ trigger.event.data.plate in ['ABC123', 'XYZ456'] }}
action:
  - action: switch.turn_on
    target:
      entity_id: switch.driveway_gate
```

---

## Events

Every detected vehicle fires a `platerecognizer.vehicle_detected` event:

```yaml
event_type: platerecognizer.vehicle_detected
data:
  entity_id: image_processing.platerecognizer_frontgate
  plate: ABC123
  confidence: 1.0
  region_code: my
  vehicle_type: Sedan
  box_y_centre: 234.5
  box_x_centre: 456.2
```

---

## Dashboard

### Picture Entity Card (annotated image)

```yaml
type: picture-entity
entity: image.platerecognizer_frontgate
show_state: false
show_name: true
```

### Glance card (stats + last detection)

```yaml
type: glance
entities:
  - entity: sensor.platerecognizer_frontgate_stats
    name: Calls Remaining
  - entity: image_processing.platerecognizer_frontgate
    name: Last Plates
```

---

## Country / Region Codes

See the full list at [guides.platerecognizer.com](https://guides.platerecognizer.com/docs/tech-references/country-codes).

Common codes: `my` (Malaysia), `sg` (Singapore), `gb` (UK), `au` (Australia), `us` (USA).

---

## Comparison with Original

| Feature | Original (robmarkcole) | This Integration |
|---|---|---|
| Setup | YAML only | Config Flow UI ✅ |
| Options | Restart required | Options Flow, no restart ✅ |
| Image entity | ❌ | Annotated with bounding boxes ✅ |
| Statistics sensor | ❌ | Per camera, full usage breakdown ✅ |
| `camera_id` passthrough | ❌ | Sent to Plate Recognizer dashboard ✅ |
| Multi-camera | Manual YAML entries | Add service button ✅ |
| HA version | 2021.x | 2024.1+ ✅ |
| Watched plates | Basic match | Fuzzy match (±2 chars) ✅ |
| On-Premise SDK | ✅ | ✅ |
| MMC support | ✅ | ✅ |

---

## Credits

- Plate Recognizer API: [platerecognizer.com](https://platerecognizer.com/)
- Original integration by [@robmarkcole](https://github.com/robmarkcole/HASS-plate-recognizer)

---

## License

MIT License — see [LICENSE](LICENSE)
