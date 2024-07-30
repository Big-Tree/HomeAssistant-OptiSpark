"""DataUpdateCoordinator for optispark."""

from __future__ import annotations

from datetime import timedelta, datetime, timezone
import traceback

from homeassistant.core import HomeAssistant
import homeassistant.const
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.components.climate import ClimateEntityFeature
from homeassistant.exceptions import ConfigEntryAuthFailed


from . import const, OptisparkApiClient
from . import get_entity
# from . import history
from .backend_update_handler import BackendUpdateHandler
# from .climate import OptisparkClimate
from .const import LOGGER
from homeassistant.helpers.entity_registry import EntityRegistry, RegistryEntry
from homeassistant.helpers import entity_registry
from homeassistant.helpers import template
# import numpy as np

from .domain.exception.exception import OptisparkSetTemperatureError
# from .domain.value_object.address import Address

from homeassistant.const import UnitOfTemperature

from .domain.thermostat.thermostat_info import ThermostatInfo
from .domain.control.control_info import ControlInfo
from .backend.exception.exceptions import OptisparkApiClientAuthenticationError, OptisparkApiClientError


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
        tariff: str,
        address: str,
        city: str,
        country: str,
    ) -> None:
        """Initialize."""
        self.client = client
        super().__init__(
            hass=hass,
            logger=const.LOGGER,
            name=const.DOMAIN,
            update_interval=timedelta(seconds=const.UPDATE_INTERVAL),
        )
        self._postcode = postcode if postcode is not None else "AB11 6LU"
        self._tariff = tariff
        self._address = address
        self._city = city
        self._country = country
        # user_hash = 'debug_hash'
        self._user_hash = user_hash
        self._climate_entity_id = climate_entity_id
        self._heat_pump_power_entity_id = heat_pump_power_entity_id
        self._external_temp_entity_id = external_temp_entity_id
        self._switch_enabled = False  # The switch will set this at startup
        self._available = False
        self._lambda_args = {
            const.LAMBDA_SET_POINT: 20.0,
            const.LAMBDA_TEMP_RANGE: 2.0,
            const.LAMBDA_POSTCODE: self.postcode,
            const.LAMBDA_USER_HASH: user_hash,
            const.LAMBDA_INITIAL_INTERNAL_TEMP: None,
            const.LAMBDA_OUTSIDE_RANGE: False,
            const.LAMBDA_HEAT_PUMP_MODE_RAW: "HEATING",
            const.LAMBDA_OPTIMISED_DEMAND: None,
            const.LAMBDA_HOME_ASSISTANT_VERSION: const.VERSION,
            const.LAMBDA_ADDRESS: self._address,
            const.LAMBDA_CITY: self._city,
        }
        self._previous_lambda_args = self._lambda_args
        self._lambda_update_handler = BackendUpdateHandler(
            hass=self.hass,
            client=self.client,
            climate_entity_id=self._climate_entity_id,
            heat_pump_power_entity_id=self._heat_pump_power_entity_id,
            external_temp_entity_id=self._external_temp_entity_id,
            user_hash=self._user_hash,
            postcode=self._postcode,
            address=self._address,
            country=self._country,
            city=self._city,
            tariff=self._tariff,
        )

    async def fetch_thermostat_info(self) -> ThermostatInfo:
        """Fetchs thermostat info from OptiSpark backend"""

        return await self.client.get_thermostat_info()

    def convert_sensor_from_farenheit(self, entity, temp):
        """Ensure that the sensor returns values in Celcius.

        Only works with sensor entities
        If the sensor uses Farenheit then we'll need to convert Farenheit to Celcius
        """
        sensor_unit = entity.native_unit_of_measurement
        if sensor_unit == UnitOfTemperature.CELSIUS:
            return temp
        elif sensor_unit == UnitOfTemperature.FAHRENHEIT:
            # Convert temperature from Celcius to Farenheit
            return (temp - 32) * 5 / 9
        else:
            raise ValueError(f"Heat pump uses unkown units ({sensor_unit})")

    def convert_climate_from_farenheit(self, entity, temp):
        """Ensure that the heat pump returns values in Celcius.

        Only works with climate entity
        If the heat_pump uses Farenheit then we'll need to convert Farenheit to Celcius
        """
        heat_pump_unit = entity.temperature_unit
        if heat_pump_unit == UnitOfTemperature.CELSIUS:
            return temp
        elif heat_pump_unit == UnitOfTemperature.FAHRENHEIT:
            # Convert temperature from Celcius to Farenheit
            return (temp - 32) * 5 / 9
        else:
            raise ValueError(f"Heat pump uses unkown units ({heat_pump_unit})")

    def convert_climate_from_celcius(self, entity, temp):
        """Ensure that the heat pump is given a temperature in the correct units.

        Only works with climate entities.
        If the heat_pump uses Farenheit then we'll need to convert Celcius to Farenheit
        """
        heat_pump_unit = entity.temperature_unit
        if heat_pump_unit == UnitOfTemperature.CELSIUS:
            return temp
        elif heat_pump_unit == UnitOfTemperature.FAHRENHEIT:
            # Convert temperature from Celcius to Farenheit
            return temp * 9 / 5 + 32
        else:
            raise ValueError(f"Heat pump uses unkown units ({heat_pump_unit})")

    async def update_heat_pump_temperature(self, data):
        """Set the temperature of the heat pump using the value from lambda."""
        temp: float = data[const.LAMBDA_TEMP_CONTROLS]
        climate_entity = get_entity(self.hass, self._climate_entity_id)

        try:
            if self.heat_pump_target_temperature == temp:
                return
            LOGGER.debug("Change in target temperature!")
            supports_target_temperature_range = (
                climate_entity.supported_features
                & ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
                == ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
            )
            if supports_target_temperature_range:
                await climate_entity.async_set_temperature(
                    target_temp_low=self.convert_climate_from_celcius(
                        climate_entity, temp
                    ),
                    target_temp_high=climate_entity.target_temperature_high,
                )
            else:
                await climate_entity.async_set_temperature(
                    temperature=self.convert_climate_from_celcius(climate_entity, temp)
                )
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
            entity_register, device_id, include_disabled_entities=True
        )
        if include_switch is False:
            # Remove the switch from the list so it doesn't get disabled
            idx_store = None
            for idx, entity in enumerate(entities):
                if entity.entity_id == "switch." + const.SWITCH_KEY:
                    idx_store = idx
            if idx_store is not None:
                del entities[idx_store]
        return entities

    def enable_disable_entities(self, entities: list[RegistryEntry], enable: bool):
        """Enable/Disable all entities given in the list."""
        entity_register: EntityRegistry = entity_registry.async_get(self.hass)
        enable_lookup = {
            True: None,
            False: entity_registry.RegistryEntryDisabler.INTEGRATION,
        }
        for entity in entities:
            entity_register.async_update_entity(
                entity.entity_id, disabled_by=enable_lookup[enable]
            )

    def enable_disable_integration(self, enable: bool):
        """Enable/Disable all entities other than the switch."""
        entities = self.get_optispark_entities(include_switch=False)
        self.enable_disable_entities(entities, enable)
        self._switch_enabled = enable
        if enable is False:
            # The coordinator is available once data is fetched
            self._available = False
        # self.always_update = enable

    async def async_set_lambda_args(self, lambda_args):
        """Update the lambda arguments.

        To be called from entities.
        """
        self._lambda_args = lambda_args
        self._lambda_update_handler.manual_update = True

        temp = lambda_args[const.LAMBDA_SET_POINT]
        if lambda_args[const.LAMBDA_TEMP_CHANGED] is True:
            info = ControlInfo(
                set_point=temp,
                mode=lambda_args[const.LAMBDA_HEAT_PUMP_MODE_RAW]
            )
            thermostat_control_response = await self.client.set_manual(info)
            if not thermostat_control_response:
                LOGGER.error(f'Unable to update thermostat control on OptisPark backend')
        self._previous_lambda_args = lambda_args
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
        supports_target_temperature_range = (
            climate_entity.supported_features
            & ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
            == ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
        )
        if supports_target_temperature_range:
            temperature = climate_entity.target_temperature_low
        else:
            temperature = climate_entity.target_temperature

        return temperature

    @property
    def internal_temp(self):
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
            case "W":
                return native_value / 1000
            case "kW":
                return native_value
            case _:
                LOGGER.error(
                    f"Heat pump does not use supported unit({entity.unit_of_measurement})"
                )
                raise TypeError(
                    f"Heat pump does not use supported unit({entity.unit_of_measurement})"
                )

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
        """Returns the lambda arguments.

        Updates the initial_internal_temp and checks outside_range.
        """
        self._lambda_args[const.LAMBDA_INITIAL_INTERNAL_TEMP] = self.internal_temp
        self._lambda_args[const.LAMBDA_OPTIMISED_DEMAND] = self.heat_pump_power_usage
        if (
            abs(self.internal_temp - self._lambda_args[const.LAMBDA_SET_POINT])
            > self._lambda_args[const.LAMBDA_TEMP_RANGE]
        ):
            self._lambda_args[const.LAMBDA_OUTSIDE_RANGE] = True
        else:
            self._lambda_args[const.LAMBDA_OUTSIDE_RANGE] = False

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
            # self.lambda_args[const.LAMBDA_OPTIMISED_DEMAND] =
            data = await self._lambda_update_handler(self.lambda_args)
            await self.update_heat_pump_temperature(data)
            self._available = True
            return data
        except OptisparkApiClientAuthenticationError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except OptisparkApiClientError as exception:
            raise UpdateFailed(exception) from exception

