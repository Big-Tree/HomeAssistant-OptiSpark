from dataclasses import dataclass


@dataclass(frozen=True)
class ControlInfo:
    set_point: float
    mode: str

    def __str__(self):
        return f"{self.set_point}, {self.mode}"
    