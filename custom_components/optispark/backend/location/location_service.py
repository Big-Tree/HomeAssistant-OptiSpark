from http import HTTPStatus

import aiohttp

from custom_components.optispark.const import LOGGER
from custom_components.optispark.configuration_service import config_service
from custom_components.optispark.backend.exception.exceptions import (
    OptisparkApiClientAuthenticationError,
    OptisparkApiClientLocationError,
)
from custom_components.optispark.backend.location.model.location_request import (
    LocationRequest,
)
from custom_components.optispark.backend.location.model.location_response import LocationResponse


class LocationService:
    def __init__(
        self,
        session: aiohttp.ClientSession,
    ) -> None:
        """Sample API Client."""
        self._session = session
        self._base_url = config_service.get("backend.baseUrl")
        self._ssl = config_service.get('backend.verifySSL', default=True)

    async def add_location(self, request: LocationRequest, access_token: str) -> LocationResponse | None:
        """Add new location"""

        location_url = f'{self._base_url}/{config_service.get("backend.location.base")}/'
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        try:
            response = await self._session.post(
                url=location_url,
                headers=headers,
                json=request.payload(),
                ssl=self._ssl
            )

            if response.status == HTTPStatus.UNAUTHORIZED:
                raise OptisparkApiClientAuthenticationError(
                    "Invalid credentials",
                ) from Exception

            if response.status != HTTPStatus.CREATED:
                raise OptisparkApiClientLocationError(
                    "Add location error",
                ) from Exception

            json_response = await response.json()
            return LocationResponse.from_json(json_response)

        except aiohttp.ClientError as e:
            LOGGER.error(f"HTTP error occurred: {e}")
            raise OptisparkApiClientLocationError("Add location error") from e
        except Exception as e:
            LOGGER.error(f"Unexpected error occurred: {e}")
            raise

    async def get_locations(self, access_token: str) -> [LocationResponse]:
        """Get locations from OptiSpark backend"""
        location_url = f'{self._base_url}/{config_service.get("backend.location.base")}/'
        headers = {
            "Authorization": f"Bearer {access_token}"
        }

        try:
            response = await self._session.get(
                url=location_url,
                headers=headers,
                ssl=self._ssl
            )

            if response.status == HTTPStatus.UNAUTHORIZED:
                raise OptisparkApiClientAuthenticationError(
                    "Invalid credentials",
                ) from Exception

            if response.status != HTTPStatus.OK:
                raise OptisparkApiClientLocationError(
                    "Get locations error",
                ) from Exception

            json_response = await response.json()
            locations = list(map(LocationResponse.from_json, json_response))
            # Filter out any None values in case of invalid JSON elements
            return [location for location in locations if location is not None]

        except aiohttp.ClientError as e:
            LOGGER.error(f"HTTP error occurred: {e}")
            raise OptisparkApiClientLocationError("Get locations error") from e
        except Exception as e:
            LOGGER.error(f"Unexpected error occurred: {e}")
            raise

