"""Everything to do with getting the history.

Including:
    - heat pump temperatures, power usage
    - External temperature
All values in °F are converted to °C
All values in W are converted to kW
"""

from homeassistant.components.recorder.history import get_significant_states
from homeassistant.components.recorder.history import state_changes_during_period

from homeassistant.components.recorder.util import get_instance
from homeassistant.const import UnitOfTemperature
from homeassistant.helpers.entity_registry import RegistryEntry
from homeassistant.helpers.device_registry import DeviceRegistry
from homeassistant.helpers import entity_registry
from homeassistant.helpers import device_registry
from homeassistant.helpers import template
from datetime import datetime, timedelta, timezone
import json
from .const import LOGGER
from . import const


class OptisparkGetHistoryError(Exception):
    """Error getting heat pump history and user data."""


def to_celcius(x):
    """Convert from Farenheit to Celcius."""
    return (x-32) * 5/9


def optispark_integration_version(hass):
    """Get the version of the OptiSpark plugin.

    This will only work after entities have been initialised (not during config_flow)
    """
    device_id: str = template.device_id(hass, const.NAME)
    device_reg: DeviceRegistry = device_registry.async_get(hass).async_get(device_id)
    version = device_reg.model
    return version


def get_user_info(hass, heat_pump_entity_id, postcode, tariff):
    """Get user info."""
    heat_pump_entity_reg: RegistryEntry = entity_registry.async_get(hass).async_get(heat_pump_entity_id)
    heat_pump_device_id = heat_pump_entity_reg.device_id
    heat_pump_device_reg: DeviceRegistry = device_registry.async_get(hass).async_get(heat_pump_device_id)
    heat_pump_details = json.loads(heat_pump_device_reg.json_repr)

    home_assistant_details = {
        'version':   hass.config.as_dict()['version'],
        'time_zone': hass.config.as_dict()['time_zone'],
        'currency':  hass.config.as_dict()['currency'],
        'country':   hass.config.as_dict()['country'],
        'language':  hass.config.as_dict()['language']}
    home_assistant_details = home_assistant_details

    # Where can we get the integration version???  We can add that later
    return {'heat_pump_details': heat_pump_details,
            'home_assistant_details': home_assistant_details,
            'optispark_integration_version': optispark_integration_version(hass),
            'postcode': postcode,
            'tariff': tariff}


def climate_history(hass, state_changes):
    """Climate history.

    Home assistant logs the temperature states in whatever unit is set by the user (not the heat
    pump entity).  We only need to convert the temperature to °C if the user is using hh in °F mode.

    If the user toggles the hh temperature units, the past logs will be messed up.  The units will be
    incorrect, they will have been stored as the old unit but now read as the new unit.  Lets just hope
    people don't regularly swap their temperature units.
    """
    history = {}
    constant_attributes = {}  # Store attributes that would otherwise repeat in every time step
    hh_temp_units = hass.config.units.temperature_unit
    attributes_to_convert_to_celcius = ['current_temperature', 'target_temp_high', 'target_temp_low', 'temperature']
    for time_step in state_changes:
        if hh_temp_units == UnitOfTemperature.FAHRENHEIT:
            for key in attributes_to_convert_to_celcius:
                if key in time_step.attributes:
                    try:
                        time_step.attributes[key] = to_celcius(float(time_step.attributes[key]))
                    except Exception:
                        LOGGER.warn(f'Could not convert time_step.attributes[{key}] ({time_step.attributes[key]}) of type({type(time_step.attributes[key])}) to float')
                        continue
        elif hh_temp_units == UnitOfTemperature.CELSIUS:
            # Already in °C but still cast to float
            for key in attributes_to_convert_to_celcius:
                if key in time_step.attributes:
                    try:
                        time_step.attributes[key] = float(time_step.attributes[key])
                    except Exception:
                        LOGGER.warn(f'Could not convert time_step.attributes[{key}] ({time_step.attributes[key]}) of type({type(time_step.attributes[key])}) to float')
                        continue
        else:
            LOGGER.error(f'Heat pump uses unkown units ({hh_temp_units})')
            raise ValueError(f'Heat pump uses unkown units ({hh_temp_units})')

        history[time_step.last_updated] = {
            'state': time_step.state,
            'attributes': time_step.attributes}

    # Get attributes from most recent time_step
    constant_attributes = {
        'entity_id': state_changes[-1].entity_id,
        'attributes': state_changes[-1].attributes}

    return history, constant_attributes

