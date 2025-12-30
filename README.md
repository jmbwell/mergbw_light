# MeRGBW

Home Assistant integration for MeRGBW Bluetooth LE lights (Hexagon Light and Sunset Light).

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-blue.svg)](https://hacs.xyz/) [![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Bluetooth-lightgrey)](https://www.home-assistant.io/integrations/bluetooth/) [![HA integration usage](https://img.shields.io/badge/dynamic/json?color=41BDF5&logo=home-assistant&label=integration%20usage&suffix=%20installs&cacheSeconds=15600&url=https://analytics.home-assistant.io/custom_integrations.json&query=$.mergbw.total)](https://analytics.home-assistant.io/custom_integrations.json)


## Contents
- [Features](#features)
- [Supported devices](#supported-devices)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Services](#services)
- [Scenes / effects](#scenes--effects)
- [Release notes](#release-notes)
- [Troubleshooting](#troubleshooting)
- [Development](#development)
- [Protocol notes](#protocol-notes)

## Features
- Discovers nearby MeRGBW lights via Home Assistant Bluetooth and lets you override the guessed profile when needed.
- Uses protocol profiles so classic Sunset and Hexagon devices both work out of the box.
- Exposes Hexagon-only extras: music modes, scene IDs, and schedules in addition to standard HA light controls.
- Ships helper scripts for packet debugging and scene extraction.

## Supported devices

There are many devices available that seem to work with an app called **MeRGBW**. This integration first supported one such device called **Sunset Light** available on Amazon. This fork of the project adds support for a device called **Hexagon Light**, also on Amazon. Other devices that work with the **MeRGBW App** might also work. They seem to be the same reference design on the same chipset with minor firmware/profile tweaks. 

This integration supports adding more variants. This document includes some notes for developers to get started.

<img src="screenshots/example-device.png" alt="Example MeRGBW device" style="max-width: 260px; width: 100%; height: auto;" />

Above: Example of a supported device.

## Requirements
- Home Assistant with Bluetooth enabled and the host in range of the light.
- The Bluetooth MAC address of your light (if discovery does not find it).

## Installation

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=jmbwell&repository=mergbw&category=integration)

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

## Screenshots
<img src="screenshots/screenshot-02-config-device.png" alt="Config flow: device selection" style="max-width: 420px; width: 100%; height: auto;" />
<img src="screenshots/screenshot-01-config-mac-profile.png" alt="Config flow: manual entry and profile" style="max-width: 420px; width: 100%; height: auto;" />
<img src="screenshots/screenshot-03-controls.png" alt="Light controls" style="max-width: 420px; width: 100%; height: auto;" />

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

## Release notes
- 0.2.3: Add `iot_class` metadata and tidy manifest formatting.

## Troubleshooting
- Stay in Bluetooth range and ensure no other host keeps the device connected.
- If colors look wrong, delete/re-add the integration and choose the other profile.
- Use `scripts/ble_baseline.py` to scan, connect, and send raw writes (`--profile sunset_light` or `--profile hexagon_light`).

## Sniffing and adding new devices
1. Install Xcode from the Mac App Store, then download Apple’s “Additional Tools for Xcode” to get **PacketLogger** (inside `Hardware/`).
2. Install the [Bluetooth logging profile](https://developer.apple.com/bug-reporting/profiles-and-logs/) from Apple’s developer site onto your iOS device.
2. Connect your iOS device to the Mac via USB cable.
3. Open PacketLogger and start a new **iOS Trace**.
4. Open the official app for the light on iOS, interact with every feature (on/off, colors, brightness, effects/scenes, music modes, schedules, etc.) while logging runs.
5. Stop logging and save the trace. Look for repeated write patterns, command bytes, and payload shapes to infer packet structure (checksum, lengths, ID fields).
6. Add a new protocol profile in `custom_components/mergbw/protocol.py` that maps the observed commands (on/off, brightness, color payload, effects/scenes, any extras). Register it in `list_profiles`/`get_profile`, update `services.yaml` if new services are needed, and add tests mirroring `tests/test_protocol.py`.

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
