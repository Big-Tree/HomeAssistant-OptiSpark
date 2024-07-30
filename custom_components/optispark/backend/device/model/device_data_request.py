from custom_components.optispark.backend.shared.model.working_mode import WorkingMode
from typing import Optional


class DeviceDataRequest:
    internal_temp: float
    humidity: Optional[float]
    power: Optional[float]
    mode: WorkingMode
    heat_set_point: Optional[float]
    cool_set_point: Optional[float]

    def __init__(
            self,
            internal_temp: float,
            humidity: Optional[float],
            power: Optional[float],
            mode: WorkingMode,
            heat_set_point: Optional[float],
            cool_set_point: Optional[float],
    ):
        self.internal_temp = internal_temp
        self.humidity = humidity
        self.power = power
        self.mode = mode
        self.heat_set_point = heat_set_point
        self.cool_set_point = cool_set_point

    def payload(self) -> dict:
        return {
            "internalTemp": self.internal_temp,
            "humidity": self.humidity,
            "power": self.power,
            "mode": self.mode,
            "heatSetPoint": self.heat_set_point,
            "coolSetPoint": self.cool_set_point
        }
