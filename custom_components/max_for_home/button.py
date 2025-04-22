from __future__ import annotations

import logging
from typing import Final

import httpx
from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    HVAC_MODE_HEAT, HVAC_MODE_OFF, SUPPORT_TARGET_TEMPERATURE
)

from .const import (
    DOMAIN,
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_DEVICE_CODE,
)

_LOGGER = logging.getLogger(__name__)

# Endpoint API
API_ENDPOINT: Final = (
    "https://munl.altervista.org/GestioneAccountMAX/GestioneApplicativi/GetData.php"
)

################################################################
# Funzioni per interagire con l'API
#################################################################

async def kind_verify(email: str, password: str, device_id: str) -> httpx.Response:
    """HTTP Request per verificare il tipo di dispositivo (type=16)."""
    _LOGGER.debug("Verifica tipo dispositivo: %s", device_id)

    data = {
        "mail1": email,
        "pwd1": password,
        "code": device_id,
        "type": 16,
    }

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(API_ENDPOINT, data=data)
        response.raise_for_status()
        _LOGGER.info("Tipo dispositivo %s verificato", device_id)
        return response
    

async def post_max(email: str, password: str, device_id: str, type: str) -> httpx.Response:
    """HTTP Request for opening the device."""
    _LOGGER.debug("Attempting to open device: %s", device_id)

    data = {
        "mail1": email,
        "pwd1": password,
        "code": device_id,
        "type": type,
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(API_ENDPOINT, data=data)  # <-- correct constant
            response.raise_for_status()
            _LOGGER.info("Device %s activated successfully", device_id)
            return response
    except Exception as err:
        _LOGGER.error(
            "Error activating device %s: %s", device_id, err, exc_info=True
        )
        raise


async def post_switch(email: str, password: str, device_id: str) -> httpx.Response:
    """HTTP Request per commutare un interruttore (type=4)."""
    _LOGGER.debug("Tentativo commutazione interruttore: %s", device_id)
    data = {
        "mail1": email,
        "pwd1": password,
        "code": device_id,
        "type": 4,
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(API_ENDPOINT, data=data)
        resp.raise_for_status()
        _LOGGER.info("Interruttore %s commutato", device_id)
        return resp


async def post_thermostat_control(email: str, password: str, device_id: str) -> httpx.Response:
    """HTTP Request identico a post_switch, usato per accendi/spegni termostato."""
    _LOGGER.debug("Comando termostato %s", device_id)
    return await post_switch(email, password, device_id)

############################################################
# Funzioni per l'integrazione con Home Assistant
############################################################

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    email = data[CONF_EMAIL]
    password = data[CONF_PASSWORD]
    device_code = data[CONF_DEVICE_CODE]

    # 1) Verifico il tipo remoto
    try:
        resp = await kind_verify(email, password, device_code)
        device_kind = resp.text.strip().lower()
    except Exception as err:
        _LOGGER.error("Impossibile determinare tipo dispositivo %s: %s", device_code, err)
        return

    entities = []

    # 2) In base al tipo, preparo le entity
    if device_kind == "cancello":
        entities.append(MaxGateButton(device_code, email, password))

    elif device_kind == "interruttore":
        entities.append(MaxDoorButton(device_code, email, password))

    elif device_kind == "termostato":
        entities.append([MaxThermostatEntity(device_code, email, password)], False)

    else:
        _LOGGER.warning("Tipo dispositivo %s non riconosciuto: %s", device_code, device_kind)
        return

    # 3) Aggiungo tutte le entità
    async_add_entities(entities, update_before_add=False)

#############################################################
# Definizione delle entità
#############################################################

class MaxGateButton(ButtonEntity):
    """Pulsante APRI per il cancello."""

    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(self, device_code: str, email: str, password: str) -> None:
        self._device_code = device_code
        self._email = email
        self._password = password
        self._attr_unique_id = f"max_door_{device_code}"
        self._attr_name = f"Cancello {device_code}"

    async def async_press(self) -> None:
        await post_max(self._email, self._password, self._device_code, "22")

class MaxDoorButton(ButtonEntity):
    """Button to enable interaction with the device."""

    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(self, device_code: str, email: str, password: str) -> None:
        self._device_code = device_code
        self._email = email
        self._password = password

        self._attr_unique_id = f"max_door_{device_code}"
        self._attr_name = f"Door {device_code}"

    async def async_press(self) -> None:
        """Start the door opening process."""
        await post_max(self._email, self._password, self._device_code, "4")


class MaxThermostatEntity(ClimateEntity):
    """Representa un unico dispositivo termostato con temperatura, umidità e accendi/spegni"""

    _attr_supported_features = SUPPORT_TARGET_TEMPERATURE
    _attr_hvac_modes = [HVAC_MODE_OFF, HVAC_MODE_HEAT]

    def __init__(self, device_code: str, email: str, password: str) -> None:
        self._device_code = device_code
        self._email = email
        self._password = password
        self._attr_unique_id = f"thermostat_{device_code}"
        self._attr_name = f"Termostato {device_code}"
        self._current_temperature = None
        self._target_temperature = None
        self._humidity = None
        self._hvac_mode = HVAC_MODE_OFF

    @property
    def current_temperature(self) -> float | None:
        return self._current_temperature

    @property
    def humidity(self) -> float | None:
        return self._humidity

    @property
    def hvac_mode(self) -> str:
        return self._hvac_mode

    @property
    def target_temperature(self) -> float | None:
        return self._target_temperature

    # async def async_update(self) -> None:
    #     # Recupera dati: tipo=16
    #     resp = await get_device_data(self._email, self._password, self._device_code, 16)
    #     data = resp.json()
    #     self._current_temperature = data.get("temperature")
    #     self._humidity = data.get("humidity")

    # async def async_set_hvac_mode(self, hvac_mode: str) -> None:
    #     if hvac_mode == HVAC_MODE_HEAT:
    #         # accendi: utiliza type=4
    #         await get_device_data(self._email, self._password, self._device_code, 4)
    #     else:
    #         # spegni: type=4 ma forse payload diverso se richiesto
    #         await get_device_data(self._email, self._password, self._device_code, 4)
    #     self._hvac_mode = hvac_mode
    #     self.async_write_ha_state()

    # async def async_set_temperature(self, **kwargs) -> None:
    #     # Se supportato, invia nuova temperatura target via API, se endpoint lo supporta
    #     temp = kwargs.get("temperature")
    #     if temp is not None:
    #         # type=5 ad esempio per set temperature (modifica se necessario)
    #         await get_device_data(self._email, self._password, self._device_code, 5)
    #         self._target_temperature = temp
    #         self.async_write_ha_state()
