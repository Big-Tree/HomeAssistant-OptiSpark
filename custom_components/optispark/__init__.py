"""Custom integration to integrate optispark with Home Assistant.

For more details about this integration, please refer to
https://github.com/Big-Tree/HomeAssistant-OptiSpark
"""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import template
from homeassistant.helpers import entity_registry
from homeassistant.helpers import device_registry
from homeassistant.helpers.entity_registry import RegistryEntry
from homeassistant.helpers.device_registry import DeviceRegistry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.components.recorder.history import state_changes_during_period
from homeassistant.components.recorder.util import get_instance
import json
from datetime import datetime, timedelta
from .api import OptisparkApiClient
from .const import DOMAIN
from .const import LOGGER
from . import const
import pytz
import traceback

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.NUMBER,
    Platform.CLIMATE
]


# https://developers.home-assistant.io/docs/config_entries_index/#setting-up-an-entry
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up this integration using UI."""
    from .coordinator import OptisparkDataUpdateCoordinator  # Prevent circular import
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator = OptisparkDataUpdateCoordinator(
        hass=hass,
        client=OptisparkApiClient(
            session=async_get_clientsession(hass)),
        climate_entity_id=entry.data['climate_entity_id'],
        heat_pump_power_entity_id=entry.data['heat_pump_power_entity_id'],
        external_temp_entity_id=entry.data['external_temp_entity_id'],
        user_hash=entry.data['user_hash'],
        postcode=entry.data['postcode'],
    )
    # https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle removal of an entry."""
    if unloaded := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


class OptisparkGetEntityError(Exception):
    """An error occured when trying to get the entity using get_entity."""


def get_entity(hass: HomeAssistant, entity_id: str):
    """Get the entity associated with entity_id.  It could be owned by another integration.

    Accessing entities of other integrations does not seem to be supported.  The method we use
    seems a bit dodgy.
    """
    try:
        LOGGER.info('\n')
        LOGGER.info(f'entity_id: {entity_id}')
        entity_reg: RegistryEntry = entity_registry.async_get(hass).async_get(entity_id)
        LOGGER.info(f'entity_reg: {entity_reg}')
        # Lets get the domain name via the device id
        device_id = entity_reg.device_id
        LOGGER.info(f'device_id: {device_id}')
        device_reg: DeviceRegistry = device_registry.async_get(hass).async_get(device_id)
        LOGGER.info(f'device_reg: {device_reg}')
        domain: str = list(device_reg.identifiers)[0][0]
        LOGGER.info(f'domain: {domain}')
        #domain: str = entity_reg.platform
        entity_coordinator: DataUpdateCoordinator = hass.data[domain][entity_reg.config_entry_id]
        LOGGER.info(f'entity_coordinator: {entity_coordinator}\n')

        # Get the entity via the entity coordinator
        for update_callback, _ in entity_coordinator._listeners.values():
            if update_callback.__self__.unique_id == entity_reg.unique_id:
                entity = update_callback.__self__
                if entity is None:
                    raise OptisparkGetEntityError(f'Entity({entity_id}) not yet initialised')
                return entity
    except Exception as err:
        LOGGER.error(traceback.format_exc())
        LOGGER.error(err)
        raise OptisparkGetEntityError(err)


def get_username(hass):
    """Attempt to get the username.

    Surely there is a better way than this.
    """
    try:
        return list(hass.data['person'][1].data.keys())[0]
    except Exception:
        return None


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


def optispark_integration_version(hass):
    """Get the version of the OptiSpark plugin.

    This will only work after entities have been initialised (not during config_flow)
    """
    device_id: str = template.device_id(hass, const.NAME)
    device_reg: DeviceRegistry = device_registry.async_get(hass).async_get(device_id)
    version = device_reg.model
    return version


class OptisparkGetHistoryError(Exception):
    """Error getting heat pump history and user data."""


def to_celcius(x):
    """Convert from Farenheit to Celcius."""
    return (x-32) * 5/9


