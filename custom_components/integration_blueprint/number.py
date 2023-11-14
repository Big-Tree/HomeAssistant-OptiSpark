"""Sensor platform for integration_blueprint."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription

from .coordinator import BlueprintDataUpdateCoordinator
from .entity import IntegrationBlueprintEntity

from datetime import datetime

ENTITY_DESCRIPTIONS = (
    SensorEntityDescription(
        key="integration_blueprint",
        name="Optimised Demand",
        icon="mdi:format-quote-close",
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
    """Set up the sensor platform."""
    pass
    #coordinator = hass.data[DOMAIN][entry.entry_id]
    #async_add_devices(
    #    IntegrationBlueprintSensor(
    #        coordinator=coordinator,
    #        entity_description=entity_description,
    #    )
    #    for entity_description in ENTITY_DESCRIPTIONS
    #)


class IntegrationBlueprintSensor(IntegrationBlueprintEntity, SensorEntity):
    """integration_blueprint Sensor class."""

    def __init__(
        self,
        coordinator: BlueprintDataUpdateCoordinator,
        entity_description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator)
        self.entity_description = entity_description

    @property
    def native_value(self) -> str:
        """Return the native value of the sensor."""
        #out = self.coordinator.data
        ## Convert to dictionary where time is the key
        #data = {}
        #for key in ['base_demand', 'prices', 'temps', 'optimised_demand']:
        #    data[key] = {i['x']: i['y'] for i in out[key]}
        #
        #time_str: list[str] = [i['x'] for i in out['base_demand']]
        #closest_time = get_closest_time(time_str)
        #base_demand_now = data['base_demand'][closest_time]
        #return base_demand_now

        #import time
        #out = time.clock_gettime(0)
        return 5

    @property
    def unique_id(self):
        """Return unique id for the sensor."""
        return 'sensor_id_number'

    #@property
    #def device_info(self):
    #    """Return device information."""
    #    return {
    #        "identifiers": {(DOMAIN, "optispark_device_id_number")},
    #    }
