"""Adds config flow for Optispark."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import selector
from geopy.adapters import AioHTTPAdapter
from geopy.geocoders import Nominatim
import hashlib
import traceback

from .api import (
    OptisparkApiClientPostcodeError,
    OptisparkApiClientUnitError,
    OptisparkApiClient,
    OptisparkApiClientTimeoutError,
    OptisparkApiClientCommunicationError,
    OptisparkApiClientError
)
from . import OptisparkGetEntityError
from .const import DOMAIN, LOGGER
from . import const, get_entity, get_username
from .history import get_history, OptisparkGetHistoryError


class OptisparkFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Optispark."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self._been_here_before = False
        super().__init__(*args, **kwargs)

    async def async_step_user(self, user_input: dict | None = None) -> config_entries.FlowResult:
        """Handle a flow initialized by the user."""
        self._been_here_before = False
        return await self.async_step_init(user_input)

    async def async_step_accept(self, user_input: dict | None = None, reject=False) -> config_entries.FlowResult:
        """Ask user to accept data usage."""
        errors = {}
        if 'accept_agreement' in user_input:
            if user_input['accept_agreement'] == ['Accept']:
                tmp = self.user_input_init
                tmp['accept_agreement'] = user_input['accept_agreement']
                user_input = tmp

                user_hash = f'{user_input["username"]}_{self.hass.config.latitude}_{self.hass.config.longitude}'
                user_hash = hashlib.sha256(user_hash.encode('utf-8')).hexdigest()
                user_input['user_hash'] = user_hash

                try:
                    dynamo_data = await get_history(
                        hass=self.hass,
                        history_days=const.HISTORY_DAYS,
                        climate_entity_id=user_input['climate_entity_id'],
                        heat_pump_power_entity_id=user_input['heat_pump_power_entity_id'],
                        external_temp_entity_id=user_input['external_temp_entity_id'],
                        user_hash=user_hash,
                        include_user_info=False)
                    LOGGER.debug('************ Uploading history ***********')
                    tmp_client = OptisparkApiClient(
                        session=async_get_clientsession(self.hass))

                    await tmp_client.upload_history(dynamo_data)
                    LOGGER.debug('************ Upload complete ***********')

                except OptisparkApiClientTimeoutError:
                    errors['base'] = 'optispark_timeout_error'
                except OptisparkApiClientCommunicationError:
                    errors['base'] = 'optispark_communication_error'
                except OptisparkApiClientError:
                    errors['base'] = 'optispark_communication_error'
                except OptisparkGetHistoryError:
                    errors['base'] = 'optispark_history_error'

                if errors == {}:
                    return self.async_create_entry(
                        title='OptiSpark Entry',
                        data=user_input)
            else:
                errors['base'] = 'accept_agreement'
        data_schema = {}
        data_schema[vol.Optional('accept_agreement')] = selector({
            "select": {
                "options": ['Accept'],
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

    async def async_step_init(self, user_input: dict | None = None) -> config_entries.FlowResult:
        """Check that they are in the UK and Octopus Agile"""
        errors = {}
        if user_input is not None:
            try:
                postcode = await self._test_credentials(
                    postcode=user_input['postcode'],
                    heat_pump_power_entity_id=user_input['heat_pump_power_entity_id'])
                user_input['postcode'] = postcode  # Fix postcode formating
                if 'external_temp_entity_id' not in user_input:
                    user_input['external_temp_entity_id'] = None

                self.user_input_init = user_input
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
            errors["base"] = "postcode_homeassistant"

        data_schema = {
            vol.Required('username', default=get_username(self.hass)): str,
            #vol.Required('username'): str,
        }

        data_schema = {}
        data_schema[vol.Required('country', default=self.hass.config.country)] = selector({
            'country': {
            }
        })
        data_schema[vol.Optional('tariff')] = selector({
            "select": {
                "options": ['Octopus Agile', 'Other'],
                "multiple": False}
        })




        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(data_schema),
            errors=errors,
        )

    async def async_step_init_old(self, user_input: dict | None = None) -> config_entries.FlowResult:
        """Handle a flow initialized by the user."""
        errors = {}
        if user_input is not None:
            try:
                postcode = await self._test_credentials(
                    postcode=user_input['postcode'],
                    heat_pump_power_entity_id=user_input['heat_pump_power_entity_id'])
                user_input['postcode'] = postcode  # Fix postcode formating
                if 'external_temp_entity_id' not in user_input:
                    user_input['external_temp_entity_id'] = None

                self.user_input_init = user_input
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
            errors["base"] = "postcode_homeassistant"

        data_schema = {
            vol.Required('username', default=get_username(self.hass)): str,
            #vol.Required('username'): str,
        }

        data_schema[vol.Required('country', default=self.hass.config.country)] = selector({
            'country': {
            }
        })

        data_schema[vol.Required('postcode', default=postcode)] = str

        data_schema[vol.Required("climate_entity_id")] = selector({
            "entity": {
                'filter': {
                    'domain': 'climate'}
            }
        })
        data_schema[vol.Required("heat_pump_power_entity_id")] = selector({
            "entity": {
                'filter': {
                    'domain': 'sensor',
                    'device_class': 'power'}
            }
        })
        data_schema[vol.Optional("external_temp_entity_id")] = selector({
            "entity": {
                'filter': {
                    'domain': 'sensor',
                    'device_class': 'temperature'}
            }
        })

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(data_schema),
            errors=errors,
        )

    async def _test_credentials(self, postcode: str, heat_pump_power_entity_id) -> None:
        """Validate units and postcode.

        Use geopy to vilidate postcode. Geopy will throw an exception or evaluate to none if
        something is wrong.

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
