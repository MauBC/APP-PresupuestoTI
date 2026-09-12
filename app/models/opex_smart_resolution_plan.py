from dataclasses import dataclass

from app.models.opex_master_data import (
    OpexAccountMasterRecord,
)
from app.models.opex_smart_resolution import (
    OpexAccountChoiceGroup,
    OpexCebeSelectionRequirement,
)
from app.services.opex_template_distribution_service import (
    OpexTemplateDistributionStatus,
    OpexTemplateResolvedDistribution,
)


@dataclass(
    frozen=True,
    slots=True,
)
class OpexSmartResolutionPlanIssue:
    code: str
    message: str
    key: str | None = None


@dataclass(
    frozen=True,
    slots=True,
)
class OpexSmartBudgetResolutionPlan:
    sheet_name: str
    account_groups: tuple[
        OpexAccountChoiceGroup,
        ...,
    ]
    account_selection: OpexAccountMasterRecord | None
    account_resolved: bool
    cebe_requirements: tuple[
        OpexCebeSelectionRequirement,
        ...,
    ]
    unresolved_cebes: tuple[str, ...]
    cebe_resolved: bool
    distribution_status: OpexTemplateDistributionStatus
    resolved_distribution: OpexTemplateResolvedDistribution | None
    distribution_resolved: bool
    issues: tuple[
        OpexSmartResolutionPlanIssue,
        ...,
    ]
    ready: bool
