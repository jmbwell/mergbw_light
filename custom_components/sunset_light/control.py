
import asyncio
from bleak import BleakClient, BleakScanner

# UUIDs
SERVICE_UUID = "0000fff0-0000-1000-8000-00805f9b34fb"
CHARACTERISTIC_WRITEABLE = "0000fff3-0000-1000-8000-00805f9b34fb"

# Command codes
CMD_POWER_REQ = 0x01
CMD_SET_COLOR_REQ = 0x03
CMD_SET_BRIGHTNESS_REQ = 0x05
CMD_WHITE_OFF = 0x00
CMD_SET_SCENE = 0x06

# Command structure constants
CMD_HEAD = 0x55
CMD_SEQUENCE = 0xFF

def build_command(cmd_code: int, value: bytes = b'') -> bytes:
    """Builds a full command packet."""
    total_length = 5 + len(value)
    data_for_checksum = bytearray([CMD_HEAD, cmd_code, CMD_SEQUENCE, total_length]) + value
    
    s = sum(data_for_checksum)
    while s > 0xFF:
        s = (s >> 8) + (s & 0xFF)
        
    checksum = (~s) & 0xFF

    full_packet = data_for_checksum + bytes([checksum])
    return full_packet

# Try to import bleak_retry_connector for Home Assistant usage
try:
    from bleak_retry_connector import establish_connection, BleakClientWithServiceCache
    HAS_RETRY = True
except ImportError:
    HAS_RETRY = False

async def send_command(device, command: bytes):
    """Connects to the device and sends a command."""
    client = None
    try:
        # Check if we can use the robust connector (HA environment)
        if HAS_RETRY and hasattr(device, "address"):
            client = await establish_connection(BleakClientWithServiceCache, device, device.address)
            if client.is_connected:
                print(f"Sending command: {command.hex()} to {device.address}")
                await client.write_gatt_char(CHARACTERISTIC_WRITEABLE, command)
                print("Command sent.")
            else:
                print(f"Failed to connect to {device.address}")
        else:
            # Fallback for local testing or string address
            async with BleakClient(device) as client:
                if client.is_connected:
                    # Determine address for logging
                    address = device.address if hasattr(device, 'address') else device
                    print(f"Sending command: {command.hex()} to {address}")
                    await client.write_gatt_char(CHARACTERISTIC_WRITEABLE, command)
                    print("Command sent.")
                else:
                    address = device.address if hasattr(device, 'address') else device
                    print(f"Failed to connect to {address}")
    except Exception as e:
        print(f"Error sending command: {e}")
    finally:
        if client and HAS_RETRY and hasattr(device, "address"):
            await client.disconnect()

async def turn_on(device):
    """Turns the light on."""
    # Cmd 01 Data 01
    command = build_command(CMD_POWER_REQ, b'\x01')
    await send_command(device, command)

async def turn_off(device):
    """Turns the light off."""
    # Cmd 01 Data 00
    command = build_command(CMD_POWER_REQ, b'\x00')
    await send_command(device, command)

async def set_white(device):
    """Sets the light to white."""
    # Cmd 03 RGB 255,255,255
    command = build_command(CMD_SET_COLOR_REQ, bytes([255, 255, 255]))
    await send_command(device, command)

# Scene ID Mapping
# Verified by scene_hunt.py: IDs 0x80 to 0x94 work with Cmd 06.
# Mapping based on user provided list order.
SCENE_NAMES = [
    "fantasy", "sunset", "forest", "ghost", "sunrise", 
    "midsummer", "tropicaltwilight", "green prairie", "rubyglow", 
    "aurora", "savanah", "alarm", "lake placid", "neon", 
    "sundowner", "bluestar", "redrose", "rating", "disco", "autumn"
]

SCENE_PARAMS = {}
start_id = 0x80
for i, name in enumerate(SCENE_NAMES):
    SCENE_PARAMS[name] = (CMD_SET_SCENE, bytes([start_id + i]))

async def set_scene(device, scene_name: str):
    """Sets a predefined scene."""
    params = SCENE_PARAMS.get(scene_name.lower())
    if params:
        cmd, data = params
        command = build_command(cmd, data)
        await send_command(device, command)
    else:
        print(f"Unknown scene: {scene_name}")

async def set_color(device, r: int, g: int, b: int):
    """Sets the color of the light."""
    color_value = bytes([r, g, b])
    command = build_command(CMD_SET_COLOR_REQ, color_value)
    await send_command(device, command)

async def set_brightness(device, brightness: int):
    """Sets the brightness of the light."""
    brightness_value = bytes([brightness])
    command = build_command(CMD_SET_BRIGHTNESS_REQ, brightness_value)
    await send_command(device, command)
