# MeRGBW Light

Home Assistant integration for MeRGBW Bluetooth LE lights (Hexagon Light and Sunset Light).

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-blue.svg)](https://hacs.xyz/) [![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Bluetooth-lightgrey)](https://www.home-assistant.io/integrations/bluetooth/)

## Contents
- Features
- Supported devices
- Requirements
- Installation
- Configuration
- Usage
- Services
- Scenes / effects
- Troubleshooting
- Development
- Protocol notes

## Features
- Discovers nearby MeRGBW lights via Home Assistant Bluetooth and lets you override the guessed profile when needed.
- Uses protocol profiles so classic Sunset and Hexagon devices both work out of the box.
- Exposes Hexagon-only extras: music modes, scene IDs, and schedules in addition to standard HA light controls.
- Ships helper scripts for packet debugging and scene extraction.

## Supported devices
- **Sunset Light** (default profile): 8-bit RGB payloads and simple scenes.
- **Hexagon Light**: hue/saturation payloads, extended scenes (~100), music modes, schedules.

Choose the profile during setup; the profile drives command builders, effect lists, and available services.

## Requirements
- Home Assistant with Bluetooth enabled and the host in range of the light.
- The Bluetooth MAC address of your light (if discovery does not find it).

## Installation

**HACS (recommended)**
1. In HACS, open the ⋮ menu → Custom repositories.
2. Add this repo URL and set type to “Integration”.
3. Install “MeRGBW Light” from HACS.
4. Restart Home Assistant.

**Manual**
1. Copy `custom_components/mergbw` into the `custom_components` directory of your Home Assistant config.
2. Restart Home Assistant.

## Configuration
1. Go to **Settings** → **Devices & Services** → **+ Add Integration** → search for “MeRGBW Light”.
2. If discovered, select the device by name/MAC. The profile is auto-guessed; override it if needed.
3. Or choose **Manual entry**, provide the Bluetooth MAC, and pick a profile.
4. Submit to create the entry. A light entity is created; Hexagon-only services become available under the `light` domain.

## Usage
After setup you get a standard HA light entity: on/off, brightness, color, and `effect` follow the selected profile’s command format. For Hexagon devices, additional entity services are available (examples below).

### Service examples
Call these under the `light` domain.

```yaml
# Hexagon: play a specific scene by ID with optional parameter
service: light.set_scene_id
target:
  entity_id: light.mergbw
data:
  scene_id: 42
  scene_param: 3
```

```yaml
# Hexagon: music mode by name or number
service: light.set_music_mode
target:
  entity_id: light.mergbw
data:
  mode: spectrum2  # or 2
```

```yaml
# Hexagon: schedule on/off with weekday names or bitmask (0x7F = daily)
service: light.set_schedule
target:
  entity_id: light.mergbw
data:
  on_enabled: true
  on_hour: 7
  on_minute: 30
  on_days_mask: [mon, tue, wed, thu, fri]
  off_enabled: true
  off_hour: 22
  off_minute: 0
  off_days_mask: 0x7F
```

```yaml
# Both profiles: select an effect by name from the profile's effect list
service: light.turn_on
target:
  entity_id: light.mergbw
data:
  effect: Rainbow
```

## Services
- `light.set_scene_id` (Hexagon): play a scene by numeric ID, optional `scene_param`.
- `light.set_music_mode` (Hexagon): mode 1–6 or name (`spectrum1/2/3`, `flowing`, `rolling`, `rhythm`).
- `light.set_music_sensitivity` (Hexagon): value 0–100.
- `light.set_schedule` (Hexagon): `on_enabled`, `on_hour`, `on_minute`, `on_days_mask`, `off_enabled`, `off_hour`, `off_minute`, `off_days_mask` (bit0=Mon … bit6=Sun; `0x7F` = every day; mask may be int or weekday list).

## Scenes / effects
- Sunset profile: effect list mirrors the original device scenes.
- Hexagon profile: Classic, Festival, and extended “Other” scenes are exposed by name; any numeric ID works via `set_scene_id`.

## Troubleshooting
- Stay in Bluetooth range and ensure no other host keeps the device connected.
- If colors look wrong, delete/re-add the integration and choose the other profile.
- Use `scripts/ble_baseline.py` to scan, connect, and send raw writes (`--profile sunset_light` or `--profile hexagon_light`).

## Development
- Packet builder tests live in `tests/test_protocol.py`; run them with `pytest`.
- Add a new profile by subclassing `ProtocolProfile` in `custom_components/mergbw/protocol.py`, adding it to `list_profiles`/`get_profile`, extending `services.yaml` if needed, and adding tests.

## Protocol notes
- BLE service: `0000fff0-0000-1000-8000-00805f9b34fb`
- Write characteristic: `0000fff3-0000-1000-8000-00805f9b34fb`
- Notify characteristic: `0000fff4-0000-1000-8000-00805f9b34fb`
- Packet format: `0x55` + `cmd` + `0xFF` + `length` + `payload` + checksum (one’s complement of folded sum).
- Sunset: RGB bytes, brightness 0–100, simple scenes.
- Hexagon: hue (0–360) + saturation (0–1000), brightness 0–1000, scene ID + speed param, music modes 1–6, schedules via cmd 0x0A.
