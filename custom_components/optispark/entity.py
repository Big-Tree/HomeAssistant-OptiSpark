"""OptisparkEntity class.
Ensures that all entities that inherit this are grouped together into the same device
"""
from __future__ import annotations

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN, NAME, VERSION
from .coordinator import OptisparkDataUpdateCoordinator


class OptisparkEntity(CoordinatorEntity):
    """BlueprintEntity class."""

    _attr_attribution = ATTRIBUTION

    def __init__(self, coordinator: OptisparkDataUpdateCoordinator) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_unique_id = coordinator.config_entry.entry_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, 'OptiSpark_device')},
            name=NAME,
            model=VERSION,
            manufacturer=NAME,
        )
