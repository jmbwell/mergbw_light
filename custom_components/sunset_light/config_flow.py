"""Config flow for Sunset Light."""
import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components import bluetooth
from homeassistant.const import CONF_MAC

from .const import CONF_PROFILE, DEFAULT_PROFILE, DOMAIN
from .protocol import list_profiles, PROFILE_HEXAGON

_LOGGER = logging.getLogger(__name__)

class SunsetLightConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Sunset Light."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def _discover_devices(self):
        service_uuid = "0000fff0-0000-1000-8000-00805f9b34fb"
        devices = {}
        for info in bluetooth.async_discovered_service_info(self.hass, connectable=True):
            if service_uuid.lower() not in {s.lower() for s in info.service_uuids}:
                continue
            label = f"{info.name or 'Unknown'} ({info.address})"
            devices[label] = info.address
        return devices

    def _guess_profile(self, name: str) -> str:
        lower = (name or "").lower()
        if "hexagon" in lower:
            return PROFILE_HEXAGON
        return DEFAULT_PROFILE

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            mac = user_input.get(CONF_MAC)
            if not mac and user_input.get("discovered_device"):
                mac = user_input["discovered_device"]
            if not mac:
                errors["base"] = "no_mac"
            else:
                await self.async_set_unique_id(mac)
                self._abort_if_unique_id_configured()
                if user_input.get("discovered_device") and user_input.get(CONF_PROFILE) == DEFAULT_PROFILE:
                    guessed = self._guess_profile(user_input.get("discovered_device", ""))
                    user_input[CONF_PROFILE] = guessed
                user_input[CONF_MAC] = mac
                return self.async_create_entry(title="Sunset Light", data=user_input)

        profile_options = {key: label for key, label in list_profiles()}
        discovered = self._discover_devices()
        data_schema = {
            vol.Required(CONF_PROFILE, default=DEFAULT_PROFILE): vol.In(profile_options),
            vol.Optional(CONF_MAC): str,
        }
        if discovered:
            data_schema[vol.Optional("discovered_device", default=None)] = vol.In(discovered)
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(data_schema),
            errors=errors,
        )
