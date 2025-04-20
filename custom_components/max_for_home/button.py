"""Piattaforma Button per Max For Home: invia una HTTP POST per aprire il dispositivo."""

from __future__ import annotations

import logging
from typing import Final

import httpx
from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_DEVICE_CODE,
)

_LOGGER = logging.getLogger(__name__)

# Endpoint API fisso (modifica se preferisci renderlo configurabile)
API_ENDPOINT: Final = (
    "https://munl.altervista.org/GestioneAccountMAX/GestioneApplicativi/GetData.php"
)


async def post_max(email: str, password: str, device_id: str) -> httpx.Response:
    """Invia la richiesta HTTP per aprire il dispositivo specificato."""
    _LOGGER.debug("Tentativo apertura dispositivo: %s", device_id)

    data = {
        "mail1": email,
        "pwd1": password,
        "code": device_id,
        "type": 4,
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(API_ENDPOINT, data=data)  # <‑‑ costante corretta
            response.raise_for_status()
            _LOGGER.info("Dispositivo %s attivato correttamente", device_id)
            return response
    except Exception as err:
        _LOGGER.error(
            "Errore attivazione dispositivo %s: %s", device_id, err, exc_info=True
        )
        raise


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Crea l'entità Button per la Config Entry corrente."""
    data = hass.data[DOMAIN][entry.entry_id]

    email = data[CONF_EMAIL]
    password = data[CONF_PASSWORD]
    device_code = data[CONF_DEVICE_CODE]

    async_add_entities(
        [MaxDoorButton(device_code, email, password)],
        update_before_add=False,
    )


class MaxDoorButton(ButtonEntity):
    """Entità Button che aziona il dispositivo Max."""

    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(self, device_code: str, email: str, password: str) -> None:
        self._device_code = device_code
        self._email = email
        self._password = password

        self._attr_unique_id = f"max_door_{device_code}"
        self._attr_name = f"Door {device_code}"

    async def async_press(self) -> None:
        """Aziona il dispositivo tramite POST."""
        await post_max(self._email, self._password, self._device_code)
