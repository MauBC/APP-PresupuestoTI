from dataclasses import dataclass


@dataclass(
    frozen=True,
    slots=True,
)
class OpexSmartInsertionContext:
    origen: str
    presupuestador: str
    periodo: str = "2027 PB"
