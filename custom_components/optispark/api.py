"""Optispark API Client."""
from __future__ import annotations

import asyncio
import socket

import aiohttp
import async_timeout
from decimal import Decimal
from datetime import datetime
import pickle
import gzip
import base64
from .const import LOGGER


class OptisparkApiClientError(Exception):
    """Exception to indicate a general API error."""


class OptisparkApiClientTimeoutError(
    OptisparkApiClientError
):
    """Lamba probably took too long starting up."""


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


class OptisparkApiClientUnitError(
    OptisparkApiClientError
):
    """Exception to indicate unit error."""


def floats_to_decimal(obj):
    """Convert data types to those supported by DynamoDB."""
    # Base cases
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, int):
        return obj
    elif isinstance(obj, str):
        return obj
    elif obj is None:
        return None
    # Go deeper
    elif isinstance(obj, dict):
        return {floats_to_decimal(key): floats_to_decimal(value) for key, value in obj.items()}
    elif isinstance(obj, set):
        return {floats_to_decimal(element) for element in obj}
    elif isinstance(obj, list):
        return [floats_to_decimal(element) for element in obj]
    elif isinstance(obj, tuple):
        return (floats_to_decimal(element) for element in obj)
    elif isinstance(obj, datetime):
        return floats_to_decimal(obj.timestamp())
    else:
        LOGGER.error(f'Object of type {type(obj)} not supported by DynamoDB')
        raise TypeError(f'Object of type {type(obj)} not supported by DynamoDB')


class OptisparkApiClient:
    """Optispark API Client."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
    ) -> None:
        """Sample API Client."""
        self._session = session

    async def upload_history(self, dynamo_data):
        """Upload historical data to dynamoDB without calculating heat pump profile."""
        lambda_url = 'https://lhyj2mknjfmatuwzkxn4uuczrq0fbsbd.lambda-url.eu-west-2.on.aws/'
        payload = {'dynamo_data': dynamo_data}
        payload['upload_only'] = True
        await self._api_wrapper(
            method="post",
            url=lambda_url,
            data=payload,
            headers={"Content-type": "application/json; charset=UTF-8"},
        )

    async def async_get_data(self, lambda_args: dict, dynamo_data: dict) -> any:
        """Upload historical data to dynamoDB and calculate heat pump profile."""
        lambda_url = 'https://lhyj2mknjfmatuwzkxn4uuczrq0fbsbd.lambda-url.eu-west-2.on.aws/'

        payload = lambda_args
        payload['dynamo_data'] = dynamo_data
        results, errors, extra = await self._api_wrapper(
            method="post",
            url=lambda_url,
            data=payload,
            headers={"Content-type": "application/json; charset=UTF-8"},
        )
        LOGGER.debug('----------Lambda request----------')
        if errors['success'] is False:
            LOGGER.debug(f'OptisparkApiClientLambdaError: {errors["error_message"]}')
            raise OptisparkApiClientLambdaError(errors['error_message'])
        if results['optimised_cost'] == 0:
            # Heating isn't active.  Should the savings be 0?
            results['projected_percent_savings'] = 100
        else:
            results['projected_percent_savings'] = results['base_cost']/results['optimised_cost']*100 - 100
        return results, extra['oldest_dates']

    async def _api_wrapper(
        self,
        method: str,
        url: str,
        data: dict | None = None,
        headers: dict | None = None,
    ):
        """Call the Lambda function."""
        try:
            data['dynamo_data'] = floats_to_decimal(data['dynamo_data'])
            uncompressed_data = pickle.dumps(data)
            compressed_data = gzip.compress(uncompressed_data)
            LOGGER.debug(f'len(uncompressed_data): {len(uncompressed_data)}')
            LOGGER.debug(f'len(compressed_data): {len(compressed_data)}')
            base64_string = base64.b64encode(compressed_data).decode('utf-8')

            async with async_timeout.timeout(40):
                response = await self._session.request(
                    method=method,
                    url=url,
                    #headers=headers,
                    json=base64_string,
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
            LOGGER.error('OptisparkApiClientTimeoutError:\n  Timeout error fetching information')
            raise OptisparkApiClientTimeoutError(
                "Timeout error fetching information",
            ) from exception
        except (aiohttp.ClientError, socket.gaierror) as exception:
            LOGGER.error('OptisparkApiClientCommunicationError:\n  Error fetching information')
            raise OptisparkApiClientCommunicationError(
                "Error fetching information",
            ) from exception
        except Exception as exception:  # pylint: disable=broad-except
            LOGGER.error('OptisparkApiClientError:\n  Something really wrong happened!')
            raise OptisparkApiClientError(
                "Something really wrong happened!"
            ) from exception
