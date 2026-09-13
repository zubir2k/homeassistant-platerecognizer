# Plate Recognizer — Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![HA Version](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-blue)](https://www.home-assistant.io/)

A modern Home Assistant integration for [Plate Recognizer](https://platerecognizer.com/) — read vehicle license plates from any HA camera using the Snapshot Cloud API or a local On-Premise SDK.

> **Fork of** [robmarkcole/HASS-plate-recognizer](https://github.com/robmarkcole/HASS-plate-recognizer) — rewritten with a proper Config Flow UI, Options Flow, and compatibility with HA 2024.x+.

---

## Features

- ✅ **Config Flow** — set up entirely through the UI (Settings → Integrations)
- ✅ **Options Flow** — change regions, watched plates, and file-saving options without a restart
- ✅ Cloud API and **On-Premise SDK** support
- ✅ Watched plates with **fuzzy matching** (tolerates 1–2 digit errors)
- ✅ `platerecognizer_vehicle_detected` event per vehicle
- ✅ Make / Model / Colour (MMC) attributes for paid plans
- ✅ Timestamped + latest image saving
- ✅ HACS-compatible

---

## Installation

### Via HACS (recommended)

1. In HACS → **Custom Repositories** → add `https://github.com/zubir2k/homeassistant-platerecognizer` (category: Integration)
2. Install **Plate Recognizer** from the HACS list
3. Restart Home Assistant

### Manual

Copy `custom_components/platerecognizer/` into your HA `config/custom_components/` folder and restart.

---

## Setup

1. Go to **Settings → Integrations → + Add Integration**
2. Search for **Plate Recognizer**
3. Enter your API token (from [app.platerecognizer.com](https://app.platerecognizer.com/service/snapshot-cloud/)) and select a source camera
4. Click **Submit** — HA will validate your token live

For **On-Premise SDK**: tick the checkbox, leave the API token blank, and enter your local server URL (default `http://localhost:8080`).

---

## Options

After setup, click **Configure** on the integration card to adjust:

| Option | Description |
|---|---|
| `regions` | Comma-separated country/region codes to hint the engine (e.g. `my, sg`) |
| `watched_plates` | Comma-separated plate numbers to fuzzy-match |
| `detection_rule` | `none` (default) or `strict` (discard plates outside a vehicle bounding box) |
| `region_mode` | `none` (default) or `strict` (only return plates matching region template) |
| `mmc` | Enable Make/Model/Colour — requires a paid plan |
| `save_file_folder` | Absolute path to save processed images (e.g. `/config/images/lpr/`) |
| `save_timestamped_file` | Save a timestamped copy on each detection |
| `always_save_latest_file` | Always overwrite `<camera>_latest.jpg` regardless of detections |

---

## Entity & Attributes

The integration creates one `image_processing` entity per configured camera.

**State:** number of plates found in the last scan  
**Attributes:**

```yaml
plates_detected:
  - plate: ABC1234
    confidence: 0.921
    region: my
    vehicle_type: Car
    orientation: Front        # only with mmc: true
    mmc:                      # only with mmc: true
      make: Toyota
      model: Camry
      color: White
watched_plates:
  ABC1234: true
  XYZ9999: false
statistics:
  calls_remaining: 2455
  calls_used: 45
  max_calls: 2500
last_detection: "2025-01-15T08:32:11+00:00"
```

---

## Events

Every detected vehicle fires a `platerecognizer_vehicle_detected` event:

```yaml
event_type: platerecognizer_vehicle_detected
data:
  entity_id: image_processing.plate_recognizer_front_gate
  plate: ABC1234
  confidence: 0.921
  region: my
  vehicle_type: Car
```

Use this in automations to trigger gates, notifications, or logging.

---

## Triggering a scan

This integration does **not** auto-scan. Call the service manually or from an automation:

```yaml
service: image_processing.scan
target:
  entity_id: image_processing.plate_recognizer_front_gate
```

### Example automation — scan on motion

```yaml
automation:
  - alias: "LPR - Scan on driveway motion"
    trigger:
      - platform: state
        entity_id: binary_sensor.driveway_motion
        to: "on"
    action:
      - service: image_processing.scan
        target:
          entity_id: image_processing.plate_recognizer_front_gate
```

### Example automation — notify on watched plate

```yaml
automation:
  - alias: "LPR - Notify on known plate"
    trigger:
      - platform: event
        event_type: platerecognizer_vehicle_detected
    condition:
      - condition: template
        value_template: "{{ trigger.event.data.plate in ['ABC1234', 'XYZ9999'] }}"
    action:
      - service: notify.mobile_app
        data:
          title: "Known vehicle detected"
          message: "Plate {{ trigger.event.data.plate }} arrived"
```

---

## Country / Region Codes

See the full list at [guides.platerecognizer.com/docs/tech-references/country-codes](https://guides.platerecognizer.com/docs/tech-references/country-codes).

Common codes: `my` (Malaysia), `sg` (Singapore), `gb` (UK), `us-ca` (California), `au` (Australia).

---

## Credits

Original integration by [robmarkcole](https://github.com/robmarkcole/HASS-plate-recognizer).  
Modernised by [@zubir2k](https://github.com/zubir2k).
