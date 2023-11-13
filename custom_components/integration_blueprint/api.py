"""Sample API Client."""
from __future__ import annotations

import asyncio
import socket

import aiohttp
import async_timeout


class IntegrationBlueprintApiClientError(Exception):
    """Exception to indicate a general API error."""


class IntegrationBlueprintApiClientCommunicationError(
    IntegrationBlueprintApiClientError
):
    """Exception to indicate a communication error."""


class IntegrationBlueprintApiClientAuthenticationError(
    IntegrationBlueprintApiClientError
):
    """Exception to indicate an authentication error."""


class IntegrationBlueprintApiClient:
    """Sample API Client."""

    def __init__(
        self,
        postcode: str,
        #username: str,
        #password: str,
        session: aiohttp.ClientSession,
    ) -> None:
        """Sample API Client."""
        #self._username = username
        #self._password = password
        self._session = session

    async def async_get_data(self) -> any:
        """Get data from the API."""
        args = {}
        args['house_type'] = 2
        args['set_point'] = 20.0
        args['temp_range'] = 3.0
        args['postcode'] = 'SW118DD'

        lambda_url = 'https://pkgy5zrwinj2mcxerishahglvi0hfoqh.lambda-url.eu-west-2.on.aws/0.00001666670.0000166667'
        #results, errors = json.loads(response.text)

        results = await self._api_wrapper(
            method="post",
            url=lambda_url,
            data=args,
            headers={"Content-type": "application/json; charset=UTF-8"},
        )
        print('----------Lambda request----------')
        return results[0]




        return await self._api_wrapper(
            method="get", url="https://jsonplaceholder.typicode.com/posts/1"
        )

    async def async_set_title(self, value: str) -> any:
        """Get data from the API."""
        return await self._api_wrapper(
            method="patch",
            url="https://jsonplaceholder.typicode.com/posts/1",
            data={"title": value},
            headers={"Content-type": "application/json; charset=UTF-8"},
        )

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
                    raise IntegrationBlueprintApiClientAuthenticationError(
                        "Invalid credentials",
                    )
                response.raise_for_status()
                return await response.json()

        except asyncio.TimeoutError as exception:
            raise IntegrationBlueprintApiClientCommunicationError(
                "Timeout error fetching information",
            ) from exception
        except (aiohttp.ClientError, socket.gaierror) as exception:
            raise IntegrationBlueprintApiClientCommunicationError(
                "Error fetching information",
            ) from exception
        except Exception as exception:  # pylint: disable=broad-except
            raise IntegrationBlueprintApiClientError(
                "Something really wrong happened!"
            ) from exception
