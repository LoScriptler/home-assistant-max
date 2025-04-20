from homeassistant import config_entries
from .const import DOMAIN, CONF_EMAIL, CONF_PASSWORD, CONF_ENDPOINT, CONF_DEVICES

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="Max For Home", data=user_input)
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_EMAIL): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Required(CONF_ENDPOINT): str,
                vol.Required(CONF_DEVICES): str,
            }),
        )
