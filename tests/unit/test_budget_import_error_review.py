from decimal import Decimal

import pandas as pd
import pytest
from PySide6.QtCore import Qt

from app.config.budget_modules import (
    CAPEX_MODULE_CONFIG,
    OPEX_MODULE_CONFIG,
)
from app.config.capex_schema import (
    CAPEX_INTERNAL_TO_RAW,
)
from app.models.budget_excel_import import (
    BudgetImportIssue,
    BudgetImportIssueSeverity,
)
from app.services.budget_excel_import_service import (
    BudgetExcelImportService,
)
from app.ui.models.budget_import_preview_model import (
    BudgetImportIssueFilterProxyModel,
    BudgetImportIssueModel,
)
from tests.unit.test_budget_excel_import_service import (
    make_capex_dataframe,
    make_opex_dataframe,
)


pytestmark = pytest.mark.unit


def test_opex_error_has_business_context_and_can_be_corrected(
    tmp_path,
):
    path = (
        tmp_path
        / "opex_error.xlsx"
    )

    dataframe = (
        make_opex_dataframe(
            bad_amount=True
        )
    )

    dataframe.loc[
        0,
        "presupuestador",
    ] = "ANA TEST"

    dataframe.loc[
        0,
        "pais",
    ] = "PER"

    dataframe.loc[
        0,
        "nombre_gasto",
    ] = "LICENCIAS TEST"

    dataframe.to_excel(
        path,
        index=False,
    )

    service = (
        BudgetExcelImportService(
            OPEX_MODULE_CONFIG
        )
    )

    invalid = service.prepare(
        path,
        actor="tester",
    )

    assert not invalid.is_valid

    issue = next(
        issue
        for issue
        in invalid.issues
        if issue.severity
        == BudgetImportIssueSeverity.ERROR
    )

    assert (
        issue.row_number
        == 2
    )

    assert (
        "Presupuestador: ANA TEST"
        in issue.context
    )

    assert (
        "Pais: PER"
        in issue.context
    )

    assert (
        "Gasto: LICENCIAS TEST"
        in issue.context
    )

    corrected = service.prepare(
        path,
        actor="tester",
        overrides={
            (
                2,
                "enero_usd",
            ):
                "10.50",
        },
    )

    assert corrected.is_valid

    assert (
        corrected.rows[0][
            "enero_usd"
        ]
        == Decimal("10.50")
    )


def test_capex_error_has_project_context_and_can_be_corrected(
    tmp_path,
):
    path = (
        tmp_path
        / "capex_error.xlsx"
    )

    dataframe = (
        make_capex_dataframe()
    )

    dataframe.loc[
        0,
        CAPEX_INTERNAL_TO_RAW[
            "presupuestador"
        ],
    ] = "MAURO TEST"

    dataframe.loc[
        0,
        CAPEX_INTERNAL_TO_RAW[
            "pais"
        ],
    ] = "PER"

    dataframe.loc[
        0,
        CAPEX_INTERNAL_TO_RAW[
            "nombre_inversion"
        ],
    ] = "PROYECTO TEST"

    dataframe.loc[
        0,
        CAPEX_INTERNAL_TO_RAW[
            "anio"
        ],
    ] = 2026

    with pd.ExcelWriter(
        path,
        engine="openpyxl",
    ) as writer:
        dataframe.to_excel(
            writer,
            sheet_name="PB 2027",
            index=False,
        )

    service = (
        BudgetExcelImportService(
            CAPEX_MODULE_CONFIG
        )
    )

    invalid = service.prepare(
        path,
        actor="tester",
        expected_year=2027,
    )

    assert not invalid.is_valid

    issue = next(
        issue
        for issue
        in invalid.issues
        if issue.code
        == "YEAR_MISMATCH"
    )

    assert (
        "Presupuestador: MAURO TEST"
        in issue.context
    )

    assert (
        "Pais: PER"
        in issue.context
    )

    assert (
        "Proyecto: PROYECTO TEST"
        in issue.context
    )

    corrected = service.prepare(
        path,
        actor="tester",
        expected_year=2027,
        overrides={
            (
                2,
                "anio",
            ):
                2027,
        },
    )

    assert corrected.is_valid

    assert (
        corrected.rows[0][
            "anio"
        ]
        == 2027
    )


def test_issue_model_exposes_business_context():
    issue = BudgetImportIssue(
        row_number=10,
        column="enero_usd",
        code="INVALID_VALUE",
        message="Valor invalido",
        severity=(
            BudgetImportIssueSeverity.ERROR
        ),
        raw_value="ABC",
        context=(
            "Presupuestador: ANA | "
            "Pais: PER | "
            "Gasto: LICENCIAS"
        ),
    )

    model = BudgetImportIssueModel(
        issues=(
            issue,
        )
    )

    assert (
        model.headerData(
            1,
            Qt.Orientation.Horizontal,
        )
        == "CONTEXTO"
    )

    assert (
        model.issue_at(
            0
        )
        is issue
    )

    assert (
        "Presupuestador"
        in model.data(
            model.index(
                0,
                1,
            ),
            Qt.ItemDataRole.DisplayRole,
        )
    )


def test_issue_proxy_filters_severity_and_context():
    issues = (
        BudgetImportIssue(
            row_number=2,
            column="enero_usd",
            code="INVALID_VALUE",
            message="Error",
            severity=(
                BudgetImportIssueSeverity.ERROR
            ),
            context=(
                "Proyecto: SERVIDORES"
            ),
        ),
        BudgetImportIssue(
            row_number=3,
            column="anio_usd",
            code="TOTAL_CALCULATED",
            message="Warning",
            severity=(
                BudgetImportIssueSeverity.WARNING
            ),
            context=(
                "Proyecto: RED"
            ),
        ),
    )

    model = BudgetImportIssueModel(
        issues=issues
    )

    proxy = (
        BudgetImportIssueFilterProxyModel()
    )

    proxy.setSourceModel(
        model
    )

    proxy.set_severity(
        "ERROR"
    )

    assert (
        proxy.rowCount()
        == 1
    )

    proxy.set_severity(
        None
    )

    proxy.set_search_text(
        "red"
    )

    assert (
        proxy.rowCount()
        == 1
    )