def external_temp_history(_hass, state_changes):
    """External temperature history.

    The sensor will be displayed in whatever unit the sensor is set to. This is odd.  It ignores the
    hh setting and is different to the climate_entity.  I imagine this could change in the future.

    The unit is stored with each time step log, so we are fully able convert the history to °C.
    """
    history = {}
    constant_attributes = {}  # Store attributes that would otherwise repeat in every time step
    for time_step in state_changes:
        if time_step.state == '':
            LOGGER.warn(f'time_step ({time_step}) has no state value')
            continue
        if 'unit_of_measurement' not in time_step.attributes:
            LOGGER.warn(f'unit_of_measurement missing from time_step ({time_step})')
            continue
        unit = time_step.attributes['unit_of_measurement']
        state = time_step.state
        if unit == '°F':
            try:
                state = to_celcius(float(time_step.state))
            except Exception:
                LOGGER.warn(f'Could not convert state ({time_step.state}) of type({type(time_step.state)}) to float')
                continue
        elif unit == '°C':
            try:
                state = float(time_step.state)
            except Exception:
                LOGGER.warn(f'Could not convert state ({time_step.state}) of type({type(time_step.state)}) to float')
                continue
        else:
            LOGGER.error(f'External temperature sensor uses unkown units ({unit})')
            raise ValueError(f'External temperature sensor uses unkown units ({unit})')
        history[time_step.last_updated] = {
            'state': state,
            'attributes': {}}

    # Get attributes from most recent time_step
    constant_attributes = {
        'entity_id': state_changes[-1].entity_id,
        'attributes': state_changes[-1].attributes}

    return history, constant_attributes


def power_history(_hass, state_changes):
    """Heat pump power use history.

    Home assistant includes units in each power usage log.  There are no issues converting
    each time step to kW.  The unit recorded is that used by the sensor.
    """
    history = {}
    constant_attributes = {}  # Store attributes that would otherwise repeat in every time step
    for time_step in state_changes:
        if time_step.state == '':
            LOGGER.warn(f'time_step ({time_step}) has no state value')
            continue
        if 'unit_of_measurement' not in time_step.attributes:
            LOGGER.warn(f'unit_of_measurement missing from time_step ({time_step})')
            continue
        unit = time_step.attributes['unit_of_measurement']
        state = time_step.state
        if unit == 'W':
            try:
                state = float(state) / 1000
            except Exception:
                LOGGER.warn(f'Could not convert state ({state}) of type({type(state)}) to float')
                continue
        elif unit == 'kW':
            try:
                state = float(state)
            except Exception:
                LOGGER.warn(f'Could not convert state ({state}) of type({type(state)}) to float')
                continue
        else:
            LOGGER.warn(f'Heat pump uses unsupported units ({unit})')
            continue
        history[time_step.last_updated] = {
            'state': state,
            'attributes': {}}

    # Get attributes from most recent time_step
    constant_attributes = {
        'entity_id': state_changes[-1].entity_id,
        'attributes': state_changes[-1].attributes}

    return history, constant_attributes


async def get_state_changes(hass, entity_id, history_days):
    """History of state changes for entity_id."""
    start_time = datetime.now(tz=timezone.utc) - timedelta(days=history_days)
    end_time = datetime.now(tz=timezone.utc)
    filters = None
    include_start_time_state = False
    significant_changes_only = False
    minimal_response = False
    no_attributes = False
    compressed_state_format = False
    args = [
        hass,
        start_time,
        end_time,
        [entity_id],
        filters,
        include_start_time_state,
        significant_changes_only,
        minimal_response,
        no_attributes,
        compressed_state_format]
    state_changes = await get_instance(hass).async_add_executor_job(
        get_significant_states,
        *args)

    return state_changes[entity_id]


