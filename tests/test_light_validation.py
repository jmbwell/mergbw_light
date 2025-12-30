import sys
import types
from importlib import util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LIGHT_PATH = ROOT / "custom_components" / "mergbw" / "light.py"

# Stub HA modules needed for importing light.py without Home Assistant installed.
ha = types.ModuleType("homeassistant")
components = types.ModuleType("homeassistant.components")
light_mod = types.ModuleType("homeassistant.components.light")
bluetooth_mod = types.ModuleType("homeassistant.components.bluetooth")
config_entries = types.ModuleType("homeassistant.config_entries")

class ConfigEntry:
    pass

config_entries.ConfigEntry = ConfigEntry
const_mod = types.ModuleType("homeassistant.const")
core_mod = types.ModuleType("homeassistant.core")

class HomeAssistant:
    pass

core_mod.HomeAssistant = HomeAssistant
helpers_mod = types.ModuleType("homeassistant.helpers")
entity_platform = types.ModuleType("homeassistant.helpers.entity_platform")
cv_mod = types.ModuleType("homeassistant.helpers.config_validation")
event_mod = types.ModuleType("homeassistant.helpers.event")
exceptions_mod = types.ModuleType("homeassistant.exceptions")

class LightEntity:
    pass

class ColorMode:
    RGB = "rgb"

class LightEntityFeature:
    EFFECT = 1

light_mod.ATTR_BRIGHTNESS = "brightness"
light_mod.ATTR_RGB_COLOR = "rgb_color"
light_mod.ATTR_EFFECT = "effect"
light_mod.LightEntity = LightEntity
light_mod.ColorMode = ColorMode
light_mod.LightEntityFeature = LightEntityFeature

bluetooth_mod.async_ble_device_from_address = lambda *args, **kwargs: None

const_mod.CONF_MAC = "mac"
const_mod.EVENT_HOMEASSISTANT_STOP = "homeassistant_stop"
const_mod.WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

cv_mod.make_entity_service_schema = lambda value: value
cv_mod.string = str

class HomeAssistantError(Exception):
    pass

exceptions_mod.HomeAssistantError = HomeAssistantError

entity_platform.async_get_current_platform = lambda: None

def _async_call_later(*args, **kwargs):
    return lambda: None

event_mod.async_call_later = _async_call_later

# Voluptuous stub
vol_mod = types.ModuleType("voluptuous")
vol_mod.Required = lambda *args, **kwargs: None
vol_mod.Optional = lambda *args, **kwargs: None
vol_mod.Any = lambda *args, **kwargs: None
vol_mod.Range = lambda *args, **kwargs: None
vol_mod.In = lambda *args, **kwargs: None

# Bleak retry connector stub
bleak_retry = types.ModuleType("bleak_retry_connector")
bleak_retry.establish_connection = lambda *args, **kwargs: None
class BleakClientWithServiceCache:
    pass
bleak_retry.BleakClientWithServiceCache = BleakClientWithServiceCache

sys.modules.setdefault("homeassistant", ha)
sys.modules.setdefault("homeassistant.components", components)
sys.modules.setdefault("homeassistant.components.light", light_mod)
sys.modules.setdefault("homeassistant.components.bluetooth", bluetooth_mod)
sys.modules.setdefault("homeassistant.config_entries", config_entries)
sys.modules.setdefault("homeassistant.const", const_mod)
sys.modules.setdefault("homeassistant.core", core_mod)
sys.modules.setdefault("homeassistant.helpers", helpers_mod)
sys.modules.setdefault("homeassistant.helpers.entity_platform", entity_platform)
sys.modules.setdefault("homeassistant.helpers.config_validation", cv_mod)
sys.modules.setdefault("homeassistant.helpers.event", event_mod)
sys.modules.setdefault("homeassistant.exceptions", exceptions_mod)
sys.modules.setdefault("voluptuous", vol_mod)
sys.modules.setdefault("bleak_retry_connector", bleak_retry)

# Stub package modules so relative imports inside light.py work.
custom_components = types.ModuleType("custom_components")
custom_components.__path__ = [str(ROOT / "custom_components")]
sys.modules.setdefault("custom_components", custom_components)
mergbw_pkg = types.ModuleType("custom_components.mergbw")
mergbw_pkg.__path__ = [str(ROOT / "custom_components" / "mergbw")]
sys.modules.setdefault("custom_components.mergbw", mergbw_pkg)

light_spec = util.spec_from_file_location(
    "custom_components.mergbw.light",
    LIGHT_PATH,
)
light = util.module_from_spec(light_spec)
assert light_spec and light_spec.loader
light_spec.loader.exec_module(light)


class DummyHass:
    pass


def test_validate_scene_accepts_known_scene():
    entity = light.MeRGBWLight("00:11:22:33:44:55", "Test", DummyHass(), "sunset_light")
    entity._validate_scene("ghost")


def test_validate_scene_rejects_unknown_scene():
    entity = light.MeRGBWLight("00:11:22:33:44:55", "Test", DummyHass(), "sunset_light")
    with pytest.raises(HomeAssistantError):
        entity._validate_scene("not-a-scene")
