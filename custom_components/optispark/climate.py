"""Optispark climate entity."""
from __future__ import annotations

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityDescription,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import UnitOfTemperature

from . import const
from .coordinator import OptisparkDataUpdateCoordinator
from .domain.thermostat.thermostat_info import ThermostatInfo
from .entity import OptisparkEntity

ENTITY_DESCRIPTIONS = (
    ClimateEntityDescription(
        key="Optispark_climate",
        name="Optispark",
        icon="mdi:heat-pump-outline",
    ),
)


async def async_setup_entry(hass, entry, async_add_devices):
    """Set up the climate platform."""
    coordinator: OptisparkDataUpdateCoordinator = hass.data[const.DOMAIN][entry.entry_id]
    thermostat_info: ThermostatInfo = await coordinator.fetch_thermostat_info()
    target_temp = 20
    if thermostat_info is not None:
        if thermostat_info.hvac_mode == HVACMode.COOL and thermostat_info.target_temp_low:
            target_temp = thermostat_info.target_temp_low
        elif thermostat_info.hvac_mode == HVACMode.HEAT and thermostat_info.target_temp_high:
            target_temp = thermostat_info.target_temp_high
        elif thermostat_info.hvac_mode == HVACMode.HEAT_COOL:
            target_temp = thermostat_info.target_temp_high

    async_add_devices(
        OptisparkClimate(
            coordinator=coordinator,
            entity_description=entity_description,
            target_temp=target_temp
        )
        for entity_description in ENTITY_DESCRIPTIONS
    )


class OptisparkClimate(OptisparkEntity, ClimateEntity):
    """Optispark climate class."""

    def __init__(
            self,
            coordinator: OptisparkDataUpdateCoordinator,
            entity_description: ClimateEntityDescription,
            target_temp: float,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._target_temperature = target_temp if target_temp else 20
        self._target_temperature_high = 25
        self._target_temperature_low = 20
        self._hvac_mode = HVACMode.HEAT

    async def async_set_hvac_mode(self, hvac_mode):
        """Such as heat, cool, both..."""
        self._hvac_mode = hvac_mode
        await self.coordinator.async_request_update()
        return

    async def async_set_temperature(self, **kwargs):
        """Utilised when the heat pump is in either heat or cooling only mode."""
        self._target_temperature = kwargs['temperature']
        lambda_args = self.coordinator.lambda_args
        lambda_args[const.LAMBDA_SET_POINT] = self._target_temperature
        lambda_args[const.LAMBDA_TEMP_CHANGED] = True
        await self.coordinator.async_set_lambda_args(lambda_args)

    @property
    def supported_features(self) -> ClimateEntityFeature:
        """Return the list of supported features."""
        out = ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
        out |= ClimateEntityFeature.AUX_HEAT
        if self._hvac_mode == HVACMode.HEAT_COOL:
            # Do we need to include AUTO mode?
            out = ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
            out |= ClimateEntityFeature.AUX_HEAT
        else:
            out = ClimateEntityFeature.TARGET_TEMPERATURE
            out |= ClimateEntityFeature.AUX_HEAT
        return out

    @property
    def hvac_modes(self) -> HVACMode:
        """Returns available modes."""
        match 'heat':
            case 'heat':
                return [
                    # HVACMode.OFF,
                    HVACMode.HEAT,
                    # HVACMode.COOL,
                    # HVACMode.HEAT_COOL,
                    # HVACMode.AUTO,
                    # HVACMode.DRY,
                    # HVACMode.FAN_ONLY
                ]
            case 'cool':
                return [
                    HVACMode.OFF,
                    # HVACMode.HEAT,
                    HVACMode.COOL,
                    # HVACMode.HEAT_COOL,
                    # HVACMode.AUTO,
                    # HVACMode.DRY,
                    HVACMode.FAN_ONLY]
            case 'heat_cool':
                return [
                    HVACMode.OFF,
                    HVACMode.HEAT,
                    HVACMode.COOL,
                    HVACMode.HEAT_COOL,
                    HVACMode.AUTO,
                    HVACMode.DRY,
                    HVACMode.FAN_ONLY]
            case _:
                raise ValueError(f'Heat_cool mode not caught: {self.coordinator.config_entry.data[const.MODE]}')

    @property
    def hvac_mode(self) -> HVACMode:
        """Return current operation.

        ie. OFF, HEAT, COOL, HEAT_COOL, AUTO, DRY, FAN_ONLY.
        HEAT_COOL: The device is set to heat/cool to a target temperature range.
        AUTO: The device is set to a schedule, learned behavior, AI.
        """

        return self._hvac_mode

    @property
    def temperature_unit(self) -> str:
        """Temperature unit that the backend works in.

        Our backend will always work in celsius so this should always be set to celsius.
        The front end of homeassistant deals with unit conversion, it just needs to know which
        units we are working with.
        """
        return UnitOfTemperature.CELSIUS

    @property
    def target_temperature(self) -> float:
        """Target temperature when operating in single cooling or heating mode."""
        return self._target_temperature

    @property
    def target_temperature_high(self) -> float:
        """Maximum desirable temperature when operating in dual cooling and heating mode."""
        return self._target_temperature_high

    @property
    def target_temperature_low(self) -> float:
        """Minimum desirable temperature when operating in dual cooling and heating mode."""
        return self._target_temperature_low

    @property
    def current_temperature(self) -> float:
        """House temperature measured by the heat pump."""
        return self.coordinator.internal_temp

    @property
    def is_aux_heat(self) -> int:
        """I think this returns whether the heat pump is currently using resistive heating."""
        return None

    @property
    def max_temp(self) -> float:
        """Maximum temperature the heat pump can be set to."""
        return 28

    @property
    def min_temp(self) -> float:
        """Minimum temperature the heat pump can be set to."""
        return 8

    # @property
    # def unique_id(self):
    #    """Return a unique ID."""
    #    return 'debug_heat_pump_id'
