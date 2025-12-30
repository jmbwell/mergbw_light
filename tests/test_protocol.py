from importlib import util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / "custom_components" / "mergbw" / "protocol.py"
spec = util.spec_from_file_location("mergbw_protocol", PROTOCOL_PATH)
protocol = util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(protocol)
SunsetLightProfile = protocol.SunsetLightProfile
HexagonProfile = protocol.HexagonProfile
build_packet = protocol._build_packet  # noqa: SLF001
checksum = protocol._checksum  # noqa: SLF001


def test_sunset_packets():
    p = SunsetLightProfile()
    on_pkt = p.build_power(True)[0]
    off_pkt = p.build_power(False)[0]
    assert on_pkt[1] == 0x01 and on_pkt[-1] != 0  # checksum present
    assert off_pkt[1] == 0x01
    color_pkt = p.build_color(1, 2, 3)[0]
    assert color_pkt[1] == 0x03
    scene = p.build_scene("ghost")[0]
    assert scene[1] == 0x06


def test_hexagon_packets():
    p = HexagonProfile()
    on_pkt = p.build_power(True)[0]
    assert on_pkt[1] == 0x01
    color_pkt = p.build_color(255, 0, 0)[0]
    assert color_pkt[1] == 0x03
    scene_packets = p.build_scene("Symphony")
    assert scene_packets and scene_packets[0][1] == 0x06
    # Scene by id yields two packets: 0x06 and 0x0F
    by_id = p.build_scene_by_id(0x1234, 0x5678)
    assert by_id[0][1] == 0x06 and by_id[1][1] == 0x0F
    assert by_id[0][4:6] == b"\x12\x34"
    assert by_id[1][4:6] == b"\x56\x78"


def test_checksum_and_build_packet():
    payload = bytes([0xAA, 0xBB])
    pkt = build_packet(0x10, payload)
    # length = header(3) + length byte + payload(2) + checksum(1) = 7
    assert pkt[3] == 7
    assert pkt[-1] == checksum(pkt[:-1])


def test_sunset_brightness_bounds():
    p = SunsetLightProfile()
    # Brightness scales 0-255 into 0-100
    low_pkt = p.build_brightness(0)[0]
    high_pkt = p.build_brightness(400)[0]  # clamp to 100
    assert low_pkt[4] == 0
    assert high_pkt[4] == 100


def test_hexagon_color_and_brightness_scaling():
    p = HexagonProfile()
    color_pkt = p.build_color(255, 0, 0)[0]
    # Hue 0 deg -> 0x0000, sat 1000 -> 0x03E8
    assert color_pkt[4:6] == b"\x00\x00"
    assert color_pkt[6:8] == b"\x03\xE8"
    bright_pkt = p.build_brightness(255)[0]
    # Max HA brightness maps to 1000
    assert bright_pkt[4:6] == b"\x03\xE8"


def test_hexagon_unknown_scene_returns_empty():
    p = HexagonProfile()
    assert p.build_scene("not-a-scene") == []


def test_hexagon_music_and_schedule():
    p = HexagonProfile()
    mode_pkt = p.build_music_mode("rolling")[0]
    assert mode_pkt[1] == 0x07 and mode_pkt[4] == 5  # rolling -> 5
    sens_pkt = p.build_music_sensitivity(60)[0]
    assert sens_pkt[1] == 0x08 and sens_pkt[4] == 60
    sched_pkt = p.build_schedule(True, 10, 5, 0x03, False, 20, 10, 0x7F)[0]
    assert sched_pkt[1] == 0x0A
    assert sched_pkt[4:12] == bytes([1, 10, 5, 0x03, 0, 20, 10, 0x7F])
