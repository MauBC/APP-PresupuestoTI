from dataclasses import dataclass
from decimal import Decimal


@dataclass(
    frozen=True,
    slots=True,
)
class OpexSmartImportAccountChoice:
    categoria_gasto: str
    nombre_cuenta: str
    atributo_2: str


@dataclass(
    frozen=True,
    slots=True,
)
class OpexSmartImportCebeOption:
    centro_beneficio: str
    desc_cebe: str
    macroservicio_cg: str
    tipo_servicio_cg: str
    region_cg: str
    sede_cg: str
    segmentacion: str


@dataclass(
    frozen=True,
    slots=True,
)
class OpexSmartImportCebeChoice:
    centro_beneficio: str
    options: tuple[
        OpexSmartImportCebeOption,
        ...,
    ]


@dataclass(
    frozen=True,
    slots=True,
)
class OpexSmartImportSheetReview:
    sheet_name: str
    account_options: tuple[
        OpexSmartImportAccountChoice,
        ...,
    ]
    distribution_modes: tuple[
        str,
        ...,
    ]
    cebe_choices: tuple[
        OpexSmartImportCebeChoice,
        ...,
    ]


@dataclass(
    frozen=True,
    slots=True,
)
class OpexSmartImportSheetOverride:
    sheet_name: str
    account: (
        OpexSmartImportAccountChoice
        | None
    ) = None
    distribution_mode: (
        str
        | None
    ) = None
    cebe_selections: tuple[
        OpexSmartImportCebeOption,
        ...,
    ] = ()


@dataclass(
    frozen=True,
    slots=True,
)
class OpexSmartImportCebeDecision:
    centro_beneficio: str
    tipo_servicio_cg: str
    selected_option: OpexSmartImportCebeOption | None = None


@dataclass(
    frozen=True,
    slots=True,
)
class OpexSmartImportDecision:
    sheet_name: str
    account_name: str
    atributo_2: str
    distribution_mode: str
    cebe_decisions: tuple[
        OpexSmartImportCebeDecision,
        ...,
    ]
    categoria_gasto: str | None = None


@dataclass(
    frozen=True,
    slots=True,
)
class OpexSmartImportPreparation:
    rows: tuple[dict, ...]
    source_name: str
    budget_count: int
    auto_cebe_count: int
    total_usd: Decimal
    country_counts: tuple[
        tuple[str, int],
        ...,
    ]
    invoice_currency_counts: tuple[
        tuple[str, int],
        ...,
    ]
    review_options: tuple[
        OpexSmartImportSheetReview,
        ...,
    ]
    decisions: tuple[
        OpexSmartImportDecision,
        ...,
    ]
