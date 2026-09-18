from dataclasses import dataclass

from app.models.opex_master_data import (
    OpexCebeMasterRecord,
)


@dataclass(
    frozen=True,
    slots=True,
)
class OpexAccountChoiceGroup:
    categoria_gasto: str
    nombre_cuenta: str
    atributos_2: tuple[str, ...]


@dataclass(
    frozen=True,
    slots=True,
)
class OpexCebeSelectionRequirement:
    centro_beneficio: str
    cecos: tuple[str, ...]
    excel_rows: tuple[int, ...]
    options: tuple[
        OpexCebeMasterRecord,
        ...,
    ]
