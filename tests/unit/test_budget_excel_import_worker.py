
import pytest

from app.ui.workers.budget_excel_import import (
    BudgetExcelImportThread,
)


pytestmark = pytest.mark.unit


def test_worker_stores_import_contract(
    tmp_path,
):
    thread = (
        BudgetExcelImportThread(
            module_config=object(),
            file_path=(
                tmp_path
                / "archivo.xlsx"
            ),
            actor="tester",
        )
    )

    assert (
        thread._actor
        == "tester"
    )

    assert (
        thread._file_path
        .endswith(
            "archivo.xlsx"
        )
    )
