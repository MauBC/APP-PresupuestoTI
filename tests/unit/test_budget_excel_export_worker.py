from types import SimpleNamespace

import pytest

from app.ui.workers.budget_excel_export import (
    BudgetExcelExportThread,
)


pytestmark = pytest.mark.unit


def test_worker_exports_result():
    expected = SimpleNamespace(
        path="archivo.xlsx",
        row_count=10,
    )

    class FakeService:
        def __init__(
            self,
        ):
            self.destination = None

        def export(
            self,
            destination,
        ):
            self.destination = (
                destination
            )

            return expected

    service = FakeService()

    worker = (
        BudgetExcelExportThread(
            module_config=object(),
            destination="salida.xlsx",
            service_factory=(
                lambda config:
                    service
            ),
        )
    )

    exported = []
    failed = []

    worker.exported.connect(
        exported.append
    )

    worker.failed.connect(
        failed.append
    )

    worker.run()

    assert exported == [
        expected
    ]

    assert failed == []

    assert (
        service.destination
        == "salida.xlsx"
    )


def test_worker_emits_failure():
    class FakeService:
        @staticmethod
        def export(
            destination,
        ):
            raise RuntimeError(
                "synthetic export failure"
            )

    worker = (
        BudgetExcelExportThread(
            module_config=object(),
            destination="salida.xlsx",
            service_factory=(
                lambda config:
                    FakeService()
            ),
        )
    )

    exported = []
    failed = []

    worker.exported.connect(
        exported.append
    )

    worker.failed.connect(
        failed.append
    )

    worker.run()

    assert exported == []
    assert len(failed) == 1

    assert (
        "synthetic export failure"
        in failed[0]
    )
