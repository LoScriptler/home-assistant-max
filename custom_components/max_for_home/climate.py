from __future__ import annotations

import logging
from datetime import timedelta
from typing import Final

import httpx
from homeassistant.components.climate import (
    ClimateEntity,
    HVACMode,
    ClimateEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    CoordinatorEntity,
)

from .const import DOMAIN, CONF_EMAIL, CONF_PASSWORD, CONF_DEVICE_CODE

_LOGGER = logging.getLogger(__name__)

API_ENDPOINT: Final = (
    "https://munl.altervista.org/GestioneAccountMAX/GestioneApplicativi/GetData.php"
)


async def get_device_data(
    email: str,
    password: str,
    device_id: str,
    type_code: int,
    extra: dict | None = None,
) -> str:
    """Invia POST all’API per un dato type e ritorna il body come testo."""
    payload: dict[str, str | int] = {
        "mail1": email,
        "pwd1": password,
        "code": device_id,
        "type": type_code,
    }
    if extra:
        payload.update(extra)
    _LOGGER.debug("API request type=%s for device=%s extra=%s", type_code, device_id, extra)
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(API_ENDPOINT, data=payload)
        resp.raise_for_status()
        _LOGGER.debug("API response type=%s: %s", type_code, resp.text.strip())
        return resp.text


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Setup della piattaforma climate per i soli termostati."""
    conf = hass.data[DOMAIN][entry.entry_id]
    email = conf[CONF_EMAIL]
    password = conf[CONF_PASSWORD]
    device_code = conf[CONF_DEVICE_CODE]

    _LOGGER.debug("Setting up thermostat for device %s", device_code)
    try:
        kind = (await get_device_data(email, password, device_code, 16)).strip().lower()
        _LOGGER.info("Device %s kind verified: %s", device_code, kind)
        if kind != "termostato":
            return
    except Exception as err:
        _LOGGER.error("Cannot verify device type for %s: %s", device_code, err)
        return

    async def _async_update_data() -> dict[str, str]:
        """Esegue le richieste 2 e 17 e ritorna entrambi i risultati."""
        temp_text = await get_device_data(email, password, device_code, 2)
        conn_text = await get_device_data(email, password, device_code, 17)
        return {"temp": temp_text, "conn": conn_text}

    coordinator: DataUpdateCoordinator[dict[str, str]] = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"max_for_home_thermo_{device_code}",
        update_interval=timedelta(seconds=3),
        update_method=_async_update_data,
    )
    await coordinator.async_config_entry_first_refresh()

    async_add_entities(
        [MaxThermostatEntity(coordinator, email, password, device_code)],
        update_before_add=False,
    )
    _LOGGER.debug("Thermostat entity added for device %s", device_code)


class MaxThermostatEntity(CoordinatorEntity, ClimateEntity):
    """Entità termostato: temp, umidità, on/off, auto/manuale, connessione."""

    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE
    )
    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]
    _attr_preset_modes = ["auto", "manual"]

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[dict[str, str]],
        email: str,
        password: str,
        device_code: str,
    ) -> None:
        super().__init__(coordinator)
        self._email = email
        self._password = password
        self._device_code = device_code

        self._attr_unique_id = f"thermostat_{device_code}"
        self._attr_name = f"Termostato {device_code}"

        self._current_temperature: float | None = None
        self._target_temperature: float | None = None
        self._humidity: float | None = None
        self._hvac_mode: HVACMode = HVACMode.OFF
        self._preset_mode: str = "manual"
        self._is_connected: bool = False
        self._last_seen: str | None = None

        _LOGGER.debug("Initialized MaxThermostatEntity %s", device_code)
        self._parse(self.coordinator.data)

    @callback
    def _handle_coordinator_update(self) -> None:
        _LOGGER.debug("Coordinator update for %s: %s", self._device_code, self.coordinator.data)
        self._parse(self.coordinator.data)
        self.async_write_ha_state()

    def _parse(self, data: dict[str, str]) -> None:
        # Request 2: "temp?hum?target?on?auto"
        temp_parts = data["temp"].split("?")
        if len(temp_parts) >= 5:
            self._current_temperature = float(temp_parts[0])
            self._humidity = float(temp_parts[1])
            self._target_temperature = float(temp_parts[2])
            self._hvac_mode = HVACMode.HEAT if temp_parts[3] == "1" else HVACMode.OFF
            self._preset_mode = "auto" if temp_parts[4] == "1" else "manual"
            _LOGGER.info(
                "%s parsed: temp=%s°, hum=%s%%, target=%s°, hvac=%s, preset=%s",
                self._device_code,
                self._current_temperature,
                self._humidity,
                self._target_temperature,
                self._hvac_mode,
                self._preset_mode,
            )

        # Request 17: "connected?last_seen"
        conn_parts = data["conn"].split("?")
        if len(conn_parts) >= 2:
            self._is_connected = conn_parts[0] == "1"
            self._last_seen = conn_parts[1]
            _LOGGER.info(
                "%s connectivity: connected=%s, last_seen=%s",
                self._device_code,
                self._is_connected,
                self._last_seen,
            )

    @property
    def temperature_unit(self) -> str:
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

    @property
    def preset_mode(self) -> str | None:
        return self._preset_mode

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "humidity": self._humidity,
            "connected": self._is_connected,
            "last_seen": self._last_seen,
        }

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        code = 4 if hvac_mode == HVACMode.HEAT else 3
        _LOGGER.debug("Set HVAC mode %s (type=%s) for %s", hvac_mode, code, self._device_code)
        await get_device_data(self._email, self._password, self._device_code, code)
        self._hvac_mode = hvac_mode
        self.async_write_ha_state()
        _LOGGER.info("HVAC mode set to %s for %s", hvac_mode, self._device_code)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        man_auto = 1 if preset_mode == "auto" else 0
        _LOGGER.debug("Set preset_mode=%s (man_auto=%s) for %s", preset_mode, man_auto, self._device_code)
        await get_device_data(
            self._email,
            self._password,
            self._device_code,
            11,
            extra={"man_auto": man_auto},
        )
        self._preset_mode = preset_mode
        self.async_write_ha_state()
        _LOGGER.info("Preset mode set to %s for %s", preset_mode, self._device_code)

    async def async_set_temperature(self, **kwargs) -> None:
        temp = kwargs.get("temperature")
        if temp is None:
            return
        _LOGGER.debug("Set target_temperature=%s (type=5) for %s", temp, self._device_code)
        await get_device_data(
            self._email,
            self._password,
            self._device_code,
            5,
            extra={"TempDR": temp},
        )
        self._target_temperature = float(temp)
        self.async_write_ha_state()
        _LOGGER.info("Target temperature set to %s for %s", temp, self._device_code)
