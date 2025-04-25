from __future__ import annotations

import logging

import httpx
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD

from .const import DOMAIN, CONF_DEVICE_CODE, API_ENDPOINT

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required(CONF_DEVICE_CODE): str,  # es. "123456"
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow per l’integrazione MAX for Home."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, str] | None = None
    ) -> FlowResult:
        """Primo (e unico) step: richiedi email, password e device_code."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Proviamo a verificare connessione e creds con type=16
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
                    # resp.text conterrà "interruttore", "cancello" o "termostato"
                    kind = resp.text.strip().lower()
                    if kind not in {"interruttore", "cancello", "termostato"}:
                        errors["base"] = "invalid_device"
            except httpx.ConnectError:
                _LOGGER.exception("Impossibile connettersi all'endpoint")
                errors["base"] = "cannot_connect"
            except httpx.HTTPStatusError:
                _LOGGER.exception("Credenziali o device_code non validi")
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Errore imprevisto durante la verifica")
                errors["base"] = "unknown"
            else:
                # Tutto ok: creiamo l’entry
                return self.async_create_entry(
                    title=f"MAX Device {user_input[CONF_DEVICE_CODE]}",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
