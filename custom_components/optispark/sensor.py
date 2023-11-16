"""Sensor platform for optispark."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription, SensorStateClass

from .const import DOMAIN
from .coordinator import OptisparkDataUpdateCoordinator
from .entity import OptisparkEntity
from random import getrandbits


def random_uuid_hex() -> str:
    """Generate a random UUID hex.

    This uuid should not be used for cryptographically secure
    operations.
    """
    return "%032x" % getrandbits(32 * 4)


ENTITY_DESCRIPTIONS = (
    SensorEntityDescription(
        key="optispark",
        name="Base Demand",
        icon="mdi:format-quote-close",
    ),
    SensorEntityDescription(
        key="optispark_second",
        name="Optimised Demand",
        icon="mdi:format-quote-close",
    ),
    SensorEntityDescription(
        key="optispark_third",
        name="Price",
        icon="mdi:format-quote-close",
    ),
    SensorEntityDescription(
        key="optispark_fourth",
        name="House Temp",
        icon="mdi:format-quote-close",
    ),
)


async def async_setup_entry(hass, entry, async_add_devices):
    """Set up the sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_devices(
        [
            OptisparkSensor(
                coordinator=coordinator,
                entity_description=ENTITY_DESCRIPTIONS[0],
                lambda_measurement='base_demand'
            ),
            OptisparkSensor(
                coordinator=coordinator,
                entity_description=ENTITY_DESCRIPTIONS[1],
                lambda_measurement='optimised_demand'
            ),
            OptisparkSensor(
                coordinator=coordinator,
                entity_description=ENTITY_DESCRIPTIONS[2],
                lambda_measurement='prices'
            ),
            OptisparkSensor(
                coordinator=coordinator,
                entity_description=ENTITY_DESCRIPTIONS[3],
                lambda_measurement='temps'
            )
        ],
        True
    )


class OptisparkSensor(OptisparkEntity, SensorEntity):
    """optispark Sensor class."""

    #_attr_has_entity_name = True

    #@property
    #def name(self):
    #    """Name of the entity."""
    #    return self.lambda_measurement

    def __init__(
        self,
        coordinator: OptisparkDataUpdateCoordinator,
        entity_description: SensorEntityDescription,
        lambda_measurement: str
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self.lambda_measurement = lambda_measurement

    @property
    def native_value(self) -> float:
        """Return the native value of the sensor."""
        out = self.coordinator.data[self.lambda_measurement]

        return out

    @property
    def state_class(self):
        """Returns the sensor stateclass measurement field."""
        #return 50
        return SensorStateClass.MEASUREMENT

    @property
    def unique_id(self):
        """Returns a unique ID for the sensor."""
        return f'sensor_id-{self.lambda_measurement}'