from __future__ import annotations

import logging
from typing import Final

import httpx
from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.climate import ClimateEntity, HVACMode
from homeassistant.components.climate import ClimateEntityFeature


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

async def get_device_data(
    email: str,
    password: str,
    device_id: str,
    type_code: int,
    extra: dict | None = None,
) -> httpx.Response:
    """Invia una richiesta POST all'API per il tipo specificato."""
    _LOGGER.debug("Request type=%s for device %s", type_code, device_id)
    data: dict[str, str | int] = {
        "mail1": email,
        "pwd1": password,
        "code": device_id,
        "type": type_code,
    }
    if extra:
        data.update(extra)
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(API_ENDPOINT, data=data)
        resp.raise_for_status()
        return resp

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

    entities: list[ButtonEntity | ClimateEntity] = []

    if device_kind == "cancello":
        entities.append(MaxGateButton(device_code, email, password))

    elif device_kind == "interruttore":
        entities.append(MaxDoorButton(device_code, email, password))

    elif device_kind == "termostato":
        # qui appendi *solo* l’entità Climate, senza lista o flag aggiuntivi
        entities.append(MaxThermostatEntity(device_code, email, password))

    else:
        _LOGGER.warning(
            "Tipo dispositivo non supportato: %s (device %s)",
            device_kind,
            device_code,
        )
        return

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
    """Unica entità per il termostato: temperatura, umidità, accendi/spegni e target."""

    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]

    def __init__(self, device_code: str, email: str, password: str) -> None:
        self._device_code = device_code
        self._email = email
        self._password = password
        self._attr_unique_id = f"thermostat_{device_code}"
        self._attr_name = f"Termostato {device_code}"
        self._current_temperature: float | None = None
        self._target_temperature: float | None = None
        self._humidity: float | None = None
        self._hvac_mode: HVACMode = HVACMode.OFF

    @property
    def temperature_unit(self) -> str:
        """Unità di misura della temperatura da configurazione HA."""
        return self.hass.config.units.temperature_unit

    @property
    def current_temperature(self) -> float | None:
        return self._current_temperature

    @property
    def current_humidity(self) -> float | None:
        return self._humidity

    @property
    def target_temperature(self) -> float | None:
        return self._target_temperature

    @property
    def hvac_mode(self) -> HVACMode:
        return self._hvac_mode

    async def async_update(self) -> None:
        """Richiesta 2: ottiene 'temp?hum?target?on?auto' e aggiorna stato."""
        try:
            resp = await get_device_data(self._email, self._password, self._device_code, 2)
            parts = resp.text.strip().split("?")
            if len(parts) >= 5:
                self._current_temperature = float(parts[0])
                self._humidity = float(parts[1])
                self._target_temperature = float(parts[2])
                self._hvac_mode = HVACMode.HEAT if parts[3] == "1" else HVACMode.OFF
                # parts[4] = auto (1) / manuale (0) – se vuoi usarlo, salvalo qui
        except Exception as err:
            _LOGGER.error("Errore update termostato %s: %s", self._device_code, err)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Richiesta 4 (accesо) o 3 (spegnimento)."""
        type_code = 4 if hvac_mode == HVACMode.HEAT else 3
        try:
            await get_device_data(self._email, self._password, self._device_code, type_code)
            self._hvac_mode = hvac_mode
            self.async_write_ha_state()
        except Exception as err:
            _LOGGER.error("Errore set HVAC mode %s a %s: %s", self._device_code, hvac_mode, err)

    async def async_set_temperature(self, **kwargs) -> None:
        """Richiesta 5: imposta la temperatura target (POST 'TempDR')."""
        temp = kwargs.get("temperature")
        if temp is None:
            return
        try:
            await get_device_data(
                self._email,
                self._password,
                self._device_code,
                5,
                extra={"TempDR": temp},
            )
            self._target_temperature = float(temp)
            self.async_write_ha_state()
        except Exception as err:
            _LOGGER.error("Errore set temperature %s a %s: %s", self._device_code, temp, err)