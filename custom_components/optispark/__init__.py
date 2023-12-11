"""Custom integration to integrate optispark with Home Assistant.

For more details about this integration, please refer to
https://github.com/Big-Tree/HomeAssistant-OptiSpark
"""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import entity_registry
from homeassistant.helpers.entity_registry import RegistryEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from .api import OptisparkApiClient
from .const import DOMAIN

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.NUMBER,
]


# https://developers.home-assistant.io/docs/config_entries_index/#setting-up-an-entry
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up this integration using UI."""
    from .coordinator import OptisparkDataUpdateCoordinator  # Prevent circular import
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator = OptisparkDataUpdateCoordinator(
        hass=hass,
        client=OptisparkApiClient(
            session=async_get_clientsession(hass)),
        climate_entity_id=entry.data['climate_entity'],
        postcode=entry.data['postcode'],
    )
    # https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle removal of an entry."""
    if unloaded := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


def get_entity(hass: HomeAssistant, entity_id: str):
    """Get the entity associated with entity_id.  It could be owned by another integration.

    Accessing entities of other integrations does not seem to be supported.  The method we use
    seems a bit dodgy.
    """
    entity_reg: RegistryEntry = entity_registry.async_get(hass).async_get(entity_id)
    domain: str = entity_reg.platform
    entity_coordinator: DataUpdateCoordinator = hass.data[domain][entity_reg.config_entry_id]

    # Get the entity via the entity coordinator
    for update_callback, _ in entity_coordinator._listeners.values():
        if update_callback.__self__.unique_id == entity_reg.unique_id:
            return update_callback.__self__
