"""Config flow for MeRGBW Light."""
import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components import bluetooth
from homeassistant.const import CONF_MAC
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
)

from .const import (
    CONF_AVAILABILITY_TIMEOUT,
    CONF_PROFILE,
    DEFAULT_AVAILABILITY_TIMEOUT,
    DOMAIN,
    SERVICE_UUID,
)
from .protocol import list_profiles, PROFILE_HEXAGON

_LOGGER = logging.getLogger(__name__)

class MeRGBWLightConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for MeRGBW Light."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    @staticmethod
    def async_get_options_flow(config_entry):
        return MeRGBWLightOptionsFlow(config_entry)

    def _discover_devices(self):
        service_uuid = SERVICE_UUID
        devices = {}
        for info in bluetooth.async_discovered_service_info(self.hass, connectable=True):
            uuids = {s.lower() for s in (info.service_uuids or [])}
            name = info.name or ""
            if service_uuid.lower() not in uuids and not any(
                hint in name.lower() for hint in ("hexagon", "sunset")
            ):
                continue
            label = f"{info.name or 'Unknown'} ({info.address})"
            devices[label] = info.address
        return devices

    def _guess_profile(self, name: str) -> str:
        lower = (name or "").lower()
        if "hexagon" in lower:
            return PROFILE_HEXAGON
        return DEFAULT_PROFILE

    async def async_step_bluetooth(self, discovery_info):
        """Handle bluetooth discovery to auto-create an entry."""
        address = discovery_info.address
        name = discovery_info.name or "MeRGBW Light"
        await self.async_set_unique_id(address)
        self._abort_if_unique_id_configured()

        profile_key = self._guess_profile(discovery_info.name or "")
        return self.async_create_entry(
            title=name,
            data={
                CONF_MAC: address,
                CONF_PROFILE: profile_key,
                "device_source": "bluetooth",
            },
        )

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            source = user_input.get("device_source")
            mac = None
            profile_key = user_input.get(CONF_PROFILE, DEFAULT_PROFILE)
            if source == "manual":
                mac = user_input.get(CONF_MAC)
                if not mac:
                    errors["base"] = "no_mac"
                else:
                    await self.async_set_unique_id(mac)
                    self._abort_if_unique_id_configured()
                    user_input[CONF_MAC] = mac
                    return self.async_create_entry(title="MeRGBW Light", data=user_input)
            else:
                mac = self._discover_devices().get(source)
                if not mac:
                    errors["base"] = "no_mac"
                else:
                    # If profile left at default, guess based on the label.
                    if profile_key == DEFAULT_PROFILE:
                        guessed = self._guess_profile(source or "")
                        user_input[CONF_PROFILE] = guessed
                    user_input[CONF_MAC] = mac
                    await self.async_set_unique_id(mac)
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(title="MeRGBW Light", data=user_input)

        profile_options = {key: label for key, label in list_profiles()}
        discovered = self._discover_devices()
        if discovered:
            # Preselect first device and its guessed profile.
            first_label, first_addr = next(iter(discovered.items()))
            guessed_profile = self._guess_profile(first_label)
            device_options = [SelectOptionDict(value=label, label=label) for label in discovered.keys()]
            device_options.append(SelectOptionDict(value="manual", label="Manual entry"))
            data_schema = vol.Schema(
                {
                    vol.Required(
                        "device_source",
                        default=first_label,
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=device_options,
                            mode=SelectSelectorMode.DROPDOWN,
                            translation_key="device",
                        )
                    ),
                    vol.Required(
                        CONF_PROFILE,
                        default=guessed_profile,
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=[SelectOptionDict(value=k, label=v) for k, v in profile_options.items()],
                            mode=SelectSelectorMode.DROPDOWN,
                            translation_key="profile",
                        )
                    ),
                    vol.Optional(CONF_MAC): TextSelector(),
                }
            )
        else:
            data_schema = vol.Schema(
                {
                    vol.Required(
                        "device_source",
                        default="manual",
                    ): SelectSelector(
                            SelectSelectorConfig(
                                options=[SelectOptionDict(value="manual", label="Manual entry")],
                                mode=SelectSelectorMode.DROPDOWN,
                                translation_key="device",
                            )
                        ),
                    vol.Required(CONF_MAC): TextSelector(),
                    vol.Required(
                        CONF_PROFILE,
                        default=DEFAULT_PROFILE,
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=[SelectOptionDict(value=k, label=v) for k, v in profile_options.items()],
                            mode=SelectSelectorMode.DROPDOWN,
                            translation_key="profile",
                        )
                    ),
                }
            )
        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "helper": "Choose a discovered device or select 'Manual entry' and fill Bluetooth MAC + type.",
            },
        )


class MeRGBWLightOptionsFlow(config_entries.OptionsFlow):
    """Handle MeRGBW Light options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self._config_entry.options.get(
            CONF_AVAILABILITY_TIMEOUT, DEFAULT_AVAILABILITY_TIMEOUT
        )
        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_AVAILABILITY_TIMEOUT,
                    default=current,
                ): vol.All(int, vol.Range(min=30, max=3600)),
            }
        )
        return self.async_show_form(step_id="init", data_schema=data_schema)
