
from app.clients.sharepoint_client import (
    SharePointClient,
)
from app.config.settings import (
    settings,
)
from app.config.sharepoint_summary_config import (
    CAPEX_SHAREPOINT_COLUMN_SPECS,
)
from app.models.sharepoint_summary_publish import (
    CapexSharePointSyncOutcome,
    CapexSharePointSyncPreparation,
)
from app.services.capex_sharepoint_summary_service import (
    CapexSharePointSummaryService,
)
from app.services.sharepoint_schema_service import (
    SharePointSchemaService,
)
from app.services.sharepoint_summary_publisher import (
    SharePointSummaryPublisher,
)


class CapexSharePointSyncError(
    RuntimeError
):
    pass


class CapexSharePointSyncService:
    def __init__(
        self,
        *,
        sharepoint_client=None,
        summary_service=None,
        publisher=None,
        list_name=None,
    ):
        self._sharepoint = (
            sharepoint_client
            if sharepoint_client
            is not None
            else SharePointClient()
        )

        self._summary = (
            summary_service
            if summary_service
            is not None
            else (
                CapexSharePointSummaryService()
            )
        )

        self._publisher = (
            publisher
            if publisher is not None
            else SharePointSummaryPublisher(
                self._sharepoint
            )
        )

        self._list_name = str(
            list_name
            if list_name is not None
            else (
                settings
                .SHAREPOINT_CAPEX_LIST_NAME
            )
        ).strip()

        if not self._list_name:
            raise ValueError(
                "list_name no puede "
                "estar vacio."
            )

    @property
    def list_name(
        self,
    ) -> str:
        return self._list_name

    def prepare(
        self,
    ) -> CapexSharePointSyncPreparation:
        schema = (
            SharePointSchemaService(
                self._sharepoint
            )
            .plan(
                list_name=(
                    self._list_name
                ),
                specs=(
                    CAPEX_SHAREPOINT_COLUMN_SPECS
                ),
            )
        )

        if not schema.is_complete:
            raise (
                CapexSharePointSyncError(
                    "Resumen_Capex no cumple "
                    "el esquema requerido."
                )
            )

        summary = (
            self._summary
            .build_summary()
        )

        if not summary.is_balanced:
            raise (
                CapexSharePointSyncError(
                    "El resumen CAPEX "
                    "no esta balanceado."
                )
            )

        desired = (
            self._summary
            .map_summary(
                summary
            )
        )

        current = (
            self._sharepoint
            .get_items(
                self._list_name
            )
        )

        plan = (
            self._summary
            .build_plan(
                desired_items=(
                    desired
                ),
                current_items=(
                    current
                ),
            )
        )

        return (
            CapexSharePointSyncPreparation(
                summary_result=(
                    summary
                ),
                desired_items=tuple(
                    desired
                ),
                current_items=tuple(
                    current
                ),
                plan=plan,
            )
        )

    def publish(
        self,
        preparation,
        *,
        source_batch_id=None,
        allow_large_delete=False,
    ) -> CapexSharePointSyncOutcome:
        result = (
            self._publisher
            .publish(
                list_name=(
                    self._list_name
                ),
                plan=(
                    preparation.plan
                ),
                source_batch_id=(
                    source_batch_id
                ),
                allow_large_delete=(
                    allow_large_delete
                ),
            )
        )

        current_after = (
            self._sharepoint
            .get_items(
                self._list_name
            )
        )

        verification = (
            self._summary
            .build_plan(
                desired_items=(
                    preparation
                    .desired_items
                ),
                current_items=(
                    current_after
                ),
            )
        )

        if (
            verification.create_count
            or
            verification.update_count
            or
            verification.delete_count
        ):
            raise (
                CapexSharePointSyncError(
                    "SharePoint respondio "
                    "a la publicacion, pero "
                    "la verificacion posterior "
                    "todavia detecta cambios: "
                    f"CREATE="
                    f"{verification.create_count}, "
                    f"UPDATE="
                    f"{verification.update_count}, "
                    f"DELETE="
                    f"{verification.delete_count}."
                )
            )

        if (
            verification
            .unchanged_count
            != len(
                preparation
                .desired_items
            )
        ):
            raise (
                CapexSharePointSyncError(
                    "La cantidad final de "
                    "items administrados "
                    "no coincide con el "
                    "resumen CAPEX."
                )
            )

        return (
            CapexSharePointSyncOutcome(
                preparation=(
                    preparation
                ),
                publish_result=result,
                verification_plan=(
                    verification
                ),
            )
        )
