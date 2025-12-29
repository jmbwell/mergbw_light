# MeRGBW Light

This project implements a Home Assistant custom component for LED lights controllable by the MeRGBW App via Bluetooth LE, including the Hexagon Light and Sunset Light available on Amazon.

## Protocol profiles

The light control protocol is abstracted behind profiles:
- **Sunset Light** (default): original MeRGBW device; 8-bit RGB payloads, simple scenes.
- **Hexagon Light**: hue/saturation payloads, extended scenes (~100), music modes, schedules.

You choose the profile during config flow. The selected profile supplies command builders, effect list, and services.

## Installation

Option A (manual):
1.  Copy the `custom_components/sunset_light` directory to the `custom_components` directory of your Home Assistant configuration.
2.  Restart Home Assistant.

Option B (HACS):
1.  In HACS, open the ⋮ menu → Custom repositories.
2.  Add this repo URL and set type to “Integration”.
3.  Install “Sunset Light” from HACS.
4.  Restart Home Assistant.

## Configuration

1. Go to **Settings** → **Devices & Services**.
2. Click **+ Add Integration**, search for “Sunset Light,” and select it.
3. In the config flow:
   - If your light is discovered, pick it from the dropdown (name + MAC). The profile (Sunset/Hexagon) will be guessed but can be overridden.
   - Or choose “Manual entry” and enter the Bluetooth MAC plus the profile.
4. Submit to create the entry. A light entity is added; Hexagon-only services are available under the `light` domain (see Services below).

## Usage

After setup, Home Assistant creates a light entity. Standard HA light controls (on/off, brightness, color, effect) work using the selected profile’s command format. Hexagon-only actions are exposed as entity services (below).

## Services (light domain)

- `light.set_scene_id` (Hexagon): call a scene by numeric ID, optional `scene_param`.
- `light.set_music_mode` (Hexagon): mode number 1–6 or name (`spectrum1/2/3`, `flowing`, `rolling`, `rhythm`).
- `light.set_music_sensitivity` (Hexagon): 0–100.
- `light.set_schedule` (Hexagon): fields `on_enabled`, `on_hour`, `on_minute`, `on_days_mask`, `off_enabled`, `off_hour`, `off_minute`, `off_days_mask` (day mask bit0=Mon … bit6=Sun; 0x7F = every day; masks can be int or list of weekday names).

## Scenes / effects

- Sunset profile: effect list matches the original device’s scenes.
- Hexagon profile: Classic, Festival, and extended “Other” scenes are exposed by name; you can also use `set_scene_id` for any numeric ID.

## Testing / debug helpers

- `scripts/ble_baseline.py`: scan, connect, dump services, listen to notifications, send raw writes. Use `--profile sunset_light` or `--profile hexagon_light`, and optional flags: `--scene-id`, `--music-mode`, `--music-sensitivity`, `--on-time/--off-time` with day masks.
- `scripts/extract_scene_order.py`: parse PacketLogger text export to list scene IDs in order.

## Adding a new profile

1. Create a subclass of `ProtocolProfile` in `custom_components/sunset_light/protocol.py` that implements `build_power/color/brightness/scene` (and optional music/schedule).
2. Add it to `list_profiles` and `get_profile`.
3. Provide an effect list and any scene ID/name mappings.
4. Extend `services.yaml` if the profile introduces new entity services.
5. Add tests for packet builders in `tests/test_protocol.py`.

## Protocol notes

- BLE service: `0000fff0-0000-1000-8000-00805f9b34fb`
- Write characteristic: `0000fff3-0000-1000-8000-00805f9b34fb`
- Notify characteristic: `0000fff4-0000-1000-8000-00805f9b34fb`
- Packet format: `0x55` + `cmd` + `0xFF` + `length` + `payload` + checksum (one’s complement of folded sum).
- Sunset: RGB bytes, brightness 0–100, simple scenes.
- Hexagon: hue (0–360) + saturation (0–1000), brightness 0–1000, scene ID + speed param, music modes 1–6, schedules via cmd 0x0A.
