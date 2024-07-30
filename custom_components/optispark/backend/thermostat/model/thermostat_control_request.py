from typing import Optional

from custom_components.optispark.backend.shared.model.working_mode import WorkingMode


class ThermostatControlRequest:
    mode: WorkingMode
    heat_set_point: float | None
    cool_set_point: float | None

    def __init__(
        self,
        mode: WorkingMode,
        heat_set_point: Optional[float] = None,
        cool_set_point: Optional[float] = None
    ):
        self.mode = mode
        self.heat_set_point = heat_set_point
        self.cool_set_point = cool_set_point

    def to_dict(self) -> dict:
        result = {'mode': self.mode}

        if self.mode == WorkingMode.HEAT_AND_COOL and self.heat_set_point and self.cool_set_point:
            result['heatSetPoint'] = self.heat_set_point
            result['coolSetPoint'] = self.cool_set_point

        if self.mode == WorkingMode.COOLING and self.heat_set_point:
            result['coolSetPoint'] = self.cool_set_point

        if self.mode == WorkingMode.HEATING and self.heat_set_point:
            result['heatSetPoint'] = self.heat_set_point

        return result

    def __str__(self):
        return f'mode:{self.mode} - heat point: {self.heat_set_point} - cool point: {self.cool_set_point}'

