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
from homeassistant.const import CONF_MAC
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import service, entity_platform
import homeassistant.helpers.config_validation as cv
import voluptuous as vol

from .const import DOMAIN
from . import control

# Service schemas
SERVICE_SET_SCENE_SCHEMA = vol.Schema({
    vol.Required("scene_name"): cv.string,
})

SERVICE_SET_WHITE_SCHEMA = vol.Schema({})

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities,
):
    """Set up the Sunset Light platform."""
    mac_address = config_entry.data[CONF_MAC]
    async_add_entities([SunsetLight(mac_address, "Sunset Light", hass)])

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


class SunsetLight(LightEntity):
    """Representation of a Sunset Light."""

    _attr_supported_color_modes = {ColorMode.RGB}
    _attr_color_mode = ColorMode.RGB
    _attr_supported_features = LightEntityFeature.EFFECT
    _attr_effect_list = [
        "Fantasy", "Sunset", "Forest", "Ghost", "Sunrise", 
        "Midsummer", "Tropicaltwilight", "Green Prairie", "Rubyglow", 
        "Aurora", "Savanah", "Alarm", "Lake Placid", "Neon", 
        "Sundowner", "Bluestar", "Redrose", "Rating", "Disco", "Autumn"
    ]

    def __init__(self, mac, name, hass: HomeAssistant):
        """Initialize a Sunset Light."""
        self._mac = mac
        self._name = name
        self._is_on = None
        self._brightness = None
        self._rgb_color = None
        self._effect = None
        self._hass = hass

    @property
    def unique_id(self):
        """Return a unique ID."""
        return self._mac

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

    def _get_device(self):
        """Get the BLEDevice object or fallback to MAC."""
        device = bluetooth.async_ble_device_from_address(self._hass, self._mac, connectable=True)
        return device if device else self._mac

    async def async_turn_on(self, **kwargs):
        """Instruct the light to turn on."""
        await control.turn_on(self._get_device())
        self._is_on = True

        if ATTR_RGB_COLOR in kwargs:
            r, g, b = kwargs[ATTR_RGB_COLOR]
            await control.set_color(self._get_device(), r, g, b)
            self._rgb_color = (r, g, b)
            self._effect = None # Clear effect if color set manually
        elif ATTR_EFFECT in kwargs:
            effect = kwargs[ATTR_EFFECT]
            await control.set_scene(self._get_device(), effect)
            self._effect = effect
        else:
            # Keep current settings/defaults
            if self._rgb_color is None and self._effect is None:
                self._rgb_color = (255, 255, 255)

        if ATTR_BRIGHTNESS in kwargs:
            brightness = kwargs[ATTR_BRIGHTNESS]
            await control.set_brightness(self._get_device(), int(brightness / 255 * 100))
            self._brightness = brightness
        elif self._brightness is None:
             self._brightness = 255

        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        """Instruct the light to turn off."""
        await control.turn_off(self._get_device())
        self._is_on = False
        self.async_write_ha_state()

    async def async_handle_set_scene(self, scene_name: str):
        """Handle the set_scene service call."""
        _LOGGER.debug("Setting scene %s for %s", scene_name, self._name)
        await control.set_scene(self._get_device(), scene_name)
        self._effect = scene_name
        self.async_write_ha_state()

    async def async_handle_set_white(self):
        """Handle the set_white service call."""
        _LOGGER.debug("Setting %s to white", self._name)
        await control.set_white(self._get_device())
        self._rgb_color = (255, 255, 255)
        self._brightness = 255
        self._is_on = True
        self._effect = None
        self.async_write_ha_state()