"""Sensor platform for integration_blueprint."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription, SensorStateClass

from .const import DOMAIN, NAME, ATTRIBUTION, VERSION
from .coordinator import BlueprintDataUpdateCoordinator
from .entity import IntegrationBlueprintEntity
from random import getrandbits


def random_uuid_hex() -> str:
    """Generate a random UUID hex.

    This uuid should not be used for cryptographically secure
    operations.
    """
    return "%032x" % getrandbits(32 * 4)


ENTITY_DESCRIPTIONS = (
    SensorEntityDescription(
        key="integration_blueprint",
        name="Base Demand",
        icon="mdi:format-quote-close",
    ),
    SensorEntityDescription(
        key="integration_blueprint_second",
        name="Optimised Demand",
        icon="mdi:format-quote-close",
    ),
    SensorEntityDescription(
        key="integration_blueprint_third",
        name="Price",
        icon="mdi:format-quote-close",
    ),
    SensorEntityDescription(
        key="integration_blueprint_fourth",
        name="House Temp",
        icon="mdi:format-quote-close",
    ),
)


async def async_setup_entry(hass, entry, async_add_devices):
    """Set up the sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_devices(
        [
            IntegrationBlueprintSensor(
                coordinator=coordinator,
                entity_description=ENTITY_DESCRIPTIONS[0],
                lambda_measurement='base_demand'
            ),
            IntegrationBlueprintSensor(
                coordinator=coordinator,
                entity_description=ENTITY_DESCRIPTIONS[1],
                lambda_measurement='optimised_demand'
            ),
            IntegrationBlueprintSensor(
                coordinator=coordinator,
                entity_description=ENTITY_DESCRIPTIONS[2],
                lambda_measurement='prices'
            ),
            IntegrationBlueprintSensor(
                coordinator=coordinator,
                entity_description=ENTITY_DESCRIPTIONS[3],
                lambda_measurement='temps'
            )
        ],
        True
    )


class IntegrationBlueprintSensor(IntegrationBlueprintEntity, SensorEntity):
    """integration_blueprint Sensor class."""
    #_attr_has_entity_name = True

    #@property
    #def name(self):
    #    """Name of the entity."""
    #    return self.lambda_measurement

    def __init__(
        self,
        coordinator: BlueprintDataUpdateCoordinator,
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
        #return 50
        return SensorStateClass.MEASUREMENT

    @property
    def unique_id(self):
        return f'sensor_id-{self.lambda_measurement}'
