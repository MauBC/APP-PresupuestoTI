
import pytest

from app.config.sharepoint_summary_config import (
    CAPEX_SHAREPOINT_COMPARE_FIELDS,
)
from app.models.sharepoint_summary_sync import (
    SharePointDesiredItem,
)
from app.services.sharepoint_summary_sync_planner import (
    SharePointSummarySyncPlanError,
    SharePointSummarySyncPlanner,
)


pytestmark = pytest.mark.unit


def planner():
    return (
        SharePointSummarySyncPlanner(
            compare_fields=(
                CAPEX_SHAREPOINT_COMPARE_FIELDS
            ),
            module="CAPEX",
        )
    )


def desired(
    *,
    key="key-001",
    total=100.0,
    name="Proyecto A",
):
    fields = {
        "Title":
            name,
        "SummaryKey":
            key,
        "Vicepresidencia":
            "TI",
        "Pais":
            "Peru",
        "Sociedad":
            "Ransa",
        "Responsable":
            "Ana",
        "GerenteAprobador":
            "Gerente",
        "VPAprobador":
            "VP",
        "NombreInversion":
            name,
        "TotalUSD":
            total,
        "RegistrosOrigen":
            2,
        "Modulo":
            "CAPEX",
    }

    return (
        SharePointDesiredItem(
            summary_key=key,
            fields=tuple(
                (
                    field,
                    fields[field],
                )
                for field
                in CAPEX_SHAREPOINT_COMPARE_FIELDS
            ),
        )
    )


def current(
    *,
    item_id="10",
    key="key-001",
    total=100.0,
    name="Proyecto A",
    module="CAPEX",
):
    return {
        "id":
            item_id,
        "eTag":
            '"etag-001"',
        "fields": {
            "Title":
                name,
            "SummaryKey":
                key,
            "Vicepresidencia":
                "TI",
            "Pais":
                "Peru",
            "Sociedad":
                "Ransa",
            "Responsable":
                "Ana",
            "GerenteAprobador":
                "Gerente",
            "VPAprobador":
                "VP",
            "NombreInversion":
                name,
            "TotalUSD":
                total,
            "RegistrosOrigen":
                2,
            "Modulo":
                module,
        },
    }


def test_empty_sharepoint_creates_all():
    plan = (
        planner()
        .build(
            desired_items=(
                desired(),
            ),
            current_items=(),
        )
    )

    assert plan.create_count == 1
    assert plan.update_count == 0
    assert plan.delete_count == 0
    assert plan.unchanged_count == 0


def test_identical_item_is_unchanged():
    plan = (
        planner()
        .build(
            desired_items=(
                desired(),
            ),
            current_items=(
                current(),
            ),
        )
    )

    assert plan.create_count == 0
    assert plan.update_count == 0
    assert plan.delete_count == 0
    assert plan.unchanged_count == 1
    assert plan.write_count == 0


def test_changed_total_is_update():
    plan = (
        planner()
        .build(
            desired_items=(
                desired(
                    total=125.50
                ),
            ),
            current_items=(
                current(
                    total=100.0
                ),
            ),
        )
    )

    assert plan.update_count == 1

    action = (
        plan.updates[0]
    )

    assert action.item_id == "10"

    assert (
        action.fields_dict()[
            "TotalUSD"
        ]
        == 125.50
    )


def test_obsolete_managed_item_is_delete():
    plan = (
        planner()
        .build(
            desired_items=(),
            current_items=(
                current(),
            ),
        )
    )

    assert plan.delete_count == 1
    assert (
        plan.deletes[0].item_id
        == "10"
    )


def test_item_without_summary_key_is_unmanaged():
    item = current()

    item["fields"][
        "SummaryKey"
    ] = None

    plan = (
        planner()
        .build(
            desired_items=(),
            current_items=(
                item,
            ),
        )
    )

    assert plan.delete_count == 0
    assert plan.unmanaged_count == 1


def test_wrong_module_is_unmanaged():
    plan = (
        planner()
        .build(
            desired_items=(),
            current_items=(
                current(
                    module="OPEX"
                ),
            ),
        )
    )

    assert plan.delete_count == 0
    assert plan.unmanaged_count == 1


def test_duplicate_current_key_blocks_sync():
    with pytest.raises(
        SharePointSummarySyncPlanError,
        match="duplicada",
    ):
        (
            planner()
            .build(
                desired_items=(
                    desired(),
                ),
                current_items=(
                    current(
                        item_id="1"
                    ),
                    current(
                        item_id="2"
                    ),
                ),
            )
        )


def test_decimal_representation_does_not_trigger_update():
    plan = (
        planner()
        .build(
            desired_items=(
                desired(
                    total=100.0
                ),
            ),
            current_items=(
                current(
                    total=100
                ),
            ),
        )
    )

    assert (
        plan.unchanged_count
        == 1
    )

    assert plan.update_count == 0
