"""Platform for light integration."""
import logging
import asyncio

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_RGB_COLOR,
    ATTR_EFFECT,
    LightEntity,
    ColorMode,
    LightEntityFeature,
)
from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MAC, EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import service, entity_platform
import homeassistant.helpers.config_validation as cv
from homeassistant.const import WEEKDAYS
import voluptuous as vol
from homeassistant.helpers.event import async_call_later

from bleak_retry_connector import establish_connection, BleakClientWithServiceCache

from .const import (
    CONF_PROFILE,
    DEFAULT_PROFILE,
    DOMAIN,
    SERVICE_SET_SCENE_ID,
    SERVICE_SET_MUSIC_MODE,
    SERVICE_SET_MUSIC_SENSITIVITY,
    SERVICE_SET_SCHEDULE,
)
from . import control
from .protocol import get_profile

# Service schemas
SERVICE_SET_SCENE_SCHEMA = cv.make_entity_service_schema({
    vol.Required("scene_name"): cv.string,
})

SERVICE_SET_WHITE_SCHEMA = cv.make_entity_service_schema({})

_LOGGER = logging.getLogger(__name__)
IDLE_DISCONNECT_SECONDS = 15

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities,
):
    """Set up the MeRGBW Light platform."""
    _LOGGER.info("async_setup_entry data=%s", config_entry.data)
    mac_address = config_entry.data[CONF_MAC]
    profile_key = config_entry.data.get(CONF_PROFILE, DEFAULT_PROFILE)
    light = MeRGBWLight(mac_address, "MeRGBW Light", hass, profile_key)
    async_add_entities([light])

    platform = entity_platform.async_get_current_platform()

    platform.async_register_entity_service(
        "set_scene",
        SERVICE_SET_SCENE_SCHEMA,
        "async_handle_set_scene",
    )
    platform.async_register_entity_service(
        "set_white",
        SERVICE_SET_WHITE_SCHEMA,
        "async_handle_set_white",
    )
    platform.async_register_entity_service(
        SERVICE_SET_SCENE_ID,
        cv.make_entity_service_schema(
            {
                vol.Required("scene_id"): int,
                vol.Optional("scene_param"): int,
            }
        ),
        "async_handle_set_scene_id",
    )
    platform.async_register_entity_service(
        SERVICE_SET_MUSIC_MODE,
        cv.make_entity_service_schema({vol.Required("mode"): vol.Any(int, str)}),
        "async_handle_set_music_mode",
    )
    platform.async_register_entity_service(
        SERVICE_SET_MUSIC_SENSITIVITY,
        cv.make_entity_service_schema({vol.Required("value"): vol.All(int, vol.Range(min=0, max=100))}),
        "async_handle_set_music_sensitivity",
    )
    platform.async_register_entity_service(
        SERVICE_SET_SCHEDULE,
        cv.make_entity_service_schema(
            {
                vol.Required("on_enabled"): bool,
                vol.Required("on_hour"): vol.All(int, vol.Range(min=0, max=23)),
                vol.Required("on_minute"): vol.All(int, vol.Range(min=0, max=59)),
                vol.Required("on_days_mask"): vol.Any(
                    vol.All(int, vol.Range(min=0, max=0x7F)),
                    [vol.In(WEEKDAYS)],
                ),
                vol.Required("off_enabled"): bool,
                vol.Required("off_hour"): vol.All(int, vol.Range(min=0, max=23)),
                vol.Required("off_minute"): vol.All(int, vol.Range(min=0, max=59)),
                vol.Required("off_days_mask"): vol.Any(
                    vol.All(int, vol.Range(min=0, max=0x7F)),
                    [vol.In(WEEKDAYS)],
                ),
            }
        ),
        "async_handle_set_schedule",
    )


