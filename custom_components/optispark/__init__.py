"""Custom integration to integrate optispark with Home Assistant.

For more details about this integration, please refer to
https://github.com/Big-Tree/HomeAssistant-OptiSpark
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .api import OptisparkApiClient
from .const import DOMAIN, LOGGER
from custom_components.optispark.domain.address.address import Address

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.NUMBER,
    Platform.CLIMATE,
]


# https://developers.home-assistant.io/docs/config_entries_index/#setting-up-an-entry
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up this integration using UI."""
    from .backend_update_handler import BackendUpdateHandler  # Prevent circular import
    from .coordinator import OptisparkDataUpdateCoordinator
    from .climate import OptisparkClimate

    address = Address(
        address=entry.data["address"],
        postcode=entry.data["postcode"],
        city=entry.data["city"],
        country=entry.data["country"]
    )

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator = OptisparkDataUpdateCoordinator(
        hass=hass,
        client=OptisparkApiClient(
            session=async_get_clientsession(hass),
            user_hash=entry.data["user_hash"],
            address=address
        ),
        climate_entity_id=entry.data["climate_entity_id"],
        heat_pump_power_entity_id=entry.data["heat_pump_power_entity_id"],
        external_temp_entity_id=entry.data["external_temp_entity_id"],
        user_hash=entry.data["user_hash"],
        postcode=entry.data["postcode"],
        tariff=entry.data["tariff"],
        address=entry.data["address"],
        city=entry.data["city"],
        country=entry.data["country"],
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


class OptisparkGetEntityError(Exception):
    """An error occured when trying to get the entity using get_entity."""


def get_entity(hass, entity_id):
    """Get entity instance from entity_id.

    All integrations have their data stored in hass.data[domain]
    HA integrations such as climate, switch, binary sensor have get_entity() methods that fetch
    any entities that belong to that domain, or platforms that have implemented that domain.  This
    includes 3rd party integrations that have implemented HA integrations (as a platform).

    Scan for entity_id with all integrations that implement get_method(). We assume that only one
    entity instance will be found.
    """

    entities_found = []
    successful_domains = []
    for domain in hass.data:
        if hasattr(hass.data[domain], "get_entity"):
            entity = hass.data[domain].get_entity(entity_id)
            if entity is not None:
                entities_found.append(entity)
                successful_domains.append(domain)
    if len(entities_found) != 1:
        LOGGER.error(f"({len(entities_found)}) entities found instead of 1")
        LOGGER.error(f"successful_domains:\n  {successful_domains}")
        LOGGER.error(f"entities_found:\n  {entities_found}")
        LOGGER.error(f"hass.data.keys():\n  {hass.data.keys()}")
        raise OptisparkGetEntityError(
            f"({len(entities_found)}) entities found instead of 1"
        )
    return entities_found[0]


def get_username(hass):
    """Attempt to get the username.

    Surely there is a better way than this.
    """
    try:
        return list(hass.data["person"][1].data.keys())[0]
    except Exception:
        return None
