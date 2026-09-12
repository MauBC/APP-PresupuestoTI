from dataclasses import dataclass
from decimal import Decimal

from app.models.opex_master_enrichment import (
    OpexMasterEnrichment,
)
from app.services.opex_template_distribution_service import (
    OpexTemplateDistributionStatus,
)


@dataclass(
    frozen=True,
    slots=True,
)
class OpexSmartEnrichmentIssue:
    sheet_name: str
    excel_row: int | None
    ceco: str | None
    code: str
    message: str


@dataclass(
    frozen=True,
    slots=True,
)
class OpexSmartEnrichmentDraft:
    sheet_name: str
    excel_row: int
    nombre_gasto: str
    proveedor: str
    moneda_facturacion: str
    numero_cuenta: str
    tipo: str
    monto_presupuesto: Decimal
    ceco: str
    percentage: Decimal | None
    input_amount: Decimal | None
    enrichment: OpexMasterEnrichment


@dataclass(
    frozen=True,
    slots=True,
)
class OpexSmartEnrichedRow:
    sheet_name: str
    excel_row: int
    nombre_gasto: str
    proveedor: str
    moneda_facturacion: str
    numero_cuenta: str
    tipo: str
    monto_presupuesto: Decimal
    ceco: str
    monto_ceco: Decimal
    enrichment: OpexMasterEnrichment


@dataclass(
    frozen=True,
    slots=True,
)
class OpexSmartBudgetAnalysis:
    sheet_name: str
    distribution_status: OpexTemplateDistributionStatus
    drafts: tuple[OpexSmartEnrichmentDraft, ...]
    issues: tuple[OpexSmartEnrichmentIssue, ...]


@dataclass(
    frozen=True,
    slots=True,
)
class OpexSmartWorkbookAnalysis:
    source_path: str
    budgets: tuple[
        OpexSmartBudgetAnalysis,
        ...
    ]