async def get_state_changes_period(hass, entity_id, history_days):
    """Trying out a different history function."""
    start_time = datetime.now(tz=timezone.utc) - timedelta(days=history_days)
    end_time = datetime.now(tz=timezone.utc)
    no_attributes = False
    descending = False
    limit = 99999
    include_start_time_state = False

    args = [
        hass,
        start_time,
        end_time,
        entity_id,
        no_attributes,
        descending,
        limit,
        include_start_time_state]
    state_changes = await get_instance(hass).async_add_executor_job(
        state_changes_during_period,
        *args)

    return state_changes[entity_id]


def states_to_histories(hass, column_name, state_changes):
    """Clean up history states.

    Extracts relevent information from the states and ensures that everything is in the right data
    type.
    """
    function_lookup = {
        const.DATABASE_COLUMN_SENSOR_CLIMATE_ENTITY: climate_history,
        const.DATABASE_COLUMN_SENSOR_HEAT_PUMP_POWER: power_history,
        const.DATABASE_COLUMN_SENSOR_EXTERNAL_TEMPERATURE: external_temp_history}
    histories, constant_attributes = function_lookup[column_name](
        hass,
        state_changes)
    return histories, constant_attributes


def histories_to_dynamo_data(hass, histories, constant_attributes, user_hash, heat_pump_entity_id,
                             postcode, tariff):
    """Package the history data so that it's ready for upload to lambda."""
    user_info = get_user_info(hass, heat_pump_entity_id, postcode, tariff)
    dynamo_data = {
        'histories': histories,
        'constant_attributes': constant_attributes,
        'user_info': user_info,
        'user_hash': user_hash}
    return dynamo_data


async def get_history(hass, history_days: int, climate_entity_id, heat_pump_power_entity_id,
                      external_temp_entity_id, user_hash, postcode, tariff, include_user_info):
    """Get <history_days> worth of historical data from relevant devices.

    include_user_info should be set to False in config_flow because the entities have not yet been
    initialised.

    It ensures units are in kW and °C
    """
    histories = {}
    constant_attributes = {}  # Store attributes that would otherwise repeat in every time step
    column_name_lookup = {
        heat_pump_power_entity_id: const.DATABASE_COLUMN_SENSOR_HEAT_PUMP_POWER,
        external_temp_entity_id: const.DATABASE_COLUMN_SENSOR_EXTERNAL_TEMPERATURE,
        climate_entity_id: const.DATABASE_COLUMN_SENSOR_CLIMATE_ENTITY}
    function_lookup = {
        climate_entity_id: climate_history,
        external_temp_entity_id: external_temp_history,
        heat_pump_power_entity_id: power_history}

    for entity_id in function_lookup:
        if entity_id is None:
            LOGGER.debug(f'({column_name_lookup[entity_id]}) entity missing, skipping...')
            continue
        column_name = column_name_lookup[entity_id]
        state_changes = await get_state_changes(hass, entity_id, history_days)
        histories[column_name], constant_attributes[column_name] = states_to_histories(
            hass,
            column_name,
            state_changes)


    dynamo_data = histories_to_dynamo_data(hass, histories, constant_attributes, user_hash,
                                           heat_pump_power_entity_id, postcode, tariff)
    return dynamo_data


async def get_earliest_and_latest_data_dates(hass, climate_entity_id, heat_pump_power_entity_id,
                                             external_temp_entity_id):
    """For each entity id find the earliest date that data has been recorded and the latest date.

    Does not check further back than const.DYNAMO_HISTORY_DAYS (5 years).
    """
    entity_id_to_column_name = {
        climate_entity_id: const.DATABASE_COLUMN_SENSOR_CLIMATE_ENTITY,
        heat_pump_power_entity_id: const.DATABASE_COLUMN_SENSOR_HEAT_PUMP_POWER,
        external_temp_entity_id: const.DATABASE_COLUMN_SENSOR_EXTERNAL_TEMPERATURE}

    earliest_dates = {}
    latest_dates = {}
    for entity_id in entity_id_to_column_name:
        if entity_id is None:
            LOGGER.debug(f'({entity_id_to_column_name[entity_id]}) entity missing, skipping...')
            continue
        state_changes = await get_state_changes(hass, entity_id, const.DYNAMO_HISTORY_DAYS)
        earliest_dates[entity_id_to_column_name[entity_id]] = state_changes[0].last_updated
        latest_dates[entity_id_to_column_name[entity_id]] = state_changes[-1].last_updated
    return earliest_dates, latest_dates
