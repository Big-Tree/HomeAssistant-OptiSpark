from http import HTTPStatus

import aiohttp
import jwt
import time

from custom_components.optispark.const import LOGGER
from custom_components.optispark.configuration_service import config_service
from custom_components.optispark.backend.auth.model.login_response import LoginResponse
from custom_components.optispark.backend.exception.exceptions import OptisparkApiClientAuthenticationError


class AuthService:

    def __init__(
            self,
            session: aiohttp.ClientSession,
            user_hash: str
    ) -> None:
        """Sample API Client."""
        self._login_response = None
        self._session = session
        self._base_url = config_service.get('backend.baseUrl')
        self._ssl = config_service.get('backend.verifySSL', default=True)
        self._token = None
        self._user_hash = user_hash

    async def login(self) -> LoginResponse:
        auth_url = f'{self._base_url}/auth/ha_login'
        try:
            payload = {"user_hash": self._user_hash}
            response = await self._session.post(
                url=auth_url,
                json=payload,
                ssl=self._ssl
            )

            if response.status != HTTPStatus.OK:
                raise OptisparkApiClientAuthenticationError(
                    "Invalid credentials",
                ) from Exception

            json_response = await response.json()
            self._token = json_response["accessToken"]
            self._login_response = LoginResponse(
                token=json_response["accessToken"],
                token_type=json_response["tokenType"],
                has_locations=json_response["hasLocations"],
                has_devices=json_response["hasDevices"],
            )

            return self._login_response

        except aiohttp.ClientError as e:
            LOGGER.error(f"HTTP error occurred: {e}")
            raise OptisparkApiClientAuthenticationError(
                "Invalid credentials",
            ) from e
        except Exception as e:
            LOGGER.error(f"Unexpected error occurred: {e}")
            raise

    @property
    async def token(self) -> str:
        if self._is_token_expired() and self._user_hash:
            self._login_response: LoginResponse = await self.login()
            self._token = self._login_response.token
        return self._token

    @property
    def login_response(self) -> LoginResponse:
        return self._login_response

    def _is_token_expired(self):
        try:
            # Decodes and checks token expiration
            payload = jwt.decode(self._token, options={"verify_signature": False})
            exp_timestamp = payload.get('exp', 0)
            current_timestamp = time.time()
            return current_timestamp > exp_timestamp
        except jwt.ExpiredSignatureError:
            return True
        except jwt.DecodeError:
            return True