from http import HTTPStatus
from typing import List

import aiohttp
from aiohttp import ClientResponse

from custom_components.optispark.const import LOGGER
from custom_components.optispark.configuration_service import config_service
from custom_components.optispark.backend.device.model.device_data_request import DeviceDataRequest
from custom_components.optispark.backend.device.model.device_request import DeviceRequest
from custom_components.optispark.backend.device.model.device_response import DeviceResponse
from custom_components.optispark.backend.exception.exceptions import OptisparkApiClientAuthenticationError, \
    OptisparkApiClientDeviceError


class DeviceService:

    def __init__(
        self,
        session: aiohttp.ClientSession,
    ) -> None:
        """Sample API Client."""
        self._session = session
        self._base_url = config_service.get("backend.baseUrl")
        self._ssl = config_service.get('backend.verifySSL', default=True)

    async def get_devices(self, location_id: int, access_token: str) -> List[DeviceResponse]:
        device_url = f'{self._base_url}/{config_service.get("backend.device.base")}/'
        headers = {
            "Authorization": f"Bearer {access_token}"
        }

        try:
            response = await self._session.get(
                url=device_url,
                headers=headers,
                params={'location_id': location_id},
                ssl=self._ssl
            )

            if response.status == HTTPStatus.UNAUTHORIZED:
                raise OptisparkApiClientAuthenticationError(
                    "Invalid credentials",
                ) from Exception

            if response.status != HTTPStatus.OK:
                raise OptisparkApiClientDeviceError(
                    "Get devices error",
                ) from Exception

            json_response = await response.json()
            devices = list(map(DeviceResponse.from_json, json_response))
            # Filter out any None values in case of invalid JSON elements
            return [device for device in devices if devices is not None]

        except aiohttp.ClientError as e:
            LOGGER.error(f"HTTP error occurred: {e}")
            raise OptisparkApiClientDeviceError("Get devices error") from e
        except Exception as e:
            LOGGER.error(f"Unexpected error occurred: {e}")
            raise

    async def add_device(self, request: DeviceRequest, access_token: str) -> DeviceResponse | None:

        device_url = f'{self._base_url}/{config_service.get("backend.device.base")}/'
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        try:
            response: ClientResponse = await self._session.post(
                url=device_url,
                headers=headers,
                json=request.payload(),
                ssl=self._ssl
            )

            if response.status == HTTPStatus.UNAUTHORIZED:
                raise OptisparkApiClientAuthenticationError(
                    "Invalid credentials",
                ) from Exception

            if response.status != HTTPStatus.CREATED:
                raise OptisparkApiClientDeviceError(
                    "Add device error",
                ) from Exception

            json_response = await response.json()
            return DeviceResponse.from_json(json_response)

        except aiohttp.ClientError as e:
            LOGGER.error(f"HTTP error occurred: {e}")
            raise OptisparkApiClientDeviceError("Add device error") from e
        except Exception as e:
            LOGGER.error(f"Unexpected error occurred: {e}")
            raise

    async def add_device_data(self, device_id: int, request: DeviceDataRequest, access_token: str) -> bool:

        endpoint = config_service.get("backend.device.data")
        device_url = f'{self._base_url}/{endpoint}'.replace("{device_id}", str(device_id))
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        try:
            response = await self._session.post(
                url=device_url,
                headers=headers,
                json=request.payload(),
                ssl=self._ssl
            )

            if response.status == HTTPStatus.UNAUTHORIZED:
                raise OptisparkApiClientAuthenticationError(
                    "Invalid credentials",
                ) from Exception

            if response.status != HTTPStatus.CREATED:
                raise OptisparkApiClientDeviceError(
                    "Add device data error",
                ) from Exception

            return True

        except aiohttp.ClientError as e:
            LOGGER.error(f"HTTP error occurred: {e}")
            raise OptisparkApiClientDeviceError("Add device data error") from e
        except Exception as e:
            LOGGER.error(f"Unexpected error occurred: {e}")
            raise
