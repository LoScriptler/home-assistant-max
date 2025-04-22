from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from .const import DOMAIN, CONF_DEVICE_CODE

STEP_USER_DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_EMAIL): str,
    vol.Required(CONF_PASSWORD): str,
    vol.Required(CONF_DEVICE_CODE): str,   # es. 123456
})

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Confug flow for MAX for Home."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None):
        """Primo (e unico) step."""
        errors: dict[str, str] = {}

        if user_input is not None:

            return self.async_create_entry(
                title=f"Device {user_input[CONF_DEVICE_CODE]}",
                data=user_input, 
            )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
