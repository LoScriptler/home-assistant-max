import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from .const import DOMAIN, PLATFORMS

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict):
    """Supporto legacy YAML."""
    if DOMAIN not in config:
        return True
    hass.data[DOMAIN] = config[DOMAIN]
    # carica la piattaforma button in modalità discovery (deprecated ma ok per YAML)
    hass.helpers.discovery.async_load_platform("button", DOMAIN, {}, config)
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Future proof: setup via UI."""
    hass.data[DOMAIN] = entry.data
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
