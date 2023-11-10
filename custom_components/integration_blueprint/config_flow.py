"""Adds config flow for Blueprint."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .api import (
    IntegrationBlueprintApiClient,
    IntegrationBlueprintApiClientAuthenticationError,
    IntegrationBlueprintApiClientCommunicationError,
    IntegrationBlueprintApiClientError,
)
from .const import DOMAIN, LOGGER


class BlueprintFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Blueprint."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ) -> config_entries.FlowResult:
        """Handle a flow initialized by the user."""
        _errors = {}
        if user_input is not None:
            # Process the data
            pass
            await self._test_credentials(
                postcode=user_input['postcode'],
            )
            return self.async_create_entry(
                title=user_input['postcode'],
                data=user_input,
            )
            #except IntegrationBlueprintApiClientAuthenticationError as exception:
            #    LOGGER.warning(exception)
            #    _errors["base"] = "auth"
            #except IntegrationBlueprintApiClientCommunicationError as exception:
            #    LOGGER.error(exception)
            #    _errors["base"] = "connection"
            #except IntegrationBlueprintApiClientError as exception:
            #    LOGGER.exception(exception)
            #    _errors["base"] = "unknown"
            #else:
            #    return self.async_create_entry(
            #        title=user_input[CONF_USERNAME],
            #        data=user_input,
            #    )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required('postcode'): str,
                }
            ),
            errors=_errors,
        )

    async def _test_credentials(self, postcode: str) -> None:
        """Validate credentials."""
        pass

    async def _test_credentials_old(self, username: str, password: str) -> None:
        """Validate credentials."""
        client = IntegrationBlueprintApiClient(
            username=username,
            password=password,
            session=async_create_clientsession(self.hass),
        )
        await client.async_get_data()
