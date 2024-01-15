"""DataUpdateCoordinator for optispark."""
from __future__ import annotations

from datetime import timedelta, datetime
import pytz
import traceback

from homeassistant.core import HomeAssistant
import homeassistant.const
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
from . import history
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
        postcode: str,
        tariff: str
    ) -> None:
        """Initialize."""
        self.client = client
        super().__init__(
            hass=hass,
            logger=const.LOGGER,
            name=const.DOMAIN,
            update_interval=timedelta(seconds=10),
        )
        self._postcode = postcode if postcode is not None else 'AB11 6LU'
        self._tariff = tariff
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
            hass=self.hass,
            client=self.client,
            climate_entity_id=self._climate_entity_id,
            heat_pump_power_entity_id=self._heat_pump_power_entity_id,
            external_temp_entity_id=self._external_temp_entity_id,
            user_hash=self._user_hash,
            postcode=self._postcode,
            tariff=self._tariff)

    def convert_sensor_from_farenheit(self, entity, temp):
        """Ensure that the sensor returns values in Celcius.

        Only works with sensor entities
        If the sensor uses Farenheit then we'll need to convert Farenheit to Celcius
        """
        sensor_unit = entity.native_unit_of_measurement
        if sensor_unit == homeassistant.const.TEMP_CELSIUS:
            return temp
        elif sensor_unit == homeassistant.const.TEMP_FAHRENHEIT:
            # Convert temperature from Celcius to Farenheit
            return (temp-32) * 5/9
        else:
            raise ValueError(f'Heat pump uses unkown units ({sensor_unit})')

    def convert_climate_from_farenheit(self, entity, temp):
        """Ensure that the heat pump returns values in Celcius.

        Only works with climate entity
        If the heat_pump uses Farenheit then we'll need to convert Farenheit to Celcius
        """
        heat_pump_unit = entity.temperature_unit
        if heat_pump_unit == homeassistant.const.TEMP_CELSIUS:
            return temp
        elif heat_pump_unit == homeassistant.const.TEMP_FAHRENHEIT:
            # Convert temperature from Celcius to Farenheit
            return (temp-32) * 5/9
        else:
            raise ValueError(f'Heat pump uses unkown units ({heat_pump_unit})')

    def convert_climate_from_celcius(self, entity, temp):
        """Ensure that the heat pump is given a temperature in the correct units.

        Only works with climate entities.
        If the heat_pump uses Farenheit then we'll need to convert Celcius to Farenheit
        """
        heat_pump_unit = entity.temperature_unit
        if heat_pump_unit == homeassistant.const.TEMP_CELSIUS:
            return temp
        elif heat_pump_unit == homeassistant.const.TEMP_FAHRENHEIT:
            # Convert temperature from Celcius to Farenheit
            return temp*9/5 + 32
        else:
            raise ValueError(f'Heat pump uses unkown units ({heat_pump_unit})')

    async def update_heat_pump_temperature(self, data):
        """Set the temperature of the heat pump using the value from lambda."""
        temp: float = data[const.LAMBDA_TEMP]
        climate_entity = get_entity(self.hass, self._climate_entity_id)

        try:
            if self.heat_pump_target_temperature == temp:
                return
            LOGGER.debug('Change in target temperature!')
            if climate_entity.hvac_mode == HVACMode.HEAT_COOL:
                await climate_entity.async_set_temperature(
                    target_temp_low=self.convert_climate_from_celcius(climate_entity, temp),
                    target_temp_high=climate_entity.target_temperature_high)
            else:
                await climate_entity.async_set_temperature(
                    temperature=self.convert_climate_from_celcius(climate_entity, temp))
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
            idx_store = None
            for idx, entity in enumerate(entities):
                if entity.entity_id == 'switch.' + const.SWITCH_KEY:
                    idx_store = idx
            if idx_store is not None:
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
    def heat_pump_target_temperature(self):
        """The current target temperature that the heat pump is set to.

        Assumes that the heat pump is being used for heating.
        """
        climate_entity = get_entity(self.hass, self._climate_entity_id)
        match climate_entity.hvac_mode:
            case HVACMode.HEAT_COOL:
                temperature = climate_entity.target_temperature_low
            case _:
                temperature = climate_entity.target_temperature
        return temperature

    @property
    def house_temperature(self):
        """Internal temperature of the heat pump."""
        entity = get_entity(self.hass, self._climate_entity_id)
        out = self.convert_climate_from_farenheit(entity, entity.current_temperature)
        return out

    @property
    def heat_pump_power_usage(self):
        """Power usage of the heat pump.

        Return value in kW
        """
        entity = get_entity(self.hass, self._heat_pump_power_entity_id)
        native_value = entity.native_value
        match entity.unit_of_measurement:
            case 'W':
                return native_value/1000
            case 'kW':
                return native_value
            case _:
                LOGGER.error(f'Heat pump does not use supported unit({entity.unit_of_measurement})')
                raise TypeError(f'Heat pump does not use supported unit({entity.unit_of_measurement})')

    @property
    def external_temp(self):
        """External house temperature."""
        if self._external_temp_entity_id is None:
            return None
        else:
            entity = get_entity(self.hass, self._external_temp_entity_id)
            return self.convert_sensor_from_farenheit(entity, entity.native_value)

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
            data = await self._lambda_update_handler(self.lambda_args)
            await self.update_heat_pump_temperature(data)
            self._available = True
            return data
        except OptisparkApiClientAuthenticationError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except OptisparkApiClientError as exception:
            raise UpdateFailed(exception) from exception


