"""Optispark API Client."""

from __future__ import annotations
from typing import List

import aiohttp

from decimal import Decimal
from datetime import datetime, timezone

from . import const


from .configuration_service import ConfigurationService, config_service
from .const import LOGGER, TARIFF_PRODUCT_CODE, TARIFF_CODE

from .domain.thermostat.thermostat_info import ThermostatInfo
from custom_components.optispark.domain.address.address import Address
from .domain.control.control_info import ControlInfo
from .backend.auth.auth_service import AuthService
from .backend.auth.model.login_response import LoginResponse
from .backend.device.device_service import DeviceService
from .backend.device.model.device_data_request import DeviceDataRequest
from .backend.device.model.device_request import DeviceRequest
from .backend.device.model.device_response import DeviceResponse
from .backend.location.location_service import LocationService
from .backend.location.model.location_request import (
    LocationRequest,
)
from .backend.location.model.location_response import LocationResponse

from .backend.shared.model.working_mode import WorkingMode
from .backend.thermostat.model.thermostat_control_request import ThermostatControlRequest
from .backend.thermostat.model.thermostat_control_response import (
    ThermostatControlResponse,
)
from .backend.thermostat.model.thermostat_control_status import ThermostatControlStatus
from .backend.thermostat.model.thermostat_prediction import ThermostatPrediction
from .backend.thermostat.thermostat_service import ThermostatService
from .utils import to_thermostat_info

BACKEND_URL = "backend.url"


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
        return {
            floats_to_decimal(key): floats_to_decimal(value)
            for key, value in obj.items()
        }
    elif isinstance(obj, set):
        return {floats_to_decimal(element) for element in obj}
    elif isinstance(obj, list):
        return [floats_to_decimal(element) for element in obj]
    elif isinstance(obj, tuple):
        return (floats_to_decimal(element) for element in obj)
    elif isinstance(obj, datetime):
        return floats_to_decimal(obj.timestamp())
    else:
        LOGGER.error(f"Object of type {type(obj)} not supported by DynamoDB")
        raise TypeError(f"Object of type {type(obj)} not supported by DynamoDB")


