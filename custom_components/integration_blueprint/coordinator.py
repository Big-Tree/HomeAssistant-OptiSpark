"""DataUpdateCoordinator for integration_blueprint."""
from __future__ import annotations

from datetime import timedelta, datetime
import time

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.exceptions import ConfigEntryAuthFailed

from .api import (
    IntegrationBlueprintApiClient,
    IntegrationBlueprintApiClientAuthenticationError,
    IntegrationBlueprintApiClientError,
)
from .const import DOMAIN, LOGGER


def get_closest_time(my_data):
    """Get the closest matching time to now from the data set provided"""
    # Convert time to dattime format
    times_str: list[str] = list(my_data['base_demand'].keys())
    times = [datetime.strptime(d, '%Y-%m-%d %H:%M') for d in times_str]
    now = datetime.now()
    absolute_difference = [abs(getattr(t-now, 'total_seconds')()) for t in times]
    min_idx = absolute_difference.index(min(absolute_difference))
    closest_time = times_str[min_idx]

    out = {}
    for key in ['base_demand', 'prices', 'temps', 'optimised_demand']:
        out[key] = my_data[key][closest_time]
    for key in ['optimised_cost', 'base_cost']:
        out[key] = my_data[key]
    return out


# https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
class BlueprintDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        client: IntegrationBlueprintApiClient,
    ) -> None:
        """Initialize."""
        self.client = client
        super().__init__(
            hass=hass,
            logger=LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=10),
        )
        self.results = {}
        self.last_update_time = 0
        self.update_lambda_interval = 60*60

    async def _async_update_data(self):
        """Update data via library."""
        try:
            if time.time() - self.last_update_time > self.update_lambda_interval:
                lambda_results = await self.client.async_get_data()

                # Convert to dictionary where time is the key
                self.my_data = {}
                for key in ['base_demand', 'prices', 'temps', 'optimised_demand']:
                    self.my_data[key] = {i['x']: i['y'] for i in lambda_results[key]}
                for key in ['optimised_cost', 'base_cost']:
                    self.my_data[key] = lambda_results[key]

                out = get_closest_time(self.my_data)

                self.last_update_time = time.time()
                return out
            else:
                out = get_closest_time(self.my_data)
                return out
            #return await self.client.async_get_data()
        except IntegrationBlueprintApiClientAuthenticationError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except IntegrationBlueprintApiClientError as exception:
            raise UpdateFailed(exception) from exception
