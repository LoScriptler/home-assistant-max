import logging
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass, config):
    """Set up the Max For Home integration."""
    conf = config.get(DOMAIN)
    if conf is None:
        return True

    hass.data[DOMAIN] = {
        "token": conf.get("TOKEN"),
        "endpoint": conf.get("MAX_EP"),
        "email": conf.get("MAX_ACCOUNT_EMAIL"),
        "password": conf.get("MAX_ACCOUNT_PASSWORD"),
        "devices": [conf.get("MAX_DEVICE_1"), conf.get("MAX_DEVICE_2")],
    }

    hass.helpers.discovery.load_platform("button", DOMAIN, {}, config)
    return True