class OptisparkApiClient:
    """Optispark API Client."""

    _token: str | None
    _user_hash: str
    _has_locations: bool
    _has_devices: bool
    _address: Address
    _auth_service: AuthService
    _location_service: LocationService
    _config_service: ConfigurationService
    _thermostat_id: int
    # This is temporal
    _graph_data: dict

    def __init__(
        self, session: aiohttp.ClientSession, user_hash: str, address: Address
    ) -> None:
        """Sample API Client."""
        self._session = session
        self._user_hash = user_hash
        self._address = address
        self._has_locations = False
        self._has_devices = False
        self._auth_service = AuthService(session=session, user_hash=user_hash)
        self._location_service = LocationService(session=session)
        self._device_service = DeviceService(session=session)
        self._thermostat_service = ThermostatService(session=session)
        self._config_service: ConfigurationService = config_service

    def datetime_set_utc(self, d: dict[str, datetime]):
        """Set the timezone of the datetime values to UTC."""
        for key in d:
            if d[key] is None:
                continue
            d[key] = d[key].replace(tzinfo=timezone.utc)
        return d

    # TODO: remove this method
    async def check_and_set_manual(self, data: ControlInfo) -> ThermostatControlResponse:
        """Checks if optispark is running in manual, if not set manual mode"""
        control = await self.get_thermostat_control()
        if not control.status == ThermostatControlStatus.MANUAL:
            LOGGER.info(
                f"Control in {control.status} status, requesting manual mode..."
            )
            LOGGER.debug(f" {control.status} --> generating manual control request")
            control = await self.create_manual(
                thermostat_id=control.thermostat_id,
                set_point=data.set_point,
                mode=data.mode,
            )
            LOGGER.info(
                f"Created: {control.status} - {control.mode} - {control.heat_set_point} -/"
                f" {control.cool_set_point}"
            )
        return control

    async def get_data_dates(self):
        """Call lambda and only get the newest and oldest dates in dynamo.
        dynamo_data will only contain the user_hash.
        """

        # 3f009bbd4f13f05061d40e980c86e817c60835017a152d3bf3efa089196665d9
        LOGGER.debug(self._user_hash)
        token = await self._auth_service.token
        control = await self.get_thermostat_control()
        self._graph_data: List[
            ThermostatPrediction
        ] = await self._thermostat_service.get_graph(
            access_token=token, thermostat_id=control.thermostat_id
        )

        oldest_date = self._graph_data[0].date
        newest_date = self._graph_data[-1].date

        extra = {
            "oldest_dates": {
                "heat_pump_power": oldest_date,
                "external_temperature": oldest_date,
                "climate_entity": oldest_date,
            },
            "newest_dates": {
                "heat_pump_power": newest_date,
                "external_temperature": newest_date,
                "climate_entity": newest_date,
            },
        }

        oldest_dates = self.datetime_set_utc(extra["oldest_dates"])
        newest_dates = self.datetime_set_utc(extra["newest_dates"])

        return oldest_dates, newest_dates

    async def async_get_profile(self, lambda_args: dict):
        """Get heat pump profile only."""
        LOGGER.debug("Fetching profile")
        payload = lambda_args
        payload["get_profile_only"] = True
        if not self._graph_data:
            token = await self._auth_service.token
            control = await self.get_thermostat_control()
            self._graph_data: List[
                ThermostatPrediction
            ] = await self._thermostat_service.get_graph(
                access_token=token, thermostat_id=control.thermostat_id
            )

        if self._graph_data[0].date.tzinfo is None:
            self._graph_data[0].date = self._graph_data[0].date.replace(
                tzinfo=timezone.utc
            )

        results = {
            "timestamp": [self._graph_data[0].date],
            "electricity_price": [10],
            "base_power": [15],
            "optimised_power": [10],
            "optimised_internal_temp": [self._graph_data[0].set_point],
            "external_temp": [self._graph_data[0].set_point],
            "temp_controls": [2],
            "dni": [10],
            "total_cost_optimised": 1.3,
            "base_cost": 1.0,
            "optimised_cost": 2.0,
        }

        if results["optimised_cost"] == 0:
            # Heating isn't active.  Should the savings be 0?
            results["projected_percent_savings"] = 100
        else:
            results["projected_percent_savings"] = (
                results["base_cost"] / results["optimised_cost"] * 100 - 100
            )
        return results

    async def get_thermostat_control(self) -> ThermostatControlResponse:
        LOGGER.debug('Fetching thermostat control')
        token = await self._auth_service.token
        locations = await self._location_service.get_locations(token)
        if len(locations) > 0:
            thermostat_id = locations[0].thermostat_id
            control = await self._thermostat_service.get_control(
                thermostat_id=thermostat_id, access_token=token
            )
            LOGGER.debug(f'id:{control.thermostat_id} {control.mode} {control.status}')
            return control

    async def get_thermostat_info(self) -> ThermostatInfo:
        token = await self._auth_service.token
        locations = await self._location_service.get_locations(token)
        if len(locations) > 0:
            thermostat_id = locations[0].thermostat_id
            LOGGER.debug(f"Getting thermostat control mode")
            control = await self._thermostat_service.get_control(
                thermostat_id=thermostat_id, access_token=token
            )
            return to_thermostat_info(control)

    async def set_manual(self, data: ControlInfo) -> ThermostatControlResponse | None:
        """Sends manual request to backend"""
        response = None
        mode = WorkingMode.from_string(data.mode)
        heat_set_point = data.set_point
        cool_set_point = data.set_point
        if mode == WorkingMode.COOLING:
            heat_set_point = None
        if mode == WorkingMode.HEATING:
            cool_set_point = None
        request = ThermostatControlRequest(
            mode=mode,
            heat_set_point=heat_set_point,
            cool_set_point=cool_set_point
        )
        LOGGER.debug('Post thermostat control request')
        LOGGER.debug(request)
        token = await self._auth_service.token
        locations = await self._location_service.get_locations(token)
        if locations[0]:
            response = await self._thermostat_service.create_manual(
                thermostat_id=locations[0].thermostat_id,
                request=request,
                access_token=token
            )
        return response
        # request =

    async def create_manual(
        self, thermostat_id: int, set_point: float, mode: str
    ) -> ThermostatControlResponse:
        request = ThermostatControlRequest(
            mode=WorkingMode.from_string(mode),
            heat_set_point=set_point,
            cool_set_point=set_point,
        )
        token = await self._auth_service.token
        result = await self._thermostat_service.create_manual(
            thermostat_id=thermostat_id, request=request, access_token=token
        )
        return result

    async def check_location_and_device(self):

        if self._has_locations and self._has_devices:
            return

        login_response = await self._auth_service.login()
        if not login_response:
            login_response: LoginResponse = await self._auth_service.login()

        self._has_locations = login_response.has_locations
        self._has_devices = login_response.has_devices

        token = login_response.token
        location: LocationResponse | None = None
        if not self._has_locations:
            location_request = LocationRequest(
                name="home",
                address=self._address.address,
                zipcode=self._address.postcode,
                city=self._address.city,
                country=self._address.country,
                tariff_id=1,
                tariff_params={
                    "product_code": TARIFF_PRODUCT_CODE,
                    "tariff_code": TARIFF_CODE,
                },
            )
            location: (
                LocationResponse | None
            ) = await self._location_service.add_location(
                request=location_request, access_token=token
            )
            self._has_locations = True if location else False
        if not self._has_devices:
            if not location:
                locations: [
                    LocationResponse
                ] = await self._location_service.get_locations(access_token=token)
                LOGGER.debug(locations[0])
                location = locations[0]

            device_request = DeviceRequest(
                name="Heat Pump",
                location_id=location.id,
                manufacturer="ha",
                model_name="ha_model",
                version="version",
                integration_params={},
            )
            device_response: (
                DeviceResponse | None
            ) = await self._device_service.add_device(
                request=device_request, access_token=token
            )

            self._has_devices = True if device_response else False

    async def update_device_data(self, lambda_args):

        LOGGER.debug('Sending device data to backend')

        internal_temp = None
        humidity = None
        power = None
        temp_range = None
        set_point = None

        if const.LAMBDA_OPTIMISED_DEMAND in lambda_args:
            power = lambda_args[const.LAMBDA_OPTIMISED_DEMAND]
        if const.LAMBDA_INITIAL_INTERNAL_TEMP in lambda_args:
            set_point = lambda_args[const.LAMBDA_INITIAL_INTERNAL_TEMP]
        if const.LAMBDA_SET_POINT in lambda_args:
            set_point = lambda_args[const.LAMBDA_SET_POINT]
        if const.LAMBDA_INITIAL_INTERNAL_TEMP in lambda_args:
            internal_temp = lambda_args[const.LAMBDA_INITIAL_INTERNAL_TEMP]
        if const.LAMBDA_TEMP_RANGE in lambda_args:
            temp_range = lambda_args[const.LAMBDA_TEMP_RANGE]

        if set_point and temp_range and internal_temp:

            request = DeviceDataRequest(
                internal_temp=internal_temp,
                humidity=humidity,
                power=power,
                mode=WorkingMode.HEATING,
                heat_set_point=set_point,
                cool_set_point=None,

            )
            token = await self._auth_service.token
            locations: [LocationResponse] = await self._location_service.get_locations(access_token=token)
            if len(locations) > 0:
                LOGGER.debug(f'{len(locations)} found')
                devices: [DeviceResponse] = await self._device_service.get_devices(location_id=locations[0].id ,access_token=token)

                # 🐷 SAFETY PIG: assuming only one location and device per user
                if len(devices) > 0:
                    LOGGER.debug(f'{len(devices)} found for location {locations[0].id}')
                    device_id = devices[0].id
                    token = await self._auth_service.token
                    await self._device_service.add_device_data(device_id=device_id, request=request, access_token=token)


