from custom_components.optispark.backend.shared.model.base_enum import BaseEnum


class WorkingMode(str, BaseEnum):
    HEATING = "Heating"
    COOLING = "Cooling"
    STOPPED = "Stopped"
    HEAT_AND_COOL = "HeatAndCool"

    @classmethod
    def from_string(cls, value: str):

        val = value.lower()
        if val == 'heating':
            return WorkingMode.HEATING
        if val == 'cooling':
            return WorkingMode.COOLING
        if val == "heatandcool":
            return WorkingMode.HEAT_AND_COOL
        else:
            return WorkingMode.STOPPED
