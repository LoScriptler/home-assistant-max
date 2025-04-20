"""Piattaforma Button per Max For Home: apre il portone con un click."""

from __future__ import annotations

import logging
from typing import Final

import aiohttp
from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, CONF_EMAIL, CONF_PASSWORD, CONF_DEVICE_CODE

_LOGGER = logging.getLogger(__name__)

# Endpoint API fisso; se preferisci renderlo configurabile, spostalo in const.py
API_ENDPOINT: Final = "https://munl.altervista.org/GestioneAccountMAX/GestioneApplicativi/GetData.php"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Crea il pulsante per la Config Entry corrente."""
    data = hass.data[DOMAIN][entry.entry_id]

    email = data[CONF_EMAIL]
    password = data[CONF_PASSWORD]
    device_code = data[CONF_DEVICE_CODE]

    async_add_entities(
        [MaxDoorButton(hass, device_code, email, password)],
        update_before_add=False,
    )


class MaxDoorButton(ButtonEntity):
    """Rappresenta il pulsante 'Apri porta'."""

    _attr_should_poll = False
    _attr_has_entity_name = True  # mostra solo “Door 123456” nella UI

    def __init__(
        self,
        hass: HomeAssistant,
        device_code: str,
        email: str,
        password: str,
    ) -> None:
        self.hass = hass
        self._device_code = device_code
        self._email = email
        self._password = password

        self._attr_unique_id = f"max_door_{device_code}"
        self._attr_name = f"Door {device_code}"

    async def async_press(self) -> None:
        """Invia la richiesta HTTP per aprire la porta."""
        session = aiohttp_client.async_get_clientsession(self.hass)
        payload = {
            "mail1": self._email,
            "pwd1": self._password,
            "code": self._device_code,
            "type": 4,
        }

        try:
            async with session.post(API_ENDPOINT, json=payload) as resp:
                if resp.status == 200:
                    _LOGGER.debug("Porta %s aperta con successo", self._device_code)
                else:
                    body = await resp.text()
                    _LOGGER.error(
                        "Errore apertura porta %s: %s – %s",
                        self._device_code,
                        resp.status,
                        body,
                    )
        except aiohttp.ClientError as err:
            _LOGGER.error(
                "Errore di rete durante l'apertura della porta %s: %s",
                self._device_code,
                err,
            )
