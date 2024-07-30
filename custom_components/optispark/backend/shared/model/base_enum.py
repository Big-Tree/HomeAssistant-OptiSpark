from enum import Enum


class BaseEnum(Enum):
    def __str__(self) -> str:
        return "%s" % self.value


class FilterOperator(BaseEnum):
    OR = "or"
    AND = "and"