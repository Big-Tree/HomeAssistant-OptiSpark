from datetime import timedelta, datetime
from http import HTTPStatus
from typing import List

import aiohttp

from custom_components.optispark.const import LOGGER
from custom_components.optispark.configuration_service import ConfigurationService, config_service
from custom_components.optispark.backend.exception.exceptions import OptisparkApiClientAuthenticationError, \
    OptisparkApiClientThermostatError
from custom_components.optispark.backend.thermostat.model.thermostat_control_request import ThermostatControlRequest
from custom_components.optispark.backend.thermostat.model.thermostat_control_response import ThermostatControlResponse
from custom_components.optispark.backend.thermostat.model.thermostat_prediction import ThermostatPrediction

CACHE_REFRESH_INTERVAL = timedelta(seconds=300)
class ThermostatService:

    def __init__(
        self,
        session: aiohttp.ClientSession,
    ) -> None:
        """Sample API Client."""
        self._session = session
        self._config_service: ConfigurationService = config_service
        self._base_url = config_service.get("backend.baseUrl")
        self._ssl = config_service.get("backend.verifySSL")
        self._cache = {}

    async def get_control(self, thermostat_id: int, access_token: str) -> ThermostatControlResponse:
        cache_key = f"{thermostat_id}"
        current_time = datetime.now()

        # Check if the response is in cache and still valid
        if cache_key in self._cache:
            cached_response, timestamp = self._cache[cache_key]
            if current_time - timestamp < CACHE_REFRESH_INTERVAL:
                LOGGER.debug("Returning control from cache")
                return cached_response

        endpoint = config_service.get("backend.thermostat.control")
        thermostat_url = f'{self._base_url}/{endpoint}'.replace("{thermostat_id}", str(thermostat_id))
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        try:
            response = await self._session.get(
                url=thermostat_url,
                headers=headers,
                ssl=self._ssl
            )

            if response.status == HTTPStatus.UNAUTHORIZED:
                raise OptisparkApiClientAuthenticationError(
                    "Invalid credentials",
                ) from Exception

            if response.status != HTTPStatus.OK:
                raise OptisparkApiClientThermostatError(
                    "Get thermostat control error",
                ) from Exception

            json_response = await response.json()
            thermostat_control = ThermostatControlResponse.from_json(json_response)

            if thermostat_control is not None:
                self._cache[cache_key] = (thermostat_control, current_time)

            return thermostat_control

        except aiohttp.ClientError as e:
            LOGGER.error(f"HTTP error occurred: {e}")
            raise OptisparkApiClientThermostatError("get thermostat control error") from e
        except Exception as e:
            LOGGER.error(f"Unexpected error occurred: {e}")
            raise

    async def create_manual(
            self,
            thermostat_id: int,
            request: ThermostatControlRequest,
            access_token: str
    ) -> ThermostatControlResponse:
        cache_key = f"{thermostat_id}"
        current_time = datetime.now()
        # ssl = config_service.get('backend.verifySSL', default=True)
        endpoint = config_service.get("backend.thermostat.manual")
        thermostat_url = f'{self._base_url}/{endpoint}'.replace("{thermostat_id}", str(thermostat_id))
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        try:
            response = await self._session.post(
                url=thermostat_url,
                headers=headers,
                json=request.to_dict(),
                ssl=self._ssl
            )

            if response.status == HTTPStatus.UNAUTHORIZED:
                raise OptisparkApiClientAuthenticationError(
                    "Invalid credentials",
                ) from Exception

            if response.status != HTTPStatus.CREATED:
                raise OptisparkApiClientThermostatError(
                    "Create thermostat manual control error",
                ) from Exception

            json_response = await response.json()
            thermostat_control = ThermostatControlResponse.from_json(json_response)
            if thermostat_control is not None:
                self._cache[cache_key] = (thermostat_control, current_time)
            return thermostat_control

        except aiohttp.ClientError as e:
            LOGGER.error(f"HTTP error occurred: {e}")
            raise OptisparkApiClientThermostatError("post thermostat manual control error") from e
        except Exception as e:
            LOGGER.error(f"Unexpected error occurred: {e}")
            raise

    async def get_graph(self, thermostat_id: int, access_token: str) -> List[ThermostatPrediction]:
        # Graph query param,
        hours_from_now = config_service.get("hoursFromNow")
        endpoint = config_service.get("backend.thermostat.graph")
        graph_url = f'{self._base_url}/{endpoint}'.replace("{thermostat_id}", str(thermostat_id))
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        try:
            response = await self._session.get(
                url=graph_url,
                headers=headers,
                params={'hours_from_now': hours_from_now},
                ssl=self._ssl
            )

            if response.status == HTTPStatus.UNAUTHORIZED:
                raise OptisparkApiClientAuthenticationError(
                    "Invalid credentials",
                ) from Exception

            if response.status != HTTPStatus.OK:
                raise OptisparkApiClientThermostatError(
                    "Get graph error",
                ) from Exception

            json_array = await response.json()
            return [ThermostatPrediction.from_json(item) for item in json_array]

        except aiohttp.ClientError as e:
            LOGGER.error(f"HTTP error occurred: {e}")
            raise OptisparkApiClientThermostatError("get graph error") from e
        except Exception as e:
            LOGGER.error(f"Unexpected error occurred: {e}")
            raise

        