from dataclasses import dataclass, field

from app.models.opex_master_data import (
    OpexAccountMasterRecord,
    OpexCebeMasterRecord,
)
from app.models.opex_smart_template import (
    OpexTemplateBudget,
)
from app.services.opex_template_distribution_service import (
    OpexTemplateResolvedDistribution,
)


@dataclass(
    slots=True,
)
class OpexSmartBudgetResolutionState:
    budget: OpexTemplateBudget
    account_selection: OpexAccountMasterRecord | None = None
    cebe_selections: dict[
        str,
        OpexCebeMasterRecord,
    ] = field(
        default_factory=dict
    )
    resolved_distribution: OpexTemplateResolvedDistribution | None = None


@dataclass(
    slots=True,
)
class OpexSmartWorkbookResolutionState:
    source_path: str
    budgets: dict[
        str,
        OpexSmartBudgetResolutionState,
    ] = field(
        default_factory=dict
    )
