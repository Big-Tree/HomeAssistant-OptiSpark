"""DataUpdateCoordinator for optispark."""
from __future__ import annotations

from datetime import timedelta, datetime
import pytz
import traceback

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.components.climate import HVACMode
from homeassistant.exceptions import ConfigEntryAuthFailed

from .api import (
    OptisparkApiClient,
    OptisparkApiClientAuthenticationError,
    OptisparkApiClientError,
)
from . import const
from . import get_entity
from . import get_history
from .const import LOGGER
from homeassistant.helpers.entity_registry import EntityRegistry, RegistryEntry
from homeassistant.helpers import entity_registry
from homeassistant.helpers import template


class OptisparkSetTemperatureError(Exception):
    """Error while setting the temperature of the heat pump."""


class OptisparkDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: OptisparkApiClient,
        climate_entity_id: str,
        heat_pump_power_entity_id: str,
        external_temp_entity_id: str,
        user_hash: str,
        postcode: str
    ) -> None:
        """Initialize."""
        self.client = client
        super().__init__(
            hass=hass,
            logger=const.LOGGER,
            name=const.DOMAIN,
            update_interval=timedelta(seconds=10),
        )
        self._postcode = postcode
        self._user_hash = user_hash
        self._climate_entity_id = climate_entity_id
        self._heat_pump_power_entity_id = heat_pump_power_entity_id
        self._external_temp_entity_id = external_temp_entity_id
        self._switch_enabled = False  # The switch will set this at startup
        self._available = False
        self._lambda_args = {
            const.LAMBDA_HOUSE_CONFIG: None,
            const.LAMBDA_SET_POINT: 20.0,
            const.LAMBDA_TEMP_RANGE: 3.0,
            const.LAMBDA_POSTCODE: self.postcode}
        self._lambda_update_handler = LambdaUpdateHandler(
            self.hass,
            self._climate_entity_id,
            self._heat_pump_power_entity_id,
            self._external_temp_entity_id,
            self._user_hash)

    async def update_heat_pump_temperature(self, data):
        """Set the temperature of the heat pump using the value from lambda."""
        temp: float = data[const.LAMBDA_TEMP]
        climate_entity = get_entity(self.hass, self._climate_entity_id)

        try:
            if climate_entity.hvac_mode == HVACMode.HEAT_COOL:
                await climate_entity.async_set_temperature(
                    target_temp_low=temp,
                    target_temp_high=climate_entity.target_temperature_high)
            else:
                await climate_entity.async_set_temperature(temperature=temp)
        except Exception as err:
            LOGGER.error(traceback.format_exc())
            raise OptisparkSetTemperatureError(err)

    def get_optispark_entities(self, include_switch=True) -> list[RegistryEntry]:
        """Get all entities registered to this integration.

        If include_switch is False, it won't be included in the list of entities returned.
        """
        entity_register: EntityRegistry = entity_registry.async_get(self.hass)
        device_id: str = template.device_id(self.hass, const.NAME)
        if device_id is None:
            # Id not found - this is the first time the integration has been initialised
            return []
        entities: list[RegistryEntry] = entity_registry.async_entries_for_device(
            entity_register,
            device_id,
            include_disabled_entities=True)
        if include_switch is False:
            # Remove the switch from the list so it doesn't get disabled
            for idx, entity in enumerate(entities):
                if entity.entity_id == 'switch.' + const.SWITCH_KEY:
                    idx_store = idx
            del entities[idx_store]
        return entities

    def enable_disable_entities(self, entities: list[RegistryEntry], enable: bool):
        """Enable/Disable all entities given in the list."""
        entity_register: EntityRegistry = entity_registry.async_get(self.hass)
        enable_lookup = {True: None, False: entity_registry.RegistryEntryDisabler.INTEGRATION}
        for entity in entities:
            entity_register.async_update_entity(entity.entity_id, disabled_by=enable_lookup[enable])

    def enable_disable_integration(self, enable: bool):
        """Enable/Disable all entities other than the switch."""
        entities = self.get_optispark_entities(include_switch=False)
        self.enable_disable_entities(entities, enable)
        self._switch_enabled = enable
        if enable is False:
            # The coordinator is available once data is fetched
            self._available = False
        #self.always_update = enable

    async def async_set_lambda_args(self, lambda_args):
        """Update the lambda arguments.

        To be called from entities.
        """
        self._lambda_args = lambda_args
        self._lambda_update_handler.manual_update = True
        await self.async_request_update()

    @property
    def postcode(self):
        """Postcode."""
        return self._postcode

    @property
    def house_temperature(self):
        """Power usage of the heat pump."""
        entity = get_entity(self.hass, self._climate_entity_id)
        out = entity.current_temperature
        return out

    @property
    def heat_pump_power_usage(self):
        """Power usage of the heat pump."""
        return get_entity(self.hass, self._heat_pump_power_entity_id).native_value

    @property
    def external_temp(self):
        """External house temperature."""
        if self._external_temp_entity_id is None:
            return None
        else:
            return get_entity(self.hass, self._external_temp_entity_id).native_value

    @property
    def lambda_args(self):
        """Returns the lamba arguments."""
        return self._lambda_args

    @property
    def available(self):
        """Is there data available for the entities."""
        return self._available

    async def async_request_update(self):
        """Request home assistant to update all its values.

        In certain scenarios, such as when the user makes a change on the front end, the front end
        won't update itself immediately.  This function can be called to request an update faster.
        """
        await self.async_request_refresh()


    async def _async_update_data(self):
        """Update data for entities.

        Returns the current setting for the heat pump for the current moment.
        Entire days heat pump profile will be stored if it's out of date.
        """
        if self._switch_enabled is False:
            # Integration is disabled, don't call lambda
            return self.data
        try:
            data = await self._lambda_update_handler(self.client, self.lambda_args)
            await self.update_heat_pump_temperature(data)
            self._available = True
            return data
        except OptisparkApiClientAuthenticationError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except OptisparkApiClientError as exception:
            raise UpdateFailed(exception) from exception


