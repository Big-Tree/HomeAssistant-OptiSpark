from datetime import datetime, timezone, timedelta

from custom_components.optispark import OptisparkApiClient, const, LOGGER, history
import numpy as np

from custom_components.optispark.domain.control.control_info import ControlInfo
from custom_components.optispark.backend.thermostat.model.thermostat_control_response import ThermostatControlResponse
from custom_components.optispark.backend.thermostat.model.thermostat_control_status import ThermostatControlStatus


class BackendUpdateHandler:
    """Backend communication handler
    """

    def __init__(
        self,
        hass,
        client: OptisparkApiClient,
        climate_entity_id,
        heat_pump_power_entity_id,
        external_temp_entity_id,
        user_hash,
        postcode,
        address,
        city,
        country,
        tariff,
    ):
        """Init."""
        self.hass = hass
        self.client: OptisparkApiClient = client
        self.climate_entity_id = climate_entity_id
        self.heat_pump_power_entity_id = heat_pump_power_entity_id
        self.external_temp_entity_id = external_temp_entity_id
        self.user_hash = user_hash
        self.postcode = postcode
        self.address = address
        self.country = country
        self.city = city
        self.tariff = tariff
        self.expire_time = datetime(
            1, 1, 1, 0, 0, 0, tzinfo=timezone.utc
        )  # Already expired
        # Interval to upload device data (in seconds)
        self.update_device_data_countdown = const.UPDATE_DEVICE_DATA_INTERVAL
        self.manual_update = False
        self.history_upload_complete = False
        self.outside_range_flag = False
        self.id_to_column_name_lookup = {
            climate_entity_id: const.DATABASE_COLUMN_SENSOR_CLIMATE_ENTITY,
            heat_pump_power_entity_id: const.DATABASE_COLUMN_SENSOR_HEAT_PUMP_POWER,
            external_temp_entity_id: const.DATABASE_COLUMN_SENSOR_EXTERNAL_TEMPERATURE,
        }
        # LOGGER.debug(f"{self.user_hash = }")
        # Entity ids will be None if they are optional and not enabled
        self.active_entity_ids = []
        for entity_id in [
            climate_entity_id,
            heat_pump_power_entity_id,
            external_temp_entity_id,
        ]:
            if entity_id is not None:
                self.active_entity_ids.append(entity_id)

    def get_missing_histories_boundary(self, history_states, dynamo_date):
        """Get index where history_state matches dynamo_date."""
        idx_bound = 0
        for idx, datum in enumerate(history_states):
            if datum.last_updated >= dynamo_date:
                idx_bound = idx
                return idx_bound
        return idx_bound  # type: ignore

    def get_missing_old_histories_states(self, history_states, column):
        """Get states that are older than anything in dynamo."""
        dynamo_date = self.dynamo_oldest_dates[column]
        idx_bound = self.get_missing_histories_boundary(history_states, dynamo_date)
        return history_states[:idx_bound]

    def get_missing_new_histories_states(self, history_states, column):
        """Get states that are newer than anything in dynamo."""
        dynamo_date = self.dynamo_newest_dates[column]
        if dynamo_date is None:
            # No data in dynamo - upload first x days
            dynamo_date = datetime.now(tz=timezone.utc) - timedelta(
                days=const.HISTORY_DAYS
            )
        idx_bound = self.get_missing_histories_boundary(history_states, dynamo_date)
        if idx_bound == len(history_states) - 1:
            error = True
        else:
            error = False
        return history_states[idx_bound + 1 :], error

    async def upload_new_history(self, missing_entities):
        """Upload section of new history states that are newer than anything in dynamo.

        self.dynamo_dates is updated so that if this function is called again a new section will be
        uploaded.
        const.MAX_UPLOAD_HISTORY_READINGS number of readings are uploaded to avoid long delay.
        """
        histories = {}
        constant_attributes = {}

        async def debug_check_history_length(days):
            # history_states = await history.get_state_changes(
            #     self.hass, active_entity_id, days
            # )
            history_states = await history.get_state_changes_period(
                self.hass, active_entity_id, days
            )
            # LOGGER.debug(
            #     f'  history_states[0]: {history_states[0].last_updated.strftime("%Y-%m-%d %H:%M:%S")}'
            # )
            # LOGGER.debug(
            #     f'  history_states[-1]: {history_states[-1].last_updated.strftime("%Y-%m-%d %H:%M:%S")}'
            # )

        for active_entity_id in missing_entities:
            column = self.id_to_column_name_lookup[active_entity_id]
            history_states = await history.get_state_changes(
                self.hass, active_entity_id, const.DYNAMO_HISTORY_DAYS
            )
            missing_new_histories_states, error = self.get_missing_new_histories_states(
                history_states, column
            )
            if error:
                raise RuntimeError(
                    "No missing history data to upload, should not have gotten here"
                )

            LOGGER.debug(f"  column: {column}")
            if len(missing_new_histories_states) == 0:
                LOGGER.debug(f"    ({column}) - Upload complete")
                continue
            LOGGER.debug(
                f"    len(missing_new_histories_states): {len(missing_new_histories_states)}"
            )
            missing_new_histories_states = missing_new_histories_states[
                : const.MAX_UPLOAD_HISTORY_READINGS
            ]
            LOGGER.debug(
                f"    len(missing_new_histories_states): {len(missing_new_histories_states)}"
            )
            LOGGER.debug(
                f'      {missing_new_histories_states[0].last_updated.strftime("%Y-%m-%d %H:%M:%S")}'
            )
            LOGGER.debug(
                f'      {missing_new_histories_states[-1].last_updated.strftime("%Y-%m-%d %H:%M:%S")}'
            )

            histories[column], constant_attributes[column] = (
                history.states_to_histories(
                    self.hass, column, missing_new_histories_states
                )
            )
        if histories == {}:
            raise RuntimeError(
                "Should not have gotten here! No missing history data to upload"
            )
        dynamo_data = history.histories_to_dynamo_data(
            self.hass,
            histories,
            constant_attributes,
            self.user_hash,
            self.climate_entity_id,
            self.postcode,
            self.tariff,
        )
        (
            self.dynamo_oldest_dates,
            self.dynamo_newest_dates,
        ) = await self.client.get_data_dates()
        # ) = await self.client.upload_history(dynamo_data)

    async def upload_old_history(self):
        """Upload section of old history states that are older than anything in dynamo.

        self.dynamo_dates is updated so that if this function is called again a new section will be
        uploaded.
        const.MAX_UPLOAD_HISTORY_READINGS number of readings are uploaded to avoid long delay.
        """
        LOGGER.debug("Uploading portion of old history...")
        histories = {}
        constant_attributes = {}
        for active_entity_id in self.active_entity_ids:
            column = self.id_to_column_name_lookup[active_entity_id]
            history_states = await history.get_state_changes(
                self.hass, active_entity_id, const.DYNAMO_HISTORY_DAYS
            )
            missing_old_histories_states = self.get_missing_old_histories_states(
                history_states, column
            )

            if len(missing_old_histories_states) == 0:
                LOGGER.debug(f"    ({column}) - Upload complete")
                continue
            missing_old_histories_states = missing_old_histories_states[
                -const.MAX_UPLOAD_HISTORY_READINGS:
            ]

            histories[column], constant_attributes[column] = (
                history.states_to_histories(
                    self.hass, column, missing_old_histories_states
                )
            )
        if histories == {}:
            self.history_upload_complete = True
            LOGGER.debug("History upload complete, recalculate heating profile...\n")
            # Now that we have all the history, recalculate heating profile
            self.manual_update = True
            return
        dynamo_data = history.histories_to_dynamo_data(
            self.hass,
            histories,
            constant_attributes,
            self.user_hash,
            self.climate_entity_id,
            self.postcode,
            self.tariff,
        )
        (
            self.dynamo_oldest_dates,
            self.dynamo_newest_dates,
        ) = await self.client.get_data_dates()
        # ) = await self.client.upload_history(dynamo_data)

    async def __call__(self, lambda_args):
        """Return lambda data for the current time.

        Calls lambda if new heating profile is needed
        Otherwise, slowly uploads historical data
        """
        await self.client.check_location_and_device()
        thermostat = await self._check_running_manual_mode(lambda_args)
        # Temporal Fix, heat_set_point could be None
        if thermostat.mode == 'COOLING':
            lambda_args[const.LAMBDA_SET_POINT] = thermostat.cool_set_point if thermostat.cool_set_point else 20
        else:
            lambda_args[const.LAMBDA_SET_POINT] = thermostat.heat_set_point if thermostat.heat_set_point else 20

        now = datetime.now(tz=timezone.utc)
        # This probably won't result in a smooth transition
        if self.expire_time - now < timedelta(hours=0) or self.manual_update:
            await self.get_heating_profile(lambda_args, thermostat_id=thermostat.thermostat_id)

        # Updates counter
        self.update_device_data_countdown = self.update_device_data_countdown - const.UPDATE_INTERVAL
        if self.update_device_data_countdown <= 0:
            LOGGER.debug('Sending device data to OptiSpark backend')
            self.update_device_data_countdown = const.UPDATE_DEVICE_DATA_INTERVAL
            await self._update_device_data(lambda_args)

        return self.get_closest_time(lambda_args)

    async def _update_device_data(self, lambda_args):
        await self.client.update_device_data(lambda_args)

    async def _check_running_manual_mode(self, lambda_args: dict) -> ThermostatControlResponse:
        thermostat_control = await self.client.get_thermostat_control()
        if thermostat_control.status != ThermostatControlStatus.MANUAL:
            data = ControlInfo(
                set_point=lambda_args["temp_set_point"],
                mode=lambda_args["heat_pump_mode_raw"]
            )
            return await self.client.set_manual(data)
        return thermostat_control

    async def update_dynamo_dates(self, lambda_args: dict):
        """Call the lambda function and get the oldest and newest dates in dynamodb."""
        # TODO: create class
        dynamo_data = {
            "user_hash": self.user_hash,
            "postcode": lambda_args["postcode"],
            "address": lambda_args["address"],
            "city": lambda_args["city"],
            "temp_set_point": lambda_args['temp_set_point'],
            "heat_pump_mode_raw": lambda_args['heat_pump_mode_raw']
        }
        (
            self.dynamo_oldest_dates,
            self.dynamo_newest_dates,
        ) = await self.client.get_data_dates()

    async def update_ha_dates(self):
        """Get the oldest and newest dates in HA histories for active_entity_ids."""
        (
            self.ha_oldest_dates,
            self.ha_newest_dates,
        ) = await history.get_earliest_and_latest_data_dates(
            hass=self.hass,
            climate_entity_id=self.climate_entity_id,
            heat_pump_power_entity_id=self.heat_pump_power_entity_id,
            external_temp_entity_id=self.external_temp_entity_id,
        )

    def entities_with_data_missing_from_dynamo(self):
        """Return entities with new data that needs to be uploaded.

        If there is data in HA histories for active_entity_ids that is newer than what is in dynamo,
        return those entities.
        """
        entities_missing = []
        for active_entity_id in self.active_entity_ids:
            column = self.id_to_column_name_lookup[active_entity_id]
            if self.dynamo_newest_dates[column] is None:
                # First run, therefore data is missing
                LOGGER.debug(
                    f"First run, upload ({const.HISTORY_DAYS}) days of history...\n"
                )
                entities_missing.append(active_entity_id)
                continue
            if self.dynamo_newest_dates[column] < self.ha_newest_dates[column]:
                LOGGER.debug(
                    f"self.dynamo_newest_dates[{column}]: {self.dynamo_newest_dates[column]}"
                )
                LOGGER.debug(
                    f"self.ha_newest_dates[{column}]: {self.ha_newest_dates[column]}"
                )
                LOGGER.debug(f"  column: {column}")
                LOGGER.debug(
                    f"  dynamo {self.dynamo_newest_dates[column]} is older than local {self.ha_newest_dates[column]}"
                )
                entities_missing.append(active_entity_id)
        return entities_missing
        # return False

    async def get_heating_profile(self, lambda_args: dict, thermostat_id: int):
        """Fetch heating profile from Optispark Backend.

        Upload all new and missing data to dynamo first.
        If there is no data in dynamo, upload const.HISTORY_DAYS worth of data.
        Records the when the heating profile expires and should be refreshed.
        """
        LOGGER.debug(f'Fetching heating profile')
        LOGGER.debug(f"Expire time: {self.expire_time}")
        count = 0
        await self.update_dynamo_dates(lambda_args)
        (
            self.dynamo_oldest_dates,
            self.dynamo_newest_dates,
        ) = await self.client.get_data_dates()
        await self.update_ha_dates()

        while missing_entities := self.entities_with_data_missing_from_dynamo():
            count += 1
            LOGGER.debug(f"Updating dynamo with NEW data: round ({count})")
            await self.upload_new_history(missing_entities)
        LOGGER.debug("Upload of new history complete\n")

        self.lambda_results = await self.client.async_get_profile(lambda_args)

        self.expire_time = self.lambda_results[const.LAMBDA_TIMESTAMP][-1]
        # The backend will currently only update upon a new day. FIX!
        self.expire_time = self.expire_time + timedelta(hours=1, minutes=30)
        self.manual_update = False

    async def call_lambda(self, lambda_args):
        """Fetch heating profile from AWS Lambda.

        Upload all new and missing data to dynamo first.
        If there is no data in dynamo, upload const.HISTORY_DAYS worth of data.
        Records the when the heating profile expires and should be refreshed.
        """
        count = 0
        await self.update_dynamo_dates(lambda_args)
        await self.update_ha_dates()
        while missing_entities := self.entities_with_data_missing_from_dynamo():
            count += 1
            LOGGER.debug(f"Updating dynamo with NEW data: round ({count})")
            await self.upload_new_history(missing_entities)
        LOGGER.debug("Upload of new history complete\n")

        self.lambda_results = await self.client.async_get_profile(lambda_args)

        self.expire_time = self.lambda_results[const.LAMBDA_TIMESTAMP][-1]
        # The backend will currently only update upon a new day. FIX!
        self.expire_time = self.expire_time + timedelta(hours=1, minutes=30)
        self.manual_update = False

    def get_closest_time(self, lambda_args):
        """Get the closest matching time to now from the lambda data set provided."""
        time_based_keys = [
            const.LAMBDA_BASE_DEMAND,
            const.LAMBDA_PRICE,
            const.LAMBDA_TEMP_CONTROLS,
            const.LAMBDA_OPTIMISED_DEMAND,
        ]
        non_time_based_keys = [
            const.LAMBDA_BASE_COST,
            const.LAMBDA_OPTIMISED_COST,
            const.LAMBDA_PROJECTED_PERCENT_SAVINGS,
        ]

        # Convert lists to {datetime: list_element}
        my_data = {}
        for key in time_based_keys:
            my_data[key] = {
                self.lambda_results[const.LAMBDA_TIMESTAMP][i]: self.lambda_results[
                    key
                ][i]
                for i in range(len(self.lambda_results[key]))
            }
        for key in non_time_based_keys:
            my_data[key] = self.lambda_results[key]

        # Get closet datetime that is in the past
        datetime_np = np.asarray(self.lambda_results[const.LAMBDA_TIMESTAMP])
        filtered = datetime_np[datetime_np < datetime.now(tz=timezone.utc)]
        closest_past_date = filtered.max()

        out = {}
        for key in time_based_keys:
            out[key] = my_data[key][closest_past_date]

        for key in non_time_based_keys:
            out[key] = my_data[key]

        if lambda_args[const.LAMBDA_OUTSIDE_RANGE]:
            # We're outside of the temp range so simply set the set point to whatever the user has
            # requested
            out[const.LAMBDA_TEMP_CONTROLS] = lambda_args[const.LAMBDA_SET_POINT]
            self.outside_range_flag = True
            LOGGER.debug(
                f"initial_internal_temp({lambda_args[const.LAMBDA_INITIAL_INTERNAL_TEMP]}) is outside of temp_range({lambda_args[const.LAMBDA_TEMP_RANGE]}) of the internal_temp({out[const.LAMBDA_TEMP_CONTROLS]}) - setting to set_point({lambda_args[const.LAMBDA_SET_POINT]})"
            )
        elif self.outside_range_flag:
            # We have just entered the temp_range! The optimisation can now be run
            LOGGER.debug("Temperature range reached")
            self.manual_update = True
            self.outside_range_flag = False
        return out
