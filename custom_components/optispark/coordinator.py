"""DataUpdateCoordinator for optispark."""
from __future__ import annotations

from datetime import timedelta, datetime
import time

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
from .const import LOGGER
from homeassistant.helpers.entity_registry import EntityRegistry, RegistryEntry
from homeassistant.helpers import entity_registry
from homeassistant.helpers import template


def get_closest_time(lambda_results):
    """Get the closest matching time to now from the data set provided."""
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
        my_data[key] = {i['x']: i['y'] for i in lambda_results[key]}
        for key in non_time_based_keys:
            my_data[key] = lambda_results[key]

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


class OptisparkDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: OptisparkApiClient,
        climate_entity: entity_registry.RegistryEntity,
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
        self.climate_entity = climate_entity
        self.results = {}
        self.last_update_time = 0
        self.update_lambda_interval = 60*60
        self.switched_enabled = True
        self._lambda_update = True
        self._lambda_args = {
            const.LAMBDA_HOUSE_CONFIG: None,
            const.LAMBDA_SET_POINT: 20.0,
            const.LAMBDA_TEMP_RANGE: 3.0,
            const.LAMBDA_POSTCODE: self.postcode}

    async def update_heat_pump_temperature(self):
        """Set the temperature of the heat pump using the value from lambda.

        Accessing entities of other integrations does not seem to be supported.  The method we use
        seems a bit dodgy.
        """
        temp: float = self.data[const.LAMBDA_TEMP]
        domain: str = self.climate_entity.platform
        entity_coordinator: DataUpdateCoordinator = self.hass.data[domain][self.climate_entity.config_entry_id]

        # Get the entity via the entity coordinator
        for update_callback, _ in entity_coordinator._listeners.values():
            if update_callback.__self__.unique_id == self.climate_entity.unique_id:
                entity = update_callback.__self__
                break

        if entity.hvac_mode == HVACMode.HEAT_COOL:
            await entity.async_set_temperature(
                target_temp_low=temp,
                target_temp_high=entity.target_temperature_high)
        else:
            await entity.async_set_temperature(temperature=temp)

    def enable_integration(self, enable: bool):
        """Enable/Disable all entities other than the switch."""
        entity_register: EntityRegistry = entity_registry.async_get(self.hass)
        device_id: str = template.device_id(self.hass, const.NAME)
        entities: list[RegistryEntry] = entity_registry.async_entries_for_device(
            entity_register,
            device_id,
            include_disabled_entities=True)

        # Remove the switch from the list so it doesn't get disabled
        for idx, entity in enumerate(entities):
            if entity.entity_id == 'switch.enable_optispark':
                idx_store = idx
        del entities[idx_store]

        enable_lookup = {True: None, False: entity_registry.RegistryEntryDisabler.INTEGRATION}
        for entity in entities:
            entity_register.async_update_entity(entity.entity_id, disabled_by=enable_lookup[enable])
        #self._available = enable
        #self.always_update = enable

    async def async_set_lambda_args(self, lambda_args):
        """Update the lambda arguments.

        To be called from entities.
        """
        self._lambda_args = lambda_args
        self._lambda_update = True
        await self.async_request_update()

    @property
    def postcode(self):
        """Postcode."""
        return self._postcode

    @property
    def lambda_args(self):
        """Returns the lamba arguments."""
        return self._lambda_args

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
        if self.switched_enabled is False:
            # Integration is disabled, don't call lambda
            return self.data
        try:
            if time.time() - self.last_update_time > self.update_lambda_interval or self._lambda_update:
                self._lambda_update = False
                self.lambda_results = await self.client.async_get_data(self.lambda_args)

                out = get_closest_time(self.lambda_results)

                self.last_update_time = time.time()
                #await self.update_heat_pump_temperature()
                return out
            else:
                out = get_closest_time(self.lambda_results)
                LOGGER.debug('_asnyn_update_data()')
                await self.update_heat_pump_temperature()
                return out
        except OptisparkApiClientAuthenticationError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except OptisparkApiClientError as exception:
            raise UpdateFailed(exception) from exception
