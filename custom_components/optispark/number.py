"""Sensor platform for optispark."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.components.number.const import NumberDeviceClass

from .coordinator import OptisparkDataUpdateCoordinator
from .entity import OptisparkEntity

from datetime import datetime
from .const import DOMAIN
from . import const

ENTITY_DESCRIPTIONS = (
    NumberEntityDescription(
        key="target_temperature",
        name="Target Temperature",
        icon="mdi:home-thermometer",
    ),
    NumberEntityDescription(
        key="temperature_range",
        name="Temperature Range",
        icon="mdi:gauge",
    ),
)


def get_closest_time(times_str: list[str]):
    """Get the closest matching time to now from the input data."""
    # Convert time to dattime format
    times = [datetime.strptime(d, '%Y-%m-%d %H:%M') for d in times_str]
    now = datetime.now()
    absolute_difference = [abs(getattr(t-now, 'total_seconds')()) for t in times]
    min_idx = absolute_difference.index(min(absolute_difference))
    #print(f'The closest time: {times[min_idx]}')
    return times_str[min_idx]


async def async_setup_entry(hass, entry, async_add_devices):
    """Set up the Number platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_devices(
        [
            OptisparkNumber(
                coordinator=coordinator,
                entity_description=NumberEntityDescription(
                    key="target_temperature",
                    name="Target Temperature",
                    icon="mdi:home-thermometer"),
                native_value=21,
                native_step=0.5,
                native_max_value=26,
                native_min_value=14,
                lambda_parameter=const.LAMBDA_SET_POINT,
                device_class=NumberDeviceClass.TEMPERATURE,
                native_unit_of_measurement='°C'
            ),
            OptisparkNumber(
                coordinator=coordinator,
                entity_description=NumberEntityDescription(
                    key="temperature_range",
                    name="Temperature Range",
                    icon="mdi:gauge"),
                native_value=3,
                native_step=0.5,
                native_max_value=4,
                native_min_value=0,
                lambda_parameter=const.LAMBDA_TEMP_RANGE,
                device_class=None,
                native_unit_of_measurement='°C'
            )
        ]
    )


class OptisparkNumber(OptisparkEntity, NumberEntity):
    """optispark Number class."""

    def __init__(
        self,
        coordinator: OptisparkDataUpdateCoordinator,
        entity_description: NumberEntityDescription,
        native_value,
        native_step,
        native_max_value,
        native_min_value,
        lambda_parameter,
        device_class,
        native_unit_of_measurement
    ) -> None:
        """Initialize the Number class."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._native_value = native_value
        self._native_step = native_step
        self._native_max_value = native_max_value
        self._native_min_value = native_min_value
        self._lambda_parameter = lambda_parameter
        self._device_class = device_class
        self._native_unit_of_measurement = native_unit_of_measurement

    @property
    def device_class(self):
        """Type of sensor."""
        return self._device_class

    @property
    def native_unit_of_measurement(self):
        """Home assistant can magically replaces this with °F.

        Home assistant documentation:
            If the native_unit_of_measurement is '°C' or '°F', and its device_class is temperature,
            the sensor's unit_of_measurement will be the preferred temperature unit configured by
            the user and the sensor's state will be the native_value after an optional unit
            conversion
        """
        return self._native_unit_of_measurement

    @property
    def native_value(self) -> str:
        """The value of the sensor in the sensor's native_unit_of_measurement.

        Using a device_class may restrict the types that can be returned by this property.
        """
        return self._native_value

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        self._native_value = value
        lambda_args = self.coordinator.lambda_args
        lambda_args[self._lambda_parameter] = self._native_value
        await self.coordinator.async_set_lambda_args(lambda_args)

    @property
    def native_step(self):
        """Defines the resolution of the values.

        i.e. the smallest increment or decrement in the number's.
        """
        return self._native_step

    @property
    def native_max_value(self):
        """Max possible value."""
        return self._native_max_value

    @property
    def native_min_value(self):
        """Min possible value."""
        return self._native_min_value