class MeRGBWLight(LightEntity):
    """Representation of a MeRGBW Light."""

    _attr_supported_color_modes = {ColorMode.RGB}
    _attr_color_mode = ColorMode.RGB
    _attr_supported_features = LightEntityFeature.EFFECT
    _attr_icon = "mdi:hexagon-multiple-outline"

    def __init__(self, mac, name, hass: HomeAssistant, profile_key: str):
        """Initialize a MeRGBW Light."""
        self._mac = mac
        self._name = name
        self._is_on = None
        self._brightness = None
        self._rgb_color = None
        self._effect = None
        self._hass = hass
        self._client = None
        self._disconnect_timer = None
        self._command_lock = asyncio.Lock()
        self._profile_key = profile_key
        self._profile = get_profile(profile_key)
        self._attr_effect_list = self._profile.effect_list
        self._weekday_index = {day: idx for idx, day in enumerate(WEEKDAYS)}
        self._attr_available = True

    @property
    def unique_id(self):
        """Return a unique ID."""
        return self._mac

    @property
    def device_info(self):
        """Return device registry info."""
        return {
            "identifiers": {(DOMAIN, self._mac)},
            "connections": {("bluetooth", self._mac)},
            "name": self._name,
            "manufacturer": "MeRGBW",
            "model": self._profile.name,
        }

    @property
    def name(self):
        """Return the display name of this light."""
        return self._name

    @property
    def is_on(self):
        """Return true if light is on."""
        return self._is_on

    @property
    def brightness(self):
        """Return the brightness of the light."""
        return self._brightness

    @property
    def rgb_color(self):
        """Return the RGB color value."""
        return self._rgb_color
    
    @property
    def effect(self):
        """Return the current effect."""
        return self._effect

    async def _ensure_connected(self):
        """Ensure the BleakClient is connected."""
        if self._client and self._client.is_connected:
            return self._client

        device = bluetooth.async_ble_device_from_address(self._hass, self._mac, connectable=True)
        if not device:
            _LOGGER.error("Device %s not found via bluetooth registry", self._mac)
            raise Exception(f"Device {self._mac} not found")

        self._client = await establish_connection(
            BleakClientWithServiceCache,
            device,
            self._mac,
            disconnected_callback=self._on_disconnected,
        )
        return self._client

    def _on_disconnected(self, client):
        """Handle disconnection."""
        _LOGGER.info("Disconnected from %s", self._mac)
        self._client = None
        if self._disconnect_timer:
            self._disconnect_timer()
            self._disconnect_timer = None
        if self._hass:
            self._hass.async_create_task(self.async_write_ha_state())

    async def async_will_remove_from_hass(self):
        """Disconnect when removed."""
        if self._client:
            await self._client.disconnect()
        if self._disconnect_timer:
            self._disconnect_timer()
            self._disconnect_timer = None

    async def async_added_to_hass(self):
        """Set up lifecycle callbacks when added."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self._hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, self._async_handle_hass_stop)
        )

    async def _async_handle_hass_stop(self, _event):
        """Disconnect cleanly when HA stops."""
        if self._disconnect_timer:
            self._disconnect_timer()
            self._disconnect_timer = None
        if self._client:
            await self._client.disconnect()
            self._client = None
            self.async_write_ha_state()

    def _schedule_disconnect(self):
        """Schedule a disconnect after idle timeout."""
        if self._disconnect_timer:
            self._disconnect_timer()
        self._disconnect_timer = async_call_later(self._hass, IDLE_DISCONNECT_SECONDS, self._async_idle_disconnect)

    async def _async_idle_disconnect(self, _now):
        """Disconnect after idle period to free BLE resources."""
        self._disconnect_timer = None
        if self._client:
            await self._client.disconnect()
            self._client = None
            self.async_write_ha_state()

    async def _run_with_client(self, handler):
        """Serialize BLE writes and ensure connection."""
        async with self._command_lock:
            client = await self._ensure_connected()
            try:
                return await handler(client)
            finally:
                self._schedule_disconnect()

    async def async_turn_on(self, **kwargs):
        """Instruct the light to turn on."""
        await self._run_with_client(lambda client: control.turn_on(client, self._profile))
        self._is_on = True

        if ATTR_RGB_COLOR in kwargs:
            r, g, b = kwargs[ATTR_RGB_COLOR]
            await self._run_with_client(lambda client: control.set_color(client, self._profile, r, g, b))
            self._rgb_color = (r, g, b)
            self._effect = None
        elif ATTR_EFFECT in kwargs:
            effect = kwargs[ATTR_EFFECT]
            await self._run_with_client(lambda client: control.set_scene(client, self._profile, effect))
            self._effect = effect
        else:
            # Default behavior if just toggled on without params
            if self._rgb_color is None and self._effect is None:
                self._rgb_color = (255, 255, 255)

        if ATTR_BRIGHTNESS in kwargs:
            brightness = kwargs[ATTR_BRIGHTNESS]
            await self._run_with_client(lambda client: control.set_brightness(client, self._profile, brightness))
            self._brightness = brightness
        elif self._brightness is None:
             self._brightness = 255

        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        """Instruct the light to turn off."""
        await self._run_with_client(lambda client: control.turn_off(client, self._profile))
        self._is_on = False
        self.async_write_ha_state()

    async def async_handle_set_scene(self, scene_name: str):
        """Handle the set_scene service call."""
        await self._run_with_client(lambda client: control.set_scene(client, self._profile, scene_name))
        self._effect = scene_name
        self.async_write_ha_state()

    async def async_handle_set_white(self):
        """Handle the set_white service call."""
        await self._run_with_client(lambda client: control.set_white(client, self._profile))
        self._rgb_color = (255, 255, 255)
        self._brightness = 255
        self._is_on = True
        self._effect = None
        self.async_write_ha_state()

    async def async_handle_set_scene_id(self, scene_id: int, scene_param: int | None = None):
        """Set scene by numeric ID (Hexagon-only)."""
        await self._run_with_client(
            lambda client: control.set_scene_id(client, self._profile, scene_id, scene_param)
        )
        self._effect = f"Scene {scene_id}"
        self.async_write_ha_state()

    async def async_handle_set_music_mode(self, mode):
        """Set music mode (Hexagon-only)."""
        await self._run_with_client(lambda client: control.set_music_mode(client, self._profile, mode))

    async def async_handle_set_music_sensitivity(self, value: int):
        """Set music sensitivity 0-100 (Hexagon-only)."""
        await self._run_with_client(lambda client: control.set_music_sensitivity(client, self._profile, value))

    async def async_handle_set_schedule(
        self,
        on_enabled: bool,
        on_hour: int,
        on_minute: int,
        on_days_mask,
        off_enabled: bool,
        off_hour: int,
        off_minute: int,
        off_days_mask,
    ):
        """Set combined on/off schedule (Hexagon-only)."""
        def mask_from(value):
            if isinstance(value, int):
                return value
            mask = 0
            for day in value:
                idx = self._weekday_index.get(day)
                if idx is not None:
                    mask |= 1 << idx
            return mask

        await self._run_with_client(
            lambda client: control.set_schedule(
                client,
                self._profile,
                on_enabled,
                on_hour,
                on_minute,
                mask_from(on_days_mask),
                off_enabled,
                off_hour,
                off_minute,
                mask_from(off_days_mask),
            )
        )
