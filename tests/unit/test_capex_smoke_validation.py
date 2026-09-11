import pytest

from database.bootstrap.capex_smoke_validation import (
    CapexSmokeMetrics,
    CapexSmokeValidationError,
    validate_capex_smoke_metrics,
)


pytestmark = pytest.mark.unit


def make_metrics():
    return CapexSmokeMetrics(
        selected_rows=5,
        unique_row_ids=5,
        disabled_rows=0,
        min_version=1,
        max_version=1,
    )


def test_valid_smoke_metrics():
    validate_capex_smoke_metrics(
        make_metrics(),
        expected_rows=5,
    )


def test_wrong_row_count_is_rejected():
    metrics = make_metrics()

    metrics = CapexSmokeMetrics(
        selected_rows=4,
        unique_row_ids=4,
        disabled_rows=0,
        min_version=1,
        max_version=1,
    )

    with pytest.raises(
        CapexSmokeValidationError,
        match="Cantidad",
    ):
        validate_capex_smoke_metrics(
            metrics,
            expected_rows=5,
        )


def test_duplicate_ids_are_rejected():
    metrics = CapexSmokeMetrics(
        selected_rows=5,
        unique_row_ids=4,
        disabled_rows=0,
        min_version=1,
        max_version=1,
    )

    with pytest.raises(
        CapexSmokeValidationError,
        match="row_id",
    ):
        validate_capex_smoke_metrics(
            metrics,
            expected_rows=5,
        )


def test_wrong_initial_version_is_rejected():
    metrics = CapexSmokeMetrics(
        selected_rows=5,
        unique_row_ids=5,
        disabled_rows=0,
        min_version=1,
        max_version=2,
    )

    with pytest.raises(
        CapexSmokeValidationError,
        match="version",
    ):
        validate_capex_smoke_metrics(
            metrics,
            expected_rows=5,
        )
