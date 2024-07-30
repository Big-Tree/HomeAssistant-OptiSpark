from custom_components.optispark.backend.shared.model.base_enum import BaseEnum


class ThermostatControlStatus(str, BaseEnum):
    SCHEDULE = "schedule"
    MANUAL = "manual"
    BOOST = "boost"