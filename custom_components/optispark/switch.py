"""Switch platform for optispark."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription

from .const import DOMAIN, LOGGER
from .coordinator import OptisparkDataUpdateCoordinator
from .entity import OptisparkEntity

ENTITY_DESCRIPTIONS = (
    SwitchEntityDescription(
        key="enable_optispark",
        name="Enable Optispark",
        icon="mdi:lightning-bolt-circle",
    ),
)


async def async_setup_entry(hass, entry, async_add_devices):
    """Set up the sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_devices(
        OptisparkSwitch(
            coordinator=coordinator,
            entity_description=entity_description,
        )
        for entity_description in ENTITY_DESCRIPTIONS
    )


class OptisparkSwitch(OptisparkEntity, SwitchEntity):
    """optispark switch class."""

    def __init__(
        self,
        coordinator: OptisparkDataUpdateCoordinator,
        entity_description: SwitchEntityDescription,
    ) -> None:
        """Initialize the switch class."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._is_on = True

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        return self._is_on

    async def async_turn_on(self, **_: any) -> None:
        """Turn on the switch."""
        self._is_on = True
        #self.coordinator.enable_switch = True
        #self.coordinator._available = True
        self.coordinator.enable_integration(True)
        #self.enabled = True
        LOGGER.debug('switch on')
        await self.coordinator.request_update()

    async def async_turn_off(self, **_: any) -> None:
        """Turn off the switch."""
        self._is_on = False
        #self.coordinator.enable_switch = False
        #self.coordinator._available = False
        self.coordinator.enable_integration(False)
        LOGGER.debug('switch off')
        #self.enabled = False
        await self.coordinator.request_update()
    #
    #@property
    #def unique_id(self):
    #    """Returns a unique ID for the sensor."""
    #    return 'sensor_id_switch'
