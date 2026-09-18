from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(
    frozen=True,
    slots=True,
)
class OpexAccountMasterRecord:
    numero_cuenta: str
    categoria_gasto: str | None
    nombre_cuenta: str | None
    atributo_2: str | None


@dataclass(
    frozen=True,
    slots=True,
)
class OpexCebeMasterRecord:
    centro_beneficio: str
    desc_cebe: str | None
    macroservicio_cg: str | None
    tipo_servicio_cg: str | None
    region_cg: str | None
    sede_cg: str | None
    segmentacion: str | None


@dataclass(
    frozen=True,
    slots=True,
)
class OpexRecoverableMasterRecord:
    inicial: str
    sociedad: str | None
    compania: str | None
    pais: str | None


@dataclass(
    frozen=True,
    slots=True,
)
class OpexMasterSource:
    path: str
    sheet_name: str
    header_row: int
    physical_rows: int
    unique_rows: int
    duplicate_rows: int
    ignored_blank_key_rows: int = 0
    ignored_invalid_key_rows: int = 0
    conflict_keys: int = 0


@dataclass(
    frozen=True,
    slots=True,
)
class OpexMasterConflict:
    key: str
    locations: tuple[str, ...]
    records: tuple[Any, ...]


@dataclass(
    frozen=True,
    slots=True,
)
class OpexMasterDataSnapshot:
    accounts: Mapping[
        str,
        OpexAccountMasterRecord,
    ]

    cebes: Mapping[
        str,
        OpexCebeMasterRecord,
    ]

    recoverables: Mapping[
        str,
        OpexRecoverableMasterRecord,
    ]

    account_conflicts: Mapping[
        str,
        OpexMasterConflict,
    ]

    cebe_conflicts: Mapping[
        str,
        OpexMasterConflict,
    ]

    recoverable_conflicts: Mapping[
        str,
        OpexMasterConflict,
    ]

    account_source: OpexMasterSource
    cebe_source: OpexMasterSource
    recoverable_source: OpexMasterSource
