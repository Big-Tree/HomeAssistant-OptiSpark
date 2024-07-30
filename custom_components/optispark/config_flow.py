"""Adds config flow for Optispark."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.selector import selector
from geopy.adapters import AioHTTPAdapter
from geopy.geocoders import Nominatim
import hashlib
import traceback

# from .api import (
#     OptisparkApiClientPostcodeError,
#     OptisparkApiClientUnitError,
# )
from . import OptisparkGetEntityError
from .const import DOMAIN, LOGGER
from . import get_entity, get_username
from .backend.exception.exceptions import OptisparkApiClientPostcodeError, OptisparkApiClientUnitError


class OptisparkFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Optispark."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self._been_here_before = False
        super().__init__(*args, **kwargs)

    def get_all_user_input(self, x: dict):
        """Merge in all user_input from all steps."""
        for step in self._user_input:
            for key in self._user_input[step]:
                x[key] = self._user_input[step][key]
        return x

    async def async_step_user(self, user_input: dict | None = None) -> config_entries.FlowResult:
        """Handle a flow initialized by the user."""
        self._been_here_before = False
        self._user_input = {}
        return await self.async_step_tariff(user_input)

    async def async_step_tariff(self, user_input: dict | None = None) -> config_entries.FlowResult:
        """Check that they are in the UK and on Octopus Agile."""
        errors = {}
        if user_input is not None:
            self._user_input['tariff'] = user_input
            return await self.async_step_heat_pump_details(user_input)

        data_schema = {}
        data_schema[vol.Required('country', default=self.hass.config.country)] = selector({
            'country': {
            }
        })
        default_tariff = 'Other' if self.hass.config.country != 'GB' else ''
        data_schema[vol.Required('tariff', default=default_tariff)] = selector({
            "select": {
                "options": ['Octopus Agile', 'Other'],
                "multiple": False}
        })

        return self.async_show_form(
            step_id="tariff",
            data_schema=vol.Schema(data_schema),
            errors=errors,
        )

    async def async_step_heat_pump_details(self, user_input: dict | None = None) -> config_entries.FlowResult:
        """Handle a flow initialized by the user."""
        errors = {}
        # Post code only needed if they're from the UK or on Octopus
        user_input = self.get_all_user_input(user_input)
        postcode_required = user_input['country'] == 'GB' or user_input['tariff'] == 'Octopus Agile'
        if 'climate_entity_id' in user_input:
            # User has submitted their input
            try:
                if postcode_required:
                    postcode = await self.test_postcode(user_input['postcode'])
                    await self.test_units(user_input['heat_pump_power_entity_id'])
                    user_input['postcode'] = postcode  # Fix postcode formating
                    user_input['address'] = user_input['address']
                    user_input['city'] = user_input['city']
                else:
                    user_input['postcode'] = None
                    user_input['address'] = None
                    user_input['city'] = None
                if 'external_temp_entity_id' not in user_input:
                    user_input['external_temp_entity_id'] = None

                self._user_input['heat_pump_details'] = user_input
                return await self.async_step_accept(user_input)
            except OptisparkApiClientPostcodeError as err:
                LOGGER.warning(err)
                errors["base"] = "postcode"
            except OptisparkApiClientUnitError as err:
                LOGGER.warning(err)
                errors["base"] = "unit"
            except OptisparkGetEntityError as err:
                LOGGER.error(err)
                errors["base"] = "get_entity"

        data_schema = {}
        if postcode_required:
            # Get post code from homeassistant
            try:
                async with Nominatim(
                    user_agent=self.flow_id,
                    adapter_factory=AioHTTPAdapter,
                ) as geolocator:
                    location = await geolocator.reverse((
                        self.hass.config.latitude,
                        self.hass.config.longitude))
                    postcode = location.raw['address']['postcode']
                    address = location.raw['address']['road']
                    city = location.raw['address']['city']
                if postcode == '' or postcode is None:
                    raise OptisparkApiClientPostcodeError()
            except Exception as err:
                LOGGER.warning(err)
                postcode = ''
                address = ''
                city = ''
                errors["base"] = "postcode_homeassistant"
            data_schema[vol.Required('postcode', default=postcode)] = str
            data_schema[vol.Required('address', default=address)] = str
            data_schema[vol.Required('city', default=city)] = str

        data_schema[vol.Required("climate_entity_id")] = selector({
            "entity": {
                'filter': {
                    'domain': 'climate'}
            }})
        data_schema[vol.Required("heat_pump_power_entity_id")] = selector({
            "entity": {
                'filter': {
                    'domain': 'sensor',
                    'device_class': 'power'}
            }})
        data_schema[vol.Optional("external_temp_entity_id")] = selector({
            "entity": {
                'filter': {
                    'domain': 'sensor',
                    'device_class': 'temperature'}
            }})

        return self.async_show_form(
            step_id="heat_pump_details",
            data_schema=vol.Schema(data_schema),
            errors=errors,
        )

    async def async_step_accept(self, user_input: dict | None = None, reject=False) -> config_entries.FlowResult:
        """Ask user to accept data usage."""
        errors = {}
        if 'accept_agreement' in user_input:
            if user_input['accept_agreement'] == ['Ok']:
                user_input = self.get_all_user_input(user_input)

                user_hash = f'{get_username(self.hass)}_{self.hass.config.latitude}_{self.hass.config.longitude}'
                user_hash = hashlib.sha256(user_hash.encode('utf-8')).hexdigest()
                user_input['user_hash'] = user_hash

                return self.async_create_entry(
                    title='OptiSpark Entry',
                    data=user_input)
            else:
                errors['base'] = 'accept_agreement'
        data_schema = {}
        data_schema[vol.Optional('accept_agreement')] = selector({
            "select": {
                "options": ['Ok'],
                "multiple": True}
        })
        if self._been_here_before is True and errors == {}:
            errors['base'] = 'accept_agreement'
        self._been_here_before = True
        return self.async_show_form(
            step_id="accept",
            data_schema=vol.Schema(data_schema),
            errors=errors,
        )

    async def test_postcode(self, postcode) -> str:
        """Use geopy to validate postcode.

        Geopy will throw an exception or evaluate to none if something is wrong.
        Returns formatted postcode.
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

    async def test_units(self, heat_pump_power_entity_id) -> None:
        """Validate units of heat pump power entity.

        The heat pump power usage entity should report that it uses either W or kW
        """
        power_entity = get_entity(self.hass, heat_pump_power_entity_id)
        try:
            unit = power_entity.native_unit_of_measurement
        except Exception as err:
            LOGGER.error(traceback.format_exc())
            raise OptisparkGetEntityError(err)
        accepted_units = ['W', 'kW']
        if unit not in accepted_units:
            raise OptisparkApiClientUnitError
