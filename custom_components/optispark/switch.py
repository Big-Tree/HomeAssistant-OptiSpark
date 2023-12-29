"""Switch platform for optispark."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.helpers import entity_registry

from .const import DOMAIN, LOGGER, SWITCH_KEY
from .coordinator import OptisparkDataUpdateCoordinator
from .entity import OptisparkEntity

ENTITY_DESCRIPTIONS = (
    SwitchEntityDescription(
        key=SWITCH_KEY,
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

        # If the switch has previously disabled the integration, turn switch off
        self._is_on = True
        entities = self.coordinator.get_optispark_entities()
        for entity in entities:
            if entity.disabled_by == entity_registry.RegistryEntryDisabler.INTEGRATION:
                self.enable_disable_integration(False)
                break
        if self._is_on:
            self.enable_disable_integration(True)

    def enable_disable_integration(self, enable: bool):
        """Enable/Disable the entire integration."""
        self._is_on = enable
        self.coordinator.enable_disable_integration(enable)

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        return self._is_on

    async def async_turn_on(self, **_: any) -> None:
        """Turn on the switch."""
        self.enable_disable_integration(True)
        LOGGER.debug('switch on')
        await self.coordinator.async_request_update()

    async def async_turn_off(self, **_: any) -> None:
        """Turn off the switch."""
        self.enable_disable_integration(False)
        LOGGER.debug('switch off')
        await self.coordinator.async_request_update()
