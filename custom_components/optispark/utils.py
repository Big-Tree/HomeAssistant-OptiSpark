from homeassistant.components.climate import HVACMode

from custom_components.optispark.domain.thermostat.thermostat_info import ThermostatInfo
from custom_components.optispark.backend.shared.model.working_mode import WorkingMode
from custom_components.optispark.backend.thermostat.model.thermostat_control_response import ThermostatControlResponse


def to_thermostat_info(control: ThermostatControlResponse) -> ThermostatInfo:
    return ThermostatInfo(
        id=control.thermostat_id,
        target_temp_high=control.heat_set_point,
        target_temp_low=control.cool_set_point,
        hvac_mode=to_hvac_mode(control.mode)
    )


def to_hvac_mode(mode: WorkingMode) -> HVACMode:
    if mode == WorkingMode.HEATING:
        return HVACMode.HEAT
    if mode == WorkingMode.COOLING:
        return HVACMode.COOL
    if mode == WorkingMode.HEAT_AND_COOL:
        return HVACMode.AUTO

    return HVACMode.OFF
