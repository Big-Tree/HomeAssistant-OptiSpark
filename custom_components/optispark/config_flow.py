"""Adds config flow for Blueprint."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.selector import selector
from geopy.adapters import AioHTTPAdapter
from geopy.geocoders import Nominatim

from .api import (
    OptisparkApiClientPostcodeError
)
from .const import DOMAIN, LOGGER


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
            try:
                postcode = await self._test_credentials(postcode=user_input['postcode'])
                user_input['postcode'] = postcode  # Fix postcode formating
                return self.async_create_entry(
                    title='OptiSpark Entry',
                    data=user_input,
                )
            except OptisparkApiClientPostcodeError as err:
                LOGGER.warning(err)
                _errors["base"] = "postcode"

        # Get post code from homeassistant
        try:
            async with Nominatim(
                #user_agent="specify_your_app_name_here",
                user_agent=self.flow_id,
                adapter_factory=AioHTTPAdapter,
            ) as geolocator:
                location = await geolocator.reverse((
                    self.hass.config.latitude,
                    self.hass.config.longitude))
                postcode = location.raw['address']['postcode']
            if postcode == '' or postcode is None:
                raise OptisparkApiClientPostcodeError()
        except Exception as err:
            LOGGER.warning(err)
            postcode = ''
            _errors["base"] = "postcode_homeassistant"

        data_schema = {
            vol.Required('postcode', default=postcode): str,
        }
        data_schema[vol.Required("climate_entity")] = selector({
            "entity": {
                'filter': {
                    'domain': 'climate'}
            }
        })
        data_schema[vol.Required("heat_pump_power_entity")] = selector({
            "entity": {
                'filter': {
                    'domain': 'sensor',
                    'device_class': 'power'}
            }
        })
        data_schema[vol.Optional("external_temp_entity")] = selector({
            "entity": {
                'filter': {
                    'domain': 'sensor',
                    'device_class': 'temperature'}
            }
        })

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(data_schema),
            errors=_errors,
        )

    async def _test_credentials(self, postcode: str) -> None:
        """Use geopy to vilidate postcode.

        Geopy will throw an exception or evaluate to none if something is wrong.
        """
        try:
            async with Nominatim(
                #user_agent="specify_your_app_name_here",
                user_agent=self.flow_id,
                adapter_factory=AioHTTPAdapter,
            ) as geolocator:
                location = await geolocator.geocode(postcode)
                postcode = location.raw['name']
            if postcode == '' or postcode is None:
                raise OptisparkApiClientPostcodeError()
            return postcode
        except Exception:
            raise OptisparkApiClientPostcodeError('Error validation postcode')

    #async def _test_credentials_old(self, username: str, password: str) -> None:
    #    """Validate credentials."""
    #    client = OptisparkApiClient(
    #        username=username,
    #        password=password,
    #        session=async_create_clientsession(self.hass),
    #    )
    #    await client.async_get_data()
