from decimal import Decimal

import pytest

from PySide6.QtCore import Qt

from app.models.budget_excel_import import (
    BudgetImportIssue,
    BudgetImportIssueSeverity,
)
from app.services.capex_validator import (
    clean_and_validate_capex_row,
)
from app.ui.models.budget_import_preview_model import (
    BudgetImportIssueModel,
)
from tests.unit.test_capex_validator import (
    make_row,
)


pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    (
        "raw_total",
        "issue_column",
        "expected",
    ),
    (
        (
            "TOTAL ML",
            "anio_ml",
            Decimal(
                "300.000000000"
            ),
        ),
        (
            "TOTAL USD",
            "anio_usd",
            Decimal(
                "100.000000000"
            ),
        ),
    ),
)
def test_total_mismatch_exposes_expected_sum(
    raw_total,
    issue_column,
    expected,
):
    row = make_row()

    row[
        raw_total
    ] = Decimal(
        "999.00"
    )

    result = (
        clean_and_validate_capex_row(
            row,
            row_number=9,
        )
    )

    issue = next(
        issue
        for issue
        in result.errors
        if (
            issue.code
            == "TOTAL_MISMATCH"
            and
            issue.column
            == issue_column
        )
    )

    assert (
        issue.expected_value
        == expected
    )


def test_rounding_warning_exposes_expected_total():
    row = make_row()

    row[
        "TOTAL USD"
    ] = "100.005"

    result = (
        clean_and_validate_capex_row(
            row,
            row_number=9,
        )
    )

    issue = next(
        issue
        for issue
        in result.warnings
        if issue.code
        == "TOTAL_ROUNDING_DIFFERENCE"
    )

    assert (
        issue.expected_value
        == Decimal(
            "100.000000000"
        )
    )


def test_year_mismatch_exposes_expected_year():
    row = make_row()

    row["Año"] = 2026

    result = (
        clean_and_validate_capex_row(
            row,
            row_number=9,
            expected_year=2027,
        )
    )

    issue = next(
        issue
        for issue
        in result.errors
        if issue.code
        == "YEAR_MISMATCH"
    )

    assert (
        issue.expected_value
        == 2027
    )


def test_issue_model_displays_expected_value():
    issue = BudgetImportIssue(
        row_number=9,
        column="anio_usd",
        code="TOTAL_MISMATCH",
        message="Total invalido",
        severity=(
            BudgetImportIssueSeverity.ERROR
        ),
        raw_value=(
            Decimal("999.00")
        ),
        context=(
            "Proyecto: TEST"
        ),
        expected_value=(
            Decimal("100.00")
        ),
    )

    model = (
        BudgetImportIssueModel(
            issues=(
                issue,
            )
        )
    )

    expected_column = next(
        index
        for index, (
            attribute,
            _,
        )
        in enumerate(
            model.COLUMNS
        )
        if attribute
        == "expected_value"
    )

    assert (
        model.headerData(
            expected_column,
            Qt.Orientation.Horizontal,
        )
        == "ESPERADO"
    )

    assert (
        model.data(
            model.index(
                0,
                expected_column,
            ),
            Qt.ItemDataRole.DisplayRole,
        )
        == "100.00"
    )
