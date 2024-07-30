from homeassistant.components.climate import HVACMode


class ThermostatInfo:
    _id: int
    _target_temp_high: float
    _target_temp_low: float
    _hvac_mode: HVACMode

    def __init__(
        self,
        id: int,
        target_temp_high: float = None,
        target_temp_low: float = None,
        hvac_mode: HVACMode = HVACMode.OFF
    ):
        self._id = id
        self._target_temp_high = target_temp_high if target_temp_high is not None else 20.0
        self._target_temp_low = target_temp_low if target_temp_low is not None else 20.0
        self._hvac_mode = hvac_mode

    @property
    def id(self) -> int:
        return self._id

    @property
    def target_temp_high(self) -> float:
        return self._target_temp_high

    @property
    def target_temp_low(self) -> float:
        return self._target_temp_low

    @property
    def hvac_mode(self) -> HVACMode:
        return self._hvac_mode
