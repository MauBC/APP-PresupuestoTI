
from app.models.graph_batch import (
    GraphBatchExecutionResult,
    GraphBatchResponse,
)
from app.models.sharepoint_summary_sync import (
    SharePointCreateAction,
    SharePointDeleteAction,
    SharePointSummarySyncPlan,
    SharePointUpdateAction,
)
from app.services.sharepoint_summary_publisher import (
    SharePointSummaryPublishError,
    SharePointSummaryPublisher,
)

import pytest


pytestmark = pytest.mark.unit


class FakeSharePoint:
    graph_client = object()

    def get_site_id(
        self,
    ):
        return "site"

    def get_list_id(
        self,
        list_name,
    ):
        return "list"


class FakeBatch:
    def __init__(self):
        self.calls = []

    def execute(
        self,
        requests,
    ):
        requests = tuple(
            requests
        )

        self.calls.append(
            requests
        )

        return (
            GraphBatchExecutionResult(
                responses=tuple(
                    GraphBatchResponse(
                        request_id=(
                            request
                            .request_id
                        ),
                        status=(
                            204
                            if (
                                request.method
                                == "DELETE"
                            )
                            else 201
                        ),
                    )
                    for request
                    in requests
                ),
            )
        )


def test_publisher_creates_with_metadata():
    batch = FakeBatch()

    plan = (
        SharePointSummarySyncPlan(
            creates=(
                SharePointCreateAction(
                    summary_key="key",
                    fields=(
                        (
                            "Title",
                            "Proyecto",
                        ),
                        (
                            "SummaryKey",
                            "key",
                        ),
                        (
                            "Modulo",
                            "CAPEX",
                        ),
                    ),
                ),
            ),
            updates=(),
            deletes=(),
            unchanged_keys=(),
            unmanaged_item_ids=(),
            current_item_count=0,
            desired_item_count=1,
        )
    )

    result = (
        SharePointSummaryPublisher(
            FakeSharePoint(),
            batch_client=batch,
        )
        .publish(
            list_name="Resumen_Capex",
            plan=plan,
            source_batch_id=(
                "batch-001"
            ),
            sync_run_id=(
                "sync-001"
            ),
        )
    )

    assert result.created_count == 1
    assert result.write_count == 1

    request = batch.calls[0][0]

    fields = request.body[
        "fields"
    ]

    assert (
        fields["SourceBatchId"]
        == "batch-001"
    )

    assert (
        fields["SyncRunId"]
        == "sync-001"
    )

    assert "UpdatedAt" not in fields


def test_updates_are_executed_before_deletes():
    batch = FakeBatch()

    plan = (
        SharePointSummarySyncPlan(
            creates=(),
            updates=(
                SharePointUpdateAction(
                    item_id="10",
                    summary_key="key-new",
                    fields=(
                        (
                            "Title",
                            "Proyecto",
                        ),
                        (
                            "SummaryKey",
                            "key-new",
                        ),
                        (
                            "Modulo",
                            "CAPEX",
                        ),
                    ),
                    etag='"etag"',
                ),
            ),
            deletes=(
                SharePointDeleteAction(
                    item_id="11",
                    summary_key="key-old",
                    etag='"etag-old"',
                ),
            ),
            unchanged_keys=(),
            unmanaged_item_ids=(),
            current_item_count=2,
            desired_item_count=1,
        )
    )

    result = (
        SharePointSummaryPublisher(
            FakeSharePoint(),
            batch_client=batch,
        )
        .publish(
            list_name="Resumen_Capex",
            plan=plan,
        )
    )

    assert result.updated_count == 1
    assert result.deleted_count == 1

    assert len(batch.calls) == 2

    assert (
        batch.calls[0][0].method
        == "PATCH"
    )

    assert (
        batch.calls[1][0].method
        == "DELETE"
    )


def test_mass_delete_is_blocked():
    deletes = tuple(
        SharePointDeleteAction(
            item_id=str(index),
            summary_key=(
                f"key-{index}"
            ),
        )
        for index
        in range(30)
    )

    plan = (
        SharePointSummarySyncPlan(
            creates=(),
            updates=(),
            deletes=deletes,
            unchanged_keys=tuple(
                f"keep-{index}"
                for index
                in range(70)
            ),
            unmanaged_item_ids=(),
            current_item_count=100,
            desired_item_count=70,
        )
    )

    with pytest.raises(
        SharePointSummaryPublishError,
        match="masiva",
    ):
        (
            SharePointSummaryPublisher(
                FakeSharePoint(),
                batch_client=FakeBatch(),
            )
            .publish(
                list_name=(
                    "Resumen_Capex"
                ),
                plan=plan,
            )
        )


def test_no_changes_makes_no_batch_call():
    batch = FakeBatch()

    plan = (
        SharePointSummarySyncPlan(
            creates=(),
            updates=(),
            deletes=(),
            unchanged_keys=(
                "key",
            ),
            unmanaged_item_ids=(),
            current_item_count=1,
            desired_item_count=1,
        )
    )

    result = (
        SharePointSummaryPublisher(
            FakeSharePoint(),
            batch_client=batch,
        )
        .publish(
            list_name="Resumen_Capex",
            plan=plan,
        )
    )

    assert result.write_count == 0
    assert batch.calls == []
