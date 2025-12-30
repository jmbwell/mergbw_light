import sys
import types
from importlib import util
from pathlib import Path

import asyncio

ROOT = Path(__file__).resolve().parents[1]
CONTROL_PATH = ROOT / "custom_components" / "mergbw" / "control.py"

# Stub package modules so relative imports inside control.py work without importing HA.
custom_components = types.ModuleType("custom_components")
custom_components.__path__ = [str(ROOT / "custom_components")]
sys.modules.setdefault("custom_components", custom_components)
mergbw_pkg = types.ModuleType("custom_components.mergbw")
mergbw_pkg.__path__ = [str(ROOT / "custom_components" / "mergbw")]
sys.modules.setdefault("custom_components.mergbw", mergbw_pkg)

control_spec = util.spec_from_file_location(
    "custom_components.mergbw.control",
    CONTROL_PATH,
)
control = util.module_from_spec(control_spec)
assert control_spec and control_spec.loader
control_spec.loader.exec_module(control)


class DummyClient:
    def __init__(self):
        self.writes: list[tuple[str, bytes]] = []

    async def write_gatt_char(self, uuid: str, data: bytes):
        self.writes.append((uuid, data))


class DummyProfile:
    write_char_uuid = "uuid-write"

    def __init__(self):
        self.called = {}
        self.power_calls: list[bool] = []

    def build_power(self, on: bool):
        self.power_calls.append(on)
        self.called["power"] = on
        return [b"PON" if on else b"POFF"]

    def build_color(self, r: int, g: int, b: int):
        self.called["color"] = (r, g, b)
        return [b"COLOR"]

    def build_brightness(self, value: int):
        self.called["brightness"] = value
        return [b"BRIGHT"]

    def build_scene(self, name: str):
        self.called["scene"] = name
        return [b"SCENE"]


class OptionalProfile(DummyProfile):
    def build_scene_by_id(self, scene_id: int, param: int | None):
        self.called["scene_by_id"] = (scene_id, param)
        return [b"SCENEID"]

    def build_music_mode(self, mode):
        self.called["music_mode"] = mode
        return [b"MUSICMODE"]

    def build_music_sensitivity(self, value: int):
        self.called["music_sensitivity"] = value
        return [b"MUSICSENS"]

    def build_schedule(self, *args):
        self.called["schedule"] = args
        return [b"SCHEDULE"]


def test_basic_commands_send_packets():
    client = DummyClient()
    profile = DummyProfile()

    asyncio.run(control.turn_on(client, profile))
    asyncio.run(control.set_color(client, profile, 1, 2, 3))
    asyncio.run(control.set_brightness(client, profile, 200))
    asyncio.run(control.set_scene(client, profile, "Test"))
    asyncio.run(control.turn_off(client, profile))

    assert client.writes == [
        ("uuid-write", b"PON"),
        ("uuid-write", b"COLOR"),
        ("uuid-write", b"BRIGHT"),
        ("uuid-write", b"SCENE"),
        ("uuid-write", b"POFF"),
    ]
    assert profile.power_calls == [True, False]
    assert profile.called["color"] == (1, 2, 3)
    assert profile.called["brightness"] == 200
    assert profile.called["scene"] == "Test"


def test_optional_commands_run_when_available():
    client = DummyClient()
    profile = OptionalProfile()

    asyncio.run(control.set_scene_id(client, profile, 5, 10))
    asyncio.run(control.set_music_mode(client, profile, "flow"))
    asyncio.run(control.set_music_sensitivity(client, profile, 42))
    asyncio.run(control.set_schedule(client, profile, True, 7, 30, 0x01, False, 8, 15, 0x02))

    assert client.writes == [
        ("uuid-write", b"SCENEID"),
        ("uuid-write", b"MUSICMODE"),
        ("uuid-write", b"MUSICSENS"),
        ("uuid-write", b"SCHEDULE"),
    ]
    assert profile.called["scene_by_id"] == (5, 10)
    assert profile.called["music_mode"] == "flow"
    assert profile.called["music_sensitivity"] == 42
    assert profile.called["schedule"][0] is True


def test_optional_commands_skip_when_missing():
    client = DummyClient()
    profile = DummyProfile()

    asyncio.run(control.set_scene_id(client, profile, 1, None))
    asyncio.run(control.set_music_mode(client, profile, 2))
    asyncio.run(control.set_music_sensitivity(client, profile, 3))
    asyncio.run(control.set_schedule(client, profile, False, 0, 0, 0, False, 0, 0, 0))

    # No optional builders present; should not write anything
    assert client.writes == []
