"""Everything to do with getting the history.

Including:
    - heat pump temperatures, power usage
    - External temperature
All values in °F are converted to °C
All values in W are converted to kW
"""

from homeassistant.components.recorder.history import state_changes_during_period
from homeassistant.components.recorder.util import get_instance
from homeassistant.helpers.entity_registry import RegistryEntry
from homeassistant.helpers.device_registry import DeviceRegistry
from homeassistant.helpers import entity_registry
from homeassistant.helpers import device_registry
from homeassistant.helpers import template
from datetime import datetime, timedelta
import pytz
import json
from .const import LOGGER
from . import const
from . import get_entity


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


def get_user_info(hass, heat_pump_entity_id):
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
            'optispark_integration_version': optispark_integration_version(hass)}


def climate_history(hass, climate_entity_id, column_name, state_changes):
    """Climate history."""
    history = {}
    constant_attributes = {}  # Store attributes that would otherwise repeat in every time step
    heat_pump_unit = get_entity(hass, climate_entity_id).temperature_unit
    attributes_to_convert_to_celcius = ['current_temperature', 'target_temp_high', 'target_temp_low', 'temperature']
    for time_step in state_changes:
        if heat_pump_unit == '°F':
            for key in attributes_to_convert_to_celcius:
                if key in time_step.attributes:
                    try:
                        time_step.attributes[key] = to_celcius(float(time_step.attributes[key]))
                    except Exception:
                        LOGGER.warn(f'Could not convert time_step.attributes[{key}] ({time_step.attributes[key]}) of type({type(time_step.attributes[key])}) to float')
                        continue
        elif heat_pump_unit == '°C':
            # Already in °C but still cast to float
            for key in attributes_to_convert_to_celcius:
                if key in time_step.attributes:
                    try:
                        time_step.attributes[key] = float(time_step.attributes[key])
                    except Exception:
                        LOGGER.warn(f'Could not convert time_step.attributes[{key}] ({time_step.attributes[key]}) of type({type(time_step.attributes[key])}) to float')
                        continue
        else:
            LOGGER.error(f'Heat pump uses unkown units ({heat_pump_unit})')
            raise ValueError(f'Heat pump uses unkown units ({heat_pump_unit})')

        history[time_step.last_updated] = {
            'state': time_step.state,
            'attributes': time_step.attributes}

    # Get attributes from most recent time_step
    constant_attributes[column_name] = {
        'entity_id': state_changes[-1].entity_id,
        'attributes': state_changes[-1].attributes}

    return history, constant_attributes

def external_temp_history(_hass, _entity_id, column_name, state_changes):
    """External temperature history."""
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
    constant_attributes[column_name] = {
        'entity_id': state_changes[-1].entity_id,
        'attributes': state_changes[-1].attributes}

    return history, constant_attributes


def power_history(_hass, _entity_id, column_name, state_changes):
    """Heat pump power use history."""
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
    constant_attributes[column_name] = {
        'entity_id': state_changes[-1].entity_id,
        'attributes': state_changes[-1].attributes}

    return history, constant_attributes


async def get_state_changes(hass, entity_id, history_days):
    """History of state changes for entity_id."""
    start_time = pytz.UTC.localize(datetime.utcnow() - timedelta(days=history_days))
    end_time = pytz.UTC.localize(datetime.utcnow())
    args = [
        hass,
        start_time,
        end_time,
        entity_id]
    state_changes = await get_instance(hass).async_add_executor_job(
        state_changes_during_period,
        *args)
    return state_changes[entity_id]


async def get_history(hass, history_days: int, climate_entity_id, heat_pump_power_entity_id,
                      external_temp_entity_id, user_hash, include_user_info):
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
        column_name = column_name_lookup[entity_id]
        state_changes = await get_state_changes(hass, entity_id, history_days)
        histories[column_name], constant_attributes[column_name] = function_lookup[entity_id](
            hass,
            entity_id,
            column_name,
            state_changes)


    if include_user_info:
        user_info = get_user_info(hass, climate_entity_id)
    else:
        user_info = {}

    dynamo_data = {
        'histories': histories,
        'constant_attributes': constant_attributes,
        'user_info': user_info,
        'user_hash': user_hash}
    return dynamo_data