class LambdaUpdateHandler:
    """Handles everything lambda.

    Gets the heating profile and ensure dynamo is up to date.
    """

    def __init__(self, hass, client: OptisparkApiClient, climate_entity_id,
                 heat_pump_power_entity_id, external_temp_entity_id, user_hash, postcode, tariff):
        """Init."""
        self.hass = hass
        self.client: OptisparkApiClient = client
        self.climate_entity_id = climate_entity_id
        self.heat_pump_power_entity_id = heat_pump_power_entity_id
        self.external_temp_entity_id = external_temp_entity_id
        self.user_hash = user_hash
        self.postcode = postcode
        self.tariff = tariff
        self.london_tz = pytz.timezone('Europe/London')
        self.expire_time = datetime(1, 1, 1, 0, 0, 0, tzinfo=self.london_tz)  # Already expired
        self.manual_update = False
        self.history_upload_complete = False
        self.id_to_column_name_lookup = {
            climate_entity_id: const.DATABASE_COLUMN_SENSOR_CLIMATE_ENTITY,
            heat_pump_power_entity_id: const.DATABASE_COLUMN_SENSOR_HEAT_PUMP_POWER,
            external_temp_entity_id: const.DATABASE_COLUMN_SENSOR_EXTERNAL_TEMPERATURE}
        # Entity ids will be None if they are optional and not enabled
        self.active_entity_ids = []
        for entity_id in [climate_entity_id, heat_pump_power_entity_id, external_temp_entity_id]:
            if entity_id is not None:
                self.active_entity_ids.append(entity_id)

    def get_missing_histories_boundary(self, history_states, dynamo_date):
        """Get index where history_state matches dynamo_date."""
        idx_bound= len(history_states)
        for idx, datum in enumerate(history_states):
            if datum.last_updated.replace(tzinfo=None) >= dynamo_date:
                idx_bound = idx
                break
        return idx_bound

    def get_missing_old_histories_states(self, history_states, column):
        """Get states that are older than anything in dynamo."""
        dynamo_date = self.dynamo_oldest_dates[column]
        if dynamo_date is None:
            # No data in dynamo
            dynamo_date = datetime(3000, 1)  # Everything will be old
        idx_bound = self.get_missing_histories_boundary(
            history_states,
            dynamo_date)
        return history_states[:idx_bound]

    def get_missing_new_histories_states(self, history_states, column):
        """Get states that are newer than anything in dynamo."""
        dynamo_date = self.dynamo_newest_dates[column]
        if dynamo_date is None:
            # No data in dynamo - upload first x days
            dynamo_date = datetime.now() - timedelta(days=const.HISTORY_DAYS)
        idx_bound = self.get_missing_histories_boundary(
            history_states,
            dynamo_date)
        return history_states[idx_bound+1:]

    async def upload_new_history(self):
        """Upload section of new history states that are older than anything in dynamo.

        self.dynamo_dates is updated so that if this function is called again a new section will be
        uploaded.
        const.MAX_UPLOAD_HISTORY_READINGS number of readings are uploaded to avoid long delay.
        """
        histories = {}
        constant_attributes = {}
        for active_entity_id in self.active_entity_ids:
            column = self.id_to_column_name_lookup[active_entity_id]
            history_states = await history.get_state_changes(
                self.hass,
                active_entity_id,
                const.DYNAMO_HISTORY_DAYS)
            missing_new_histories_states = self.get_missing_new_histories_states(history_states, column)

            LOGGER.debug(f'  column: {column}')
            if len(missing_new_histories_states) == 0:
                LOGGER.debug(f'    ({column}) - Upload complete')
                continue
            LOGGER.debug(f'    len(missing_new_histories_states): {len(missing_new_histories_states)}')
            missing_new_histories_states = missing_new_histories_states[:const.MAX_UPLOAD_HISTORY_READINGS]

            histories[column], constant_attributes[column] = history.states_to_histories(
                self.hass,
                column,
                missing_new_histories_states)
        if histories == {}:
            raise RuntimeError('No missing history data to upload')
        dynamo_data = history.histories_to_dynamo_data(
            self.hass,
            histories,
            constant_attributes,
            self.user_hash,
            self.climate_entity_id,
            self.postcode,
            self.tariff)
        self.dynamo_oldest_dates, self.dynamo_newest_dates = await self.client.upload_history(dynamo_data)

    async def upload_old_history(self):
        """Upload section of old history states that are older than anything in dynamo.

        self.dynamo_dates is updated so that if this function is called again a new section will be
        uploaded.
        const.MAX_UPLOAD_HISTORY_READINGS number of readings are uploaded to avoid long delay.
        """
        LOGGER.debug('Uploading portion of old history...')
        histories = {}
        constant_attributes = {}
        for active_entity_id in self.active_entity_ids:
            column = self.id_to_column_name_lookup[active_entity_id]
            history_states = await history.get_state_changes(
                self.hass,
                active_entity_id,
                const.DYNAMO_HISTORY_DAYS)
            missing_old_histories_states = self.get_missing_old_histories_states(history_states, column)

            LOGGER.debug(f'  column: {column}')
            if len(missing_old_histories_states) == 0:
                LOGGER.debug(f'    ({column}) - Upload complete')
                continue
            LOGGER.debug(f'    len(missing_old_histories_states): {len(missing_old_histories_states)}')
            missing_old_histories_states = missing_old_histories_states[-const.MAX_UPLOAD_HISTORY_READINGS:]

            histories[column], constant_attributes[column] = history.states_to_histories(
                self.hass,
                column,
                missing_old_histories_states)
        if histories == {}:
            self.history_upload_complete = True
            LOGGER.debug('History upload complete\n')
            return
        dynamo_data = history.histories_to_dynamo_data(
            self.hass,
            histories,
            constant_attributes,
            self.user_hash,
            self.climate_entity_id,
            self.postcode,
            self.tariff)
        self.dynamo_oldest_dates, self.dynamo_newest_dates = await self.client.upload_history(dynamo_data)

    async def __call__(self, lambda_args):
        """Return lambda data for the current time.

        Calls lambda if new heating profile is needed
        Otherwise, slowly uploads historical data
        """
        london_time_now = datetime.now(self.london_tz)
        # This probably won't result in a smooth transition
        if self.expire_time - london_time_now < timedelta(hours=0) or self.manual_update:
            await self.call_lambda(lambda_args)
        else:
            if self.history_upload_complete is False:
                await self.upload_old_history()
        return self.get_closest_time()

    async def update_dynamo_dates(self):
        """Call the lambda function and get the oldest and newest dates in dynamodb."""
        self.dynamo_oldest_dates, self.dynamo_newest_dates = await self.client.get_data_dates(
            dynamo_data={'user_hash': self.user_hash})

    async def update_ha_dates(self):
        """Get the oldest and newest dates in HA histories for active_entity_ids."""
        self.ha_oldest_dates, self.ha_newest_dates = await history.get_earliest_and_latest_data_dates(
            hass=self.hass,
            climate_entity_id=self.climate_entity_id,
            heat_pump_power_entity_id=self.heat_pump_power_entity_id,
            external_temp_entity_id=self.external_temp_entity_id)

    def is_new_data_missing_from_dynamo(self):
        """Is there any new data that needs to be uploaded.

        If there is data in HA histories for active_entity_ids that is newer than what is in dynamo,
        return True.
        """
        for active_entity_id in self.active_entity_ids:
            column = self.id_to_column_name_lookup[active_entity_id]
            if self.dynamo_newest_dates[column] is None:
                # First run, therefore data is missing
                LOGGER.debug(f'First run, upload ({const.HISTORY_DAYS}) days of history...\n')
                return True
            if self.dynamo_newest_dates[column] < self.ha_newest_dates[column]:
                LOGGER.debug(f'self.dynamo_newest_dates[{column}]: {self.dynamo_newest_dates[column]}')
                LOGGER.debug(f'self.ha_newest_dates[{column}]: {self.ha_newest_dates[column]}')
                return True
        return False

    async def call_lambda(self, lambda_args):
        """Fetch heating profile from AWS Lambda.

        Upload all new and missing data to dynamo first.
        If there is no data in dynamo, upload const.HISTORY_DAYS worth of data.
        Records the when the heating profile expires and should be refreshed.
        """
        LOGGER.debug(f'********** self.expire_time: {self.expire_time}')
        count = 0
        await self.update_dynamo_dates()
        await self.update_ha_dates()
        while self.is_new_data_missing_from_dynamo():
            count += 1
            LOGGER.debug(f'Updating dynamo with NEW data: round ({count})')
            await self.upload_new_history()
        LOGGER.debug('Upload of new history complete\n')

        self.lambda_results = await self.client.async_get_profile(lambda_args)

        time_str = self.lambda_results[const.LAMBDA_OPTIMISED_DEMAND][-1]['x']
        self.expire_time = datetime.strptime(time_str, '%Y-%m-%d %H:%M')
        self.expire_time = self.expire_time.replace(tzinfo=self.london_tz)
        # The backend will currently only update upon a new day. FIX!
        self.expire_time = self.expire_time + timedelta(hours=1, minutes=30)
        LOGGER.debug(f'---------- self.expire_time: {self.expire_time}')
        self.manual_update = False

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