async def get_history(hass, history_days: int, climate_entity_id, heat_pump_power_entity_id,
                      external_temp_entity_id, user_hash, include_user_info):
    """Get <history_days> worth of historical data from relevant devices.

    include_user_info should be set to False in config_flow because the entities have not yet been
    initialised.

    It ensures units are in kW and °C
    """
    try:
        start_time = pytz.UTC.localize(datetime.utcnow() - timedelta(days=history_days))
        end_time = pytz.UTC.localize(datetime.utcnow())

        histories = {}
        history_targets = {
            heat_pump_power_entity_id: {
                'save_attributes': False,
                'is_power': True},
            external_temp_entity_id: {
                'save_attributes': False,
                'is_power': False},
            climate_entity_id: {
                'save_attributes': True,
                'is_power': False}}
        key_lookup = {
            heat_pump_power_entity_id: const.DATABASE_COLUMN_SENSOR_HEAT_PUMP_POWER,
            external_temp_entity_id: const.DATABASE_COLUMN_SENSOR_EXTERNAL_TEMPERATURE,
            climate_entity_id: const.DATABASE_COLUMN_SENSOR_CLIMATE_ENTITY}

        heat_pump_unit = get_entity(hass, climate_entity_id).temperature_unit
        constant_attributes = {}  # Store attributes that would otherwise repeat in every time step
        for entity_id in history_targets:
            sensor = key_lookup[entity_id]
            args = [
                hass,
                start_time,
                end_time,
                entity_id]
            state_changes = await get_instance(hass).async_add_executor_job(
                state_changes_during_period,
                *args)
            histories[sensor] = {}
            for time_step in state_changes[entity_id]:
                # --------------- climate ---------------
                if entity_id == climate_entity_id:
                    if heat_pump_unit == '°F':
                        for key in ['current_temperature', 'target_temp_high', 'target_temp_low', 'temperature']:
                            if key in time_step.attributes:
                                try:
                                    time_step.attributes[key] = to_celcius(float(time_step.attributes[key]))
                                except Exception:
                                    LOGGER.warn(f'Could not convert time_step.attributes[{key}] ({time_step.attributes[key]}) of type({type(time_step.attributes[key])}) to float')
                                    continue
                    elif heat_pump_unit == '°C':
                        for key in ['current_temperature', 'target_temp_high', 'target_temp_low', 'temperature']:
                            if key in time_step.attributes:
                                try:
                                    time_step.attributes[key] = float(time_step.attributes[key])
                                except Exception:
                                    LOGGER.warn(f'Could not convert time_step.attributes[{key}] ({time_step.attributes[key]}) of type({type(time_step.attributes[key])}) to float')
                                    continue
                    else:
                        LOGGER.error(f'Heat pump uses unkown units ({heat_pump_unit})')
                        raise ValueError(f'Heat pump uses unkown units ({heat_pump_unit})')

                    histories[sensor][time_step.last_updated] = {
                        'state': time_step.state,
                        'attributes': time_step.attributes}

                # --------------- external_temp ---------------
                elif entity_id == external_temp_entity_id:
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
                    histories[sensor][time_step.last_updated] = {
                        'state': state,
                        'attributes': {}}

                # --------------- heat_pump_power ---------------
                elif entity_id == heat_pump_power_entity_id:
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
                    histories[sensor][time_step.last_updated] = {
                        'state': state,
                        'attributes': {}}


            LOGGER.debug(f'len(histories[{sensor}]): {len(histories[sensor])}')

            # Get attributes from first time_step
            constant_attributes[sensor] = {
                'entity_id': state_changes[entity_id][0].entity_id,
                'attributes': state_changes[entity_id][0].attributes}

        if include_user_info:
            user_info = get_user_info(hass, climate_entity_id)
        else:
            user_info = {}

        dynamo_data = {
            'histories': histories,
            'constant_attributes': constant_attributes,
            'user_info': user_info,
            'user_hash': user_hash}
    except Exception:
        LOGGER.error(traceback.format_exc())
        raise OptisparkGetHistoryError('Error getting history')
    return dynamo_data
