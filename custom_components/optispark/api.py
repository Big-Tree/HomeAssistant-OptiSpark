"""Optispark API Client."""
from __future__ import annotations

import asyncio
import socket

import aiohttp
import async_timeout
from .const import LOGGER


class OptisparkApiClientError(Exception):
    """Exception to indicate a general API error."""


class OptisparkApiClientCommunicationError(
    OptisparkApiClientError
):
    """Exception to indicate a communication error."""


class OptisparkApiClientAuthenticationError(
    OptisparkApiClientError
):
    """Exception to indicate an authentication error."""


class OptisparkApiClientLambdaError(
    OptisparkApiClientError
):
    """Exception to indicate lambda return an error."""


class OptisparkApiClientPostcodeError(
    OptisparkApiClientError
):
    """Exception to indicate invalid postcode."""


class OptisparkApiClient:
    """Sample API Client."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
    ) -> None:
        """Sample API Client."""
        self._session = session

    async def async_get_data(self, lambda_args) -> any:
        """Get data from the API."""
        lambda_url = 'https://pkgy5zrwinj2mcxerishahglvi0hfoqh.lambda-url.eu-west-2.on.aws/0.00001666670.0000166667'
        #results, errors = json.loads(response.text)

        results, errors = await self._api_wrapper(
            method="post",
            url=lambda_url,
            data=lambda_args,
            headers={"Content-type": "application/json; charset=UTF-8"},
        )
        LOGGER.debug('----------Lambda request----------')
        if errors['success'] is False:
            LOGGER.debug(f'OptisparkApiClientLambdaError: {errors["error_message"]}')
            raise OptisparkApiClientLambdaError(errors['error_message'])
        results['projected_percent_savings'] = results['base_cost']/results['optimised_cost']*100 - 100
        return results

    async def _api_wrapper(
        self,
        method: str,
        url: str,
        data: dict | None = None,
        headers: dict | None = None,
    ) -> any:
        """Get information from the API."""
        try:
            async with async_timeout.timeout(40):
                response = await self._session.request(
                    method=method,
                    url=url,
                    #headers=headers,
                    json=data,
                )
                if response.status in (401, 403):
                    raise OptisparkApiClientAuthenticationError(
                        "Invalid credentials",
                    )
                if response.status == 502:
                    # HomeAssistant will not print errors if there was never a successful update
                    LOGGER.debug('OptisparkApiClientCommunicationError:\n  502 Bad Gateway - check payload')
                    raise OptisparkApiClientCommunicationError(
                        '502 Bad Gateway - check payload')
                response.raise_for_status()
                return await response.json()

        except asyncio.TimeoutError as exception:
            LOGGER.debug('OptisparkApiClientCommunicationError:\n  Timeout error fetching information')
            raise OptisparkApiClientCommunicationError(
                "Timeout error fetching information",
            ) from exception
        except (aiohttp.ClientError, socket.gaierror) as exception:
            raise OptisparkApiClientCommunicationError(
                "Error fetching information",
            ) from exception
        except Exception as exception:  # pylint: disable=broad-except
            raise OptisparkApiClientError(
                "Something really wrong happened!"
            ) from exception
