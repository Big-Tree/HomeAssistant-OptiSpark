"""Adds config flow for Blueprint."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.selector import selector
from .const import LOGGER

from .api import (
    OptisparkApiClient
)
from .const import DOMAIN


class OptisparkFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Blueprint."""

    VERSION = 1

    async def async_step_entity(
        self,
        user_input: dict | None = None,
    ) -> config_entries.FlowResult:
        """Handle a flow initialized by the user."""

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ) -> config_entries.FlowResult:
        """Handle a flow initialized by the user."""
        return await self.async_step_init(user_input)

    async def async_step_init(
        self,
        user_input: dict | None = None,
    ) -> config_entries.FlowResult:
        """Handle a flow initialized by the user."""
        _errors = {}
        if user_input is not None:
            await self._test_credentials(
                postcode=user_input['postcode'],
            )
            return self.async_create_entry(
                title='OptiSpark Entry',
                data=user_input,
            )

            #except OptisparkApiClientAuthenticationError as exception:
            #    LOGGER.warning(exception)
            #    _errors["base"] = "auth"
            #except OptisparkApiClientCommunicationError as exception:
            #    LOGGER.error(exception)
            #    _errors["base"] = "connection"
            #except OptisparkApiClientError as exception:
            #    LOGGER.exception(exception)
            #    _errors["base"] = "unknown"
            #else:
            #    return self.async_create_entry(
            #        title=user_input[CONF_USERNAME],
            #        data=user_input,
            #    )

        data_schema = {
            vol.Required('postcode'): str,
        }

        data_schema[vol.Required("climate_entity")] = selector({
            "entity": {
                'filter': {
                    'domain': 'climate'}
            }
        })

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(data_schema),
            errors=_errors,
        )

    async def _test_credentials(self, postcode: str) -> None:
        """Validate credentials."""
        pass

    async def _test_credentials_old(self, username: str, password: str) -> None:
        """Validate credentials."""
        client = OptisparkApiClient(
            username=username,
            password=password,
            session=async_create_clientsession(self.hass),
        )
        await client.async_get_data()
