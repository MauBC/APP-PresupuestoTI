
from datetime import (
    datetime,
    timezone,
)
from uuid import uuid4

from app.clients.graph_batch_client import (
    GraphBatchClient,
)
from app.models.graph_batch import (
    GraphBatchRequest,
)
from app.models.sharepoint_summary_publish import (
    SharePointSummaryPublishResult,
)


class SharePointSummaryPublishError(
    RuntimeError
):
    pass


class SharePointSummaryPublisher:
    def __init__(
        self,
        sharepoint_client,
        *,
        batch_client=None,
        max_delete_fraction=0.25,
        max_unconfirmed_deletes=10,
    ):
        self._sharepoint = (
            sharepoint_client
        )

        self._batch = (
            batch_client
            if batch_client is not None
            else GraphBatchClient(
                sharepoint_client
                .graph_client
            )
        )

        self._max_delete_fraction = float(
            max_delete_fraction
        )

        self._max_unconfirmed_deletes = int(
            max_unconfirmed_deletes
        )

    def publish(
        self,
        *,
        list_name,
        plan,
        source_batch_id=None,
        sync_run_id=None,
        updated_at=None,
        allow_large_delete=False,
    ) -> SharePointSummaryPublishResult:
        self._validate_delete_guard(
            plan,
            allow_large_delete=(
                allow_large_delete
            ),
        )

        sync_run_id_value = (
            str(
                sync_run_id
                or uuid4().hex
            )
            .strip()
        )

        if not sync_run_id_value:
            raise (
                SharePointSummaryPublishError(
                    "sync_run_id no puede "
                    "estar vacio."
                )
            )

        source_batch_value = (
            str(
                source_batch_id
            ).strip()
            if source_batch_id
            is not None
            else None
        )

        timestamp = (
            updated_at
            if updated_at is not None
            else datetime.now(
                timezone.utc
            )
        )

        if timestamp.tzinfo is None:
            raise (
                SharePointSummaryPublishError(
                    "updated_at debe incluir "
                    "zona horaria."
                )
            )

        timestamp = (
            timestamp
            .astimezone(
                timezone.utc
            )
        )

        if plan.write_count == 0:
            return (
                SharePointSummaryPublishResult(
                    sync_run_id=(
                        sync_run_id_value
                    ),
                    source_batch_id=(
                        source_batch_value
                    ),
                    updated_at=timestamp,
                    created_count=0,
                    updated_count=0,
                    deleted_count=0,
                )
            )

        site_id = (
            self._sharepoint
            .get_site_id()
        )

        list_id = (
            self._sharepoint
            .get_list_id(
                list_name
            )
        )

        metadata = {
            "SourceBatchId":
                source_batch_value,
            "SyncRunId":
                sync_run_id_value,
            "UpdatedAt":
                self._timestamp_text(
                    timestamp
                ),
        }

        upserts = []

        for index, action in enumerate(
            plan.creates,
            start=1,
        ):
            fields = (
                action.fields_dict()
            )

            fields.update(
                metadata
            )

            upserts.append(
                GraphBatchRequest(
                    request_id=(
                        f"C{index:06d}"
                    ),
                    method="POST",
                    url=(
                        f"/sites/{site_id}"
                        f"/lists/{list_id}"
                        "/items"
                    ),
                    headers=(
                        (
                            "Content-Type",
                            "application/json",
                        ),
                    ),
                    body={
                        "fields":
                            fields
                    },
                )
            )

        for index, action in enumerate(
            plan.updates,
            start=1,
        ):
            fields = (
                action.fields_dict()
            )

            fields.update(
                metadata
            )

            headers = [
                (
                    "Content-Type",
                    "application/json",
                ),
            ]

            if action.etag:
                headers.append(
                    (
                        "If-Match",
                        action.etag,
                    )
                )

            upserts.append(
                GraphBatchRequest(
                    request_id=(
                        f"U{index:06d}"
                    ),
                    method="PATCH",
                    url=(
                        f"/sites/{site_id}"
                        f"/lists/{list_id}"
                        f"/items/{action.item_id}"
                        "/fields"
                    ),
                    headers=tuple(
                        headers
                    ),
                    body=fields,
                )
            )

        upsert_result = (
            self._batch.execute(
                upserts
            )
        )

        self._raise_if_failed(
            "CREATE/UPDATE",
            upsert_result,
        )

        deletes = []

        for index, action in enumerate(
            plan.deletes,
            start=1,
        ):
            headers = []

            if action.etag:
                headers.append(
                    (
                        "If-Match",
                        action.etag,
                    )
                )

            deletes.append(
                GraphBatchRequest(
                    request_id=(
                        f"D{index:06d}"
                    ),
                    method="DELETE",
                    url=(
                        f"/sites/{site_id}"
                        f"/lists/{list_id}"
                        f"/items/{action.item_id}"
                    ),
                    headers=tuple(
                        headers
                    ),
                )
            )

        delete_result = (
            self._batch.execute(
                deletes
            )
        )

        self._raise_if_failed(
            "DELETE",
            delete_result,
        )

        return (
            SharePointSummaryPublishResult(
                sync_run_id=(
                    sync_run_id_value
                ),
                source_batch_id=(
                    source_batch_value
                ),
                updated_at=timestamp,
                created_count=(
                    plan.create_count
                ),
                updated_count=(
                    plan.update_count
                ),
                deleted_count=(
                    plan.delete_count
                ),
            )
        )

    def _validate_delete_guard(
        self,
        plan,
        *,
        allow_large_delete,
    ):
        if plan.delete_count == 0:
            return

        managed_current = (
            plan.current_item_count
            - plan.unmanaged_count
        )

        if (
            plan.desired_item_count == 0
            and managed_current > 0
            and not allow_large_delete
        ):
            raise (
                SharePointSummaryPublishError(
                    "Se bloqueo una "
                    "sincronizacion que "
                    "eliminaria todos los "
                    "items administrados."
                )
            )

        if managed_current <= 0:
            return

        fraction = (
            plan.delete_count
            / managed_current
        )

        if (
            plan.delete_count
            > self._max_unconfirmed_deletes
            and
            fraction
            > self._max_delete_fraction
            and
            not allow_large_delete
        ):
            raise (
                SharePointSummaryPublishError(
                    "Se bloqueo una eliminacion "
                    "masiva de SharePoint. "
                    f"Deletes={plan.delete_count}, "
                    f"administrados="
                    f"{managed_current}, "
                    f"proporcion="
                    f"{fraction:.2%}."
                )
            )

    @staticmethod
    def _raise_if_failed(
        phase,
        result,
    ):
        if result.is_success:
            return

        details = []

        for response in (
            result.failures[:5]
        ):
            body = str(
                response.body
                if response.body
                is not None
                else ""
            )

            if len(body) > 300:
                body = (
                    body[:300]
                    + "..."
                )

            details.append(
                f"{response.request_id}"
                f"=HTTP {response.status}"
                f" {body}"
            )

        raise (
            SharePointSummaryPublishError(
                f"Fallo fase {phase}. "
                f"Operaciones exitosas antes "
                f"del fallo: "
                f"{result.success_count}. "
                f"Fallos: "
                + " | ".join(
                    details
                )
            )
        )

    @staticmethod
    def _timestamp_text(
        value,
    ) -> str:
        return (
            value
            .astimezone(
                timezone.utc
            )
            .isoformat(
                timespec="seconds"
            )
            .replace(
                "+00:00",
                "Z",
            )
        )
