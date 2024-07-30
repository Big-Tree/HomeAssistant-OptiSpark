from datetime import datetime

from custom_components.optispark.backend.shared.model.working_mode import WorkingMode


class ThermostatPrediction:
    date: datetime
    mode: WorkingMode
    set_point: float
    external_temperature: float

    def __init__(self, date: datetime, mode: WorkingMode, set_point: float,  external_temperature: float):
        self.date = date
        self.mode = mode
        self.set_point = set_point
        self.external_temperature = external_temperature

    @classmethod
    def from_json(cls, json: dict):
        datetime_obj = datetime.strptime(json['date'], "%Y-%m-%dT%H:%M:%S.%fZ")
        mode = WorkingMode.from_string(json['mode'])
        return cls(
            date=datetime_obj,
            mode=mode,
            set_point=json['setPoint'],
            external_temperature=json['externalTemperature']
        )
