import pytest

from database.bootstrap.capex_full_load_validation import (
    CapexFullLoadMetrics,
    CapexFullLoadValidationError,
    validate_capex_full_load_metrics,
)


pytestmark = pytest.mark.unit


def make_metrics():
    return CapexFullLoadMetrics(
        total_rows=173,
        unique_row_ids=173,
        disabled_rows=0,
        min_version=1,
        max_version=1,
        years=(
            2027,
        ),
    )


def test_valid_full_load_metrics():
    validate_capex_full_load_metrics(
        make_metrics(),
        expected_rows=173,
        expected_year=2027,
    )


def test_simulation_allows_other_year():
    metrics = CapexFullLoadMetrics(
        total_rows=173,
        unique_row_ids=173,
        disabled_rows=0,
        min_version=1,
        max_version=1,
        years=(
            2026,
        ),
    )

    validate_capex_full_load_metrics(
        metrics,
        expected_rows=173,
        expected_year=None,
    )


def test_wrong_total_rows_is_rejected():
    metrics = CapexFullLoadMetrics(
        total_rows=172,
        unique_row_ids=172,
        disabled_rows=0,
        min_version=1,
        max_version=1,
        years=(
            2027,
        ),
    )

    with pytest.raises(
        CapexFullLoadValidationError,
        match="Cantidad total",
    ):
        validate_capex_full_load_metrics(
            metrics,
            expected_rows=173,
            expected_year=2027,
        )


def test_duplicate_row_ids_are_rejected():
    metrics = CapexFullLoadMetrics(
        total_rows=173,
        unique_row_ids=172,
        disabled_rows=0,
        min_version=1,
        max_version=1,
        years=(
            2027,
        ),
    )

    with pytest.raises(
        CapexFullLoadValidationError,
        match="row_id",
    ):
        validate_capex_full_load_metrics(
            metrics,
            expected_rows=173,
            expected_year=2027,
        )


def test_wrong_version_is_rejected():
    metrics = CapexFullLoadMetrics(
        total_rows=173,
        unique_row_ids=173,
        disabled_rows=0,
        min_version=1,
        max_version=2,
        years=(
            2027,
        ),
    )

    with pytest.raises(
        CapexFullLoadValidationError,
        match="version",
    ):
        validate_capex_full_load_metrics(
            metrics,
            expected_rows=173,
            expected_year=2027,
        )


def test_wrong_year_is_rejected():
    metrics = CapexFullLoadMetrics(
        total_rows=173,
        unique_row_ids=173,
        disabled_rows=0,
        min_version=1,
        max_version=1,
        years=(
            2026,
        ),
    )

    with pytest.raises(
        CapexFullLoadValidationError,
        match="anios",
    ):
        validate_capex_full_load_metrics(
            metrics,
            expected_rows=173,
            expected_year=2027,
        )
