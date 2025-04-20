import logging
from homeassistant.components.button import ButtonEntity
from homeassistant.helpers import aiohttp_client
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    data = hass.data[DOMAIN]
    email = data["max_account_email"]
    password = data["max_account_password"]
    endpoint = data["endpoint"]
    devices = data["devices"]

    buttons = [
        MaxDoorButton(hass, endpoint, email, password, dev_id)
        for dev_id in devices if dev_id
    ]
    async_add_entities(buttons, True)

class MaxDoorButton(ButtonEntity):
    """Rappresenta il pulsante di apertura porta."""

    _attr_should_poll = False

    def __init__(self, hass, endpoint, email, password, device_id):
        self.hass = hass
        self._endpoint = endpoint
        self._email = email
        self._password = password
        self._device_id = device_id
        self._attr_name = f"DOOR {device_id}"
        self._attr_unique_id = f"max_door_{device_id}"

    async def async_press(self) -> None:
        session = aiohttp_client.async_get_clientsession(self.hass)
        payload = {
            "mail1": self._email,
            "pwd1": self._password,
            "code": self._device_id,
            "type": 4,
        }
        try:
            async with session.post(self._endpoint, json=payload) as resp:
                if resp.status == 200:
                    _LOGGER.info("Apertura porta %s riuscita", self._device_id)
                else:
                    _LOGGER.error("Errore apertura porta %s: %s", self._device_id, resp.status)
        except Exception as err:
            _LOGGER.exception("Errore HTTP: %s", err)
