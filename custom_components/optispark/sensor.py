"""Sensor platform for optispark."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.components.sensor.const import SensorDeviceClass

from . import const
from .coordinator import OptisparkDataUpdateCoordinator
from .entity import OptisparkEntity
#from .const import LOGGER


async def async_setup_entry(hass, entry, async_add_devices):
    """Set up the sensor platform."""
    coordinator = hass.data[const.DOMAIN][entry.entry_id]
    async_add_devices([
        OptisparkSensor(
            coordinator=coordinator,
            entity_description=SensorEntityDescription(
                key="base_demand",
                name="Base Demand",
                icon="mdi:heat-pump-outline"),
            lambda_measurement=const.LAMBDA_BASE_DEMAND,
            device_class=SensorDeviceClass.POWER,
            native_unit_of_measurement='kW',
            suggested_display_precision=2
        ),
        OptisparkSensor(
            coordinator=coordinator,
            entity_description=SensorEntityDescription(
                key="optimised_demand",
                name="Optimised Demand",
                icon="mdi:heat-pump"),
            lambda_measurement=const.LAMBDA_OPTIMISED_DEMAND,
            device_class=SensorDeviceClass.POWER,
            native_unit_of_measurement='kW',
            suggested_display_precision=2
        ),
        OptisparkSensor(
            coordinator=coordinator,
            entity_description=SensorEntityDescription(
                key="price",
                name="Electricity Price",
                icon="mdi:currency-gbp"),
            lambda_measurement=const.LAMBDA_PRICE,
            device_class=SensorDeviceClass.MONETARY,
            native_unit_of_measurement='p/kWh',
            suggested_display_precision=1
        ),
        OptisparkSensor(
            coordinator=coordinator,
            entity_description=SensorEntityDescription(
                key="target_house_temp",
                name="Target House Temp",
                icon="mdi:home-thermometer"),
            lambda_measurement=const.LAMBDA_TEMP,
            device_class=SensorDeviceClass.TEMPERATURE,
            native_unit_of_measurement='°C',
            suggested_display_precision=1
        ),
        OptisparkSensor(
            coordinator=coordinator,
            entity_description=SensorEntityDescription(
                key="projected_savings",
                name="Projected Savings",
                icon="mdi:currency-gbp"),
            lambda_measurement=const.LAMBDA_PROJECTED_PERCENT_SAVINGS,
            native_unit_of_measurement='%',
            suggested_display_precision=1,
            device_class=None,
            state_class=None
        ),
        OptisparkSensorParameter(
            coordinator=coordinator,
            entity_description=SensorEntityDescription(
                key="postcode",
                name="Postcode",
                icon="mdi:map-marker"),
            lambda_measurement=None,
            coordinator_parameter='postcode',
            device_class=None,
            state_class=None,
        ),
        OptisparkSensorParameter(
            coordinator=coordinator,
            entity_description=SensorEntityDescription(
                key="heat_pump_power_usage",
                name="Heat pump power usage",
                icon="mdi:lightning-bolt"),
            lambda_measurement=None,
            native_unit_of_measurement='kW',
            suggested_display_precision=2,
            coordinator_parameter='heat_pump_power_usage',
            device_class=SensorDeviceClass.POWER,
        ),
        OptisparkSensorParameter(
            coordinator=coordinator,
            entity_description=SensorEntityDescription(
                key="external_temperature",
                name="External Temperature",
                icon="mdi:thermometer"),
            lambda_measurement=None,
            native_unit_of_measurement='°C',
            coordinator_parameter='external_temp',
            suggested_display_precision=1,
            device_class=SensorDeviceClass.TEMPERATURE,
        ),
    ])


class OptisparkSensor(OptisparkEntity, SensorEntity):
    """optispark Sensor class."""

    def __init__(
        self,
        coordinator: OptisparkDataUpdateCoordinator,
        entity_description: SensorEntityDescription,
        lambda_measurement: str,
        coordinator_parameter: str = None,
        device_class: str = None,
        native_unit_of_measurement: str = None,
        suggested_display_precision: int = None,
        state_class: SensorStateClass = SensorStateClass.MEASUREMENT
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._lambda_measurement = lambda_measurement
        self._coordinator_parameter = coordinator_parameter
        self._device_class = device_class
        self._native_unit_of_measurement = native_unit_of_measurement
        self._suggested_display_precision = suggested_display_precision
        self._state_class = state_class

    @property
    def suggested_display_precision(self):
        """The number of decimals which should be used in the sensor's state when it's displayed."""
        return self._suggested_display_precision

    @property
    def device_class(self):
        """Type of sensor."""
        return self._device_class

    @property
    def native_unit_of_measurement(self):
        """The unit of measurement that the sensor's value is expressed in.

        If the native_unit_of_measurement is °C or °F, and its device_class is temperature, the
        sensor's unit_of_measurement will be the preferred temperature unit configured by the user
        and the sensor's state will be the native_value after an optional unit conversion.
        """
        return self._native_unit_of_measurement

    @property
    def native_value(self) -> float:
        """The value of the sensor in the sensor's native_unit_of_measurement.

        Using a device_class may restrict the types that can be returned by this property.
        """
        if self.coordinator.available:
            return self.coordinator.data[self._lambda_measurement]
        else:
            return None

    @property
    def state_class(self):
        """Type of state.

        If not None, the sensor is assumed to be numerical and will be displayed as a line-chart in
        the frontend instead of as discrete values.
        """
        return self._state_class


class OptisparkSensorParameter(OptisparkSensor):
    """Uses a parameter of the coordinator as the native value instead of the data attribute."""

    @property
    def native_value(self) -> str:
        """The value of the sensor in the sensor's native_unit_of_measurement.

        Using a device_class may restrict the types that can be returned by this property.
        """
        if self.coordinator.available:
            return getattr(self.coordinator, self._coordinator_parameter)
        else:
            return None
