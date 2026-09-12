from dataclasses import dataclass
from decimal import Decimal


@dataclass(
    frozen=True,
    slots=True,
)
class OpexSmartImportCebeDecision:
    centro_beneficio: str
    tipo_servicio_cg: str


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
    decisions: tuple[
        OpexSmartImportDecision,
        ...,
    ]
