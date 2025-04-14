import logging
import aiohttp
import asyncio
from homeassistant.components.button import ButtonEntity
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    data = hass.data[DOMAIN]
    email = data["email"]
    password = data["password"]
    endpoint = data["endpoint"]
    devices = data["devices"]

    buttons = [
        MaxDoorButton(device_id, endpoint, email, password)
        for device_id in devices if device_id
    ]
    async_add_entities(buttons, True)

class MaxDoorButton(ButtonEntity):
    def __init__(self, device_id, endpoint, email, password):
        self._device_id = device_id
        self._endpoint = endpoint
        self._email = email
        self._password = password
        self._attr_name = f"DOOR {device_id}"
        self._attr_unique_id = f"max_door_{device_id}"

    async def async_press(self) -> None:
        payload = {
            "mail1": self._email,
            "pwd1": self._password,
            "code": self._device_id,
            "type": 4,
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self._endpoint, json=payload) as resp:
                    if resp.status == 200:
                        _LOGGER.info(f"Apertura porta {self._device_id} riuscita.")
                    else:
                        _LOGGER.error(f"Errore apertura porta {self._device_id}: {resp.status}")
        except Exception as e:
            _LOGGER.exception(f"Errore durante la richiesta HTTP: {e}")
