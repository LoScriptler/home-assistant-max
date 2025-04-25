from __future__ import annotations

import logging
from typing import Final

import httpx
from homeassistant.components.climate import (
    ClimateEntity,
    HVACMode,
    ClimateEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, CONF_EMAIL, CONF_PASSWORD, CONF_DEVICE_CODE

_LOGGER = logging.getLogger(__name__)
# Endpoint API
API_ENDPOINT: Final = (
    "https://munl.altervista.org/GestioneAccountMAX/GestioneApplicativi/GetData.php"
)


async def kind_verify(email: str, password: str, device_id: str) -> httpx.Response:
    data = {"mail1": email, "pwd1": password, "code": device_id, "type": 16}
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(API_ENDPOINT, data=data)
        resp.raise_for_status()
        return resp


async def get_device_data(
    email: str, password: str, device_id: str, type_code: int, extra: dict | None = None
) -> httpx.Response:
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


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    conf = hass.data[DOMAIN][entry.entry_id]
    email = conf[CONF_EMAIL]
    password = conf[CONF_PASSWORD]
    device_code = conf[CONF_DEVICE_CODE]

    try:
        resp = await kind_verify(email, password, device_code)
        device_kind = resp.text.strip().lower()
    except Exception as err:
        _LOGGER.error("Errore verify tipo %s: %s", device_code, err)
        return

    if device_kind != "termostato":
        return

    async_add_entities(
        [MaxThermostatEntity(device_code, email, password)],
        update_before_add=False,
    )


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
        return self.hass.config.units.temperature_unit

    @property
    def current_temperature(self) -> float | None:
        return self._current_temperature

    @property
    def humidity(self) -> float | None:
        return self._humidity

    @property
    def target_temperature(self) -> float | None:
        return self._target_temperature

    @property
    def hvac_mode(self) -> HVACMode:
        return self._hvac_mode

    async def async_update(self) -> None:
        try:
            resp = await get_device_data(
                self._email, self._password, self._device_code, 2
            )
            parts = resp.text.strip().split("?")
            if len(parts) >= 5:
                self._current_temperature = float(parts[0])
                self._humidity = float(parts[1])
                self._target_temperature = float(parts[2])
                self._hvac_mode = (
                    HVACMode.HEAT if parts[3] == "1" else HVACMode.OFF
                )
        except Exception as err:
            _LOGGER.error("Errore update termostato %s: %s", self._device_code, err)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        type_code = 4 if hvac_mode == HVACMode.HEAT else 3
        try:
            await get_device_data(
                self._email, self._password, self._device_code, type_code
            )
            self._hvac_mode = hvac_mode
            self.async_write_ha_state()
        except Exception as err:
            _LOGGER.error(
                "Errore set HVAC mode %s su %s: %s", self._device_code, hvac_mode, err
            )

    async def async_set_temperature(self, **kwargs) -> None:
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
            _LOGGER.error(
                "Errore set temperature %s a %s: %s", self._device_code, temp, err
            )
