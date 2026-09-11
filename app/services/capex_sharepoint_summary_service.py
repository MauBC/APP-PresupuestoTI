
from app.config.budget_modules import (
    CAPEX_MODULE_CONFIG,
)
from app.config.budget_summary_config import (
    CAPEX_POWERAPPS_SUMMARY,
)
from app.config.sharepoint_summary_config import (
    CAPEX_SHAREPOINT_BUSINESS_FIELDS,
    CAPEX_SHAREPOINT_COMPARE_FIELDS,
)
from app.repositories.budget_summary_repository import (
    BudgetSummaryRepository,
)
from app.services.bigquery_service import (
    BigQueryService,
)
from app.services.budget_summary_service import (
    BudgetSummaryService,
)
from app.services.sharepoint_summary_mapper import (
    SharePointSummaryMapper,
)
from app.services.sharepoint_summary_sync_planner import (
    SharePointSummarySyncPlanner,
)


class CapexSharePointSummaryService:
    def __init__(
        self,
        *,
        bigquery_service=None,
    ):
        self._bigquery = (
            bigquery_service
            if bigquery_service is not None
            else BigQueryService()
        )

    def build_summary(
        self,
    ):
        repository = (
            BudgetSummaryRepository(
                self._bigquery,
                module_config=(
                    CAPEX_MODULE_CONFIG
                ),
            )
        )

        return (
            BudgetSummaryService(
                repository
            )
            .build(
                CAPEX_POWERAPPS_SUMMARY
            )
        )

    @staticmethod
    def map_summary(
        summary_result,
    ):
        mapper = (
            SharePointSummaryMapper(
                field_mapping=(
                    CAPEX_SHAREPOINT_BUSINESS_FIELDS
                ),
                compare_fields=(
                    CAPEX_SHAREPOINT_COMPARE_FIELDS
                ),
                title_source=(
                    "nombre_inversion"
                ),
                module="CAPEX",
            )
        )

        return (
            mapper.map_result(
                summary_result
            )
        )

    @staticmethod
    def build_plan(
        *,
        desired_items,
        current_items,
    ):
        planner = (
            SharePointSummarySyncPlanner(
                compare_fields=(
                    CAPEX_SHAREPOINT_COMPARE_FIELDS
                ),
                module="CAPEX",
            )
        )

        return planner.build(
            desired_items=(
                desired_items
            ),
            current_items=(
                current_items
            ),
        )