class LambdaUpdateHandler:
    """Returns the lambda data for the current time.

    It will call the lambda function once a day and store the results.
    """

    def __init__(self, hass, climate_entity_id, heat_pump_power_entity_id, external_temp_entity_id,
                 user_hash):
        """Init."""
        self.hass = hass
        self.climate_entity_id = climate_entity_id
        self.heat_pump_power_entity_id = heat_pump_power_entity_id
        self.external_temp_entity_id = external_temp_entity_id
        self.user_hash = user_hash
        self.london_tz = pytz.timezone('Europe/London')
        self.expire_time = datetime(1, 1, 1, 0, 0, 0, tzinfo=self.london_tz)  # Already expired
        self.manual_update = False

    async def __call__(self, client: OptisparkApiClient, lambda_args):
        """Return lambda data for the current time."""
        london_time_now = datetime.now(self.london_tz)
        # This probably won't result in a smooth transition
        if self.expire_time - london_time_now < timedelta(hours=0) or self.manual_update:
            await self.call_lambda(client, lambda_args)
        return self.get_closest_time()

    async def call_lambda(self, client: OptisparkApiClient, lambda_args):
        """Fetch data from AWS Lambda.

        Records the when the data expires (is no longer relevant).
        """
        LOGGER.debug(f'********** self.expire_time: {self.expire_time}')
        self.manual_update = False
        dynamo_data = await get_history(
            hass=self.hass,
            history_days=1,
            climate_entity_id=self.climate_entity_id,
            heat_pump_power_entity_id=self.heat_pump_power_entity_id,
            external_temp_entity_id=self.external_temp_entity_id,
            user_hash=self.user_hash)

        self.lambda_results = await client.async_get_data(lambda_args, dynamo_data)
        time_str = self.lambda_results[const.LAMBDA_OPTIMISED_DEMAND][-1]['x']
        self.expire_time = datetime.strptime(time_str, '%Y-%m-%d %H:%M')
        self.expire_time = self.expire_time.replace(tzinfo=self.london_tz)
        # The backend will currently only update upon a new day. FIX!
        self.expire_time = self.expire_time + timedelta(hours=1, minutes=30)
        LOGGER.debug(f'---------- self.expire_time: {self.expire_time}')

    def get_closest_time(self):
        """Get the closest matching time to now from the lambda data set provided."""
        time_based_keys = [
            const.LAMBDA_BASE_DEMAND,
            const.LAMBDA_PRICE,
            const.LAMBDA_TEMP,
            const.LAMBDA_OPTIMISED_DEMAND]
        non_time_based_keys = [
            const.LAMBDA_BASE_COST,
            const.LAMBDA_OPTIMISED_COST,
            const.LAMBDA_PROJECTED_PERCENT_SAVINGS]

        # Convert to dictionary where time is the key
        my_data = {}
        for key in time_based_keys:
            my_data[key] = {i['x']: i['y'] for i in self.lambda_results[key]}
            for key in non_time_based_keys:
                my_data[key] = self.lambda_results[key]

        # Convert time to dattime format
        times_str: list[str] = list(my_data['base_demand'].keys())
        times = [datetime.strptime(d, '%Y-%m-%d %H:%M') for d in times_str]
        now = datetime.now()
        absolute_difference = [abs(getattr(t-now, 'total_seconds')()) for t in times]
        min_idx = absolute_difference.index(min(absolute_difference))
        closest_time = times_str[min_idx]

        out = {}
        for key in time_based_keys:
            out[key] = my_data[key][closest_time]

        for key in non_time_based_keys:
            out[key] = my_data[key]
        return out



