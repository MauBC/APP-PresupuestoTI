
from decimal import Decimal

import pytest

from app.config.budget_summary_config import (
    CAPEX_POWERAPPS_SUMMARY,
)
from app.services.budget_summary_service import (
    BudgetSummaryIntegrityError,
    BudgetSummaryService,
)


pytestmark = pytest.mark.unit


class FakeRepository:
    def __init__(
        self,
        rows,
    ):
        self.rows = tuple(
            rows
        )

    def get_summary_rows(
        self,
        definition,
    ):
        return self.rows


def make_row(
    *,
    project,
    total,
    count,
    source_count,
    source_total,
):
    return {
        "vicepresidencia":
            "TI",
        "pais":
            "PER",
        "sociedad":
            "RANSA PERU",
        "responsable":
            "ANA",
        "gerente_aprobador":
            "GERENTE",
        "vp_aprobador":
            "VP",
        "nombre_inversion":
            project,
        "registros_origen":
            count,
        "total_usd":
            Decimal(total),
        "_source_row_count":
            source_count,
        "_source_total_usd":
            Decimal(
                source_total
            ),
    }


def test_summary_is_balanced():
    repository = (
        FakeRepository(
            (
                make_row(
                    project="A",
                    total="65000",
                    count=3,
                    source_count=5,
                    source_total="80000",
                ),
                make_row(
                    project="B",
                    total="15000",
                    count=2,
                    source_count=5,
                    source_total="80000",
                ),
            )
        )
    )

    result = (
        BudgetSummaryService(
            repository
        )
        .build(
            CAPEX_POWERAPPS_SUMMARY
        )
    )

    assert result.is_balanced

    assert (
        result.source_row_count
        == 5
    )

    assert (
        result.grouped_row_count
        == 2
    )

    assert (
        result.summarized_row_count
        == 5
    )

    assert (
        result.source_total_usd
        == Decimal("80000")
    )

    assert (
        result.summary_total_usd
        == Decimal("80000")
    )


def test_summary_key_is_deterministic():
    service = (
        BudgetSummaryService(
            FakeRepository(())
        )
    )

    dimensions = (
        (
            "pais",
            " PER ",
        ),
        (
            "nombre_inversion",
            "Proyecto A",
        ),
    )

    first = (
        service.build_summary_key(
            CAPEX_POWERAPPS_SUMMARY,
            dimensions,
        )
    )

    second = (
        service.build_summary_key(
            CAPEX_POWERAPPS_SUMMARY,
            dimensions,
        )
    )

    assert first == second

    assert len(first) == 64


def test_summary_key_changes_when_dimension_changes():
    service = (
        BudgetSummaryService(
            FakeRepository(())
        )
    )

    first = (
        service.build_summary_key(
            CAPEX_POWERAPPS_SUMMARY,
            (
                (
                    "pais",
                    "PER",
                ),
            ),
        )
    )

    second = (
        service.build_summary_key(
            CAPEX_POWERAPPS_SUMMARY,
            (
                (
                    "pais",
                    "CHL",
                ),
            ),
        )
    )

    assert first != second


def test_amount_mismatch_blocks_summary():
    repository = (
        FakeRepository(
            (
                make_row(
                    project="A",
                    total="65000",
                    count=3,
                    source_count=3,
                    source_total="70000",
                ),
            )
        )
    )

    with pytest.raises(
        BudgetSummaryIntegrityError,
        match="Total USD|total USD",
    ):
        (
            BudgetSummaryService(
                repository
            )
            .build(
                CAPEX_POWERAPPS_SUMMARY
            )
        )


def test_row_count_mismatch_blocks_summary():
    repository = (
        FakeRepository(
            (
                make_row(
                    project="A",
                    total="65000",
                    count=2,
                    source_count=3,
                    source_total="65000",
                ),
            )
        )
    )

    with pytest.raises(
        BudgetSummaryIntegrityError,
        match="registros",
    ):
        (
            BudgetSummaryService(
                repository
            )
            .build(
                CAPEX_POWERAPPS_SUMMARY
            )
        )


def test_empty_source_is_valid():
    result = (
        BudgetSummaryService(
            FakeRepository(())
        )
        .build(
            CAPEX_POWERAPPS_SUMMARY
        )
    )

    assert result.is_balanced
    assert result.source_row_count == 0
    assert result.grouped_row_count == 0
    assert (
        result.source_total_usd
        == Decimal("0")
    )
