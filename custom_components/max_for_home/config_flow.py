from __future__ import annotations

import logging
import voluptuous as vol

import httpx
from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, CONF_DEVICE_CODE, API_ENDPOINT

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required(CONF_DEVICE_CODE): str,
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow per MAX for Home."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, str] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            # Provo la verifica via API type=16
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.post(
                        API_ENDPOINT,
                        data={
                            "mail1": user_input[CONF_EMAIL],
                            "pwd1": user_input[CONF_PASSWORD],
                            "code": user_input[CONF_DEVICE_CODE],
                            "type": 16,
                        },
                    )
                    resp.raise_for_status()
                    kind = resp.text.strip().lower()
                    if kind not in {"cancello", "interruttore", "termostato"}:
                        errors["base"] = "invalid_device"
            except httpx.ConnectError:
                _LOGGER.exception("cannot_connect")
                errors["base"] = "cannot_connect"
            except httpx.HTTPStatusError:
                _LOGGER.exception("invalid_auth")
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("unknown")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=f"MAX {user_input[CONF_DEVICE_CODE]} ({kind})",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
