from typing import Optional

from custom_components.optispark.const import LOGGER
from custom_components.optispark.backend.shared.model.working_mode import WorkingMode
from custom_components.optispark.backend.thermostat.model.thermostat_control_status import ThermostatControlStatus


class ThermostatControlResponse:
    thermostat_id: int
    status: ThermostatControlStatus
    mode: WorkingMode
    heat_set_point: float | None
    cool_set_point: float | None

    def __init__(
        self,
        thermostat_id: int,
        status: ThermostatControlStatus,
        mode: WorkingMode,
        heat_set_point: Optional[float] = None,
        cool_set_point: Optional[float] = None
    ):
        self.thermostat_id = thermostat_id
        self.status = status
        self.mode = mode
        self.heat_set_point = heat_set_point
        self.cool_set_point = cool_set_point

    @classmethod
    def from_json(cls, json: dict):
        heat_set_point = None
        cool_set_point = None
        try:
            if json['heatSetPoint']:
                heat_set_point = json['heatSetPoint']
            if json['heatSetPoint']:
                heat_set_point = json['heatSetPoint']
            return cls(
                thermostat_id=json['thermostatId'],
                status=ThermostatControlStatus(json['status']),
                mode=WorkingMode(json['mode']),
                heat_set_point=heat_set_point,
                cool_set_point=cool_set_point,
            )

        except KeyError as e:
            LOGGER.error(f"Error: No key in JSON - {e}")
            return None
        except Exception as e:
            LOGGER.error(f"Error: {e}")
            return None
