from types import SimpleNamespace

import pytest

from app.services.opex_fx_loader import (
    OpexFxLoadError,
    OpexFxLoader,
)
from app.services.opex_master_data_loader import (
    OpexMasterDataError,
    OpexMasterDataLoader,
)
from app.services.opex_smart_template_loader import (
    OpexSmartTemplateError,
    OpexSmartTemplateLoader,
)
from app.ui.dialogs.opex_smart_import_dialog import (
    OpexSmartImportDialog,
)
from app.ui.workers.opex_smart_import_worker import (
    OpexSmartImportWorker,
)


pytestmark = pytest.mark.unit


def test_corrupted_smart_template_is_contextual(
    tmp_path,
):
    path = tmp_path / "plantilla.xlsx"

    path.write_bytes(
        b"archivo-no-es-excel"
    )

    with pytest.raises(
        OpexSmartTemplateError,
        match="No se pudo abrir",
    ):
        OpexSmartTemplateLoader().load(
            path
        )


def test_missing_master_is_contextual(
    tmp_path,
):
    with pytest.raises(
        OpexMasterDataError,
        match="CUENTA.xlsx",
    ):
        OpexMasterDataLoader(
            tmp_path
        ).load()


def test_corrupted_fx_file_is_contextual(
    tmp_path,
):
    path = tmp_path / "TC.xlsx"

    path.write_bytes(
        b"archivo-no-es-excel"
    )

    with pytest.raises(
        OpexFxLoadError,
        match="No se pudo abrir TC.xlsx",
    ):
        OpexFxLoader().load(
            path
        )


def test_worker_emits_success_and_forwards_request():
    result = object()

    class FakeService:
        def __init__(self):
            self.kwargs = None

        def prepare(
            self,
            **kwargs,
        ):
            self.kwargs = kwargs
            return result

    service = FakeService()

    worker = OpexSmartImportWorker(
        service=service,
        source_path="plantilla.xlsx",
        origin="PB",
        budgeter="MAURO",
        actor="tester",
        overrides=("decision",),
    )

    succeeded = []
    failed = []

    worker.succeeded.connect(
        succeeded.append
    )

    worker.failed.connect(
        failed.append
    )

    worker.run()

    assert succeeded == [
        result
    ]

    assert failed == []

    assert (
        service.kwargs["source_path"]
        == "plantilla.xlsx"
    )

    assert (
        service.kwargs["origin"]
        == "PB"
    )

    assert (
        service.kwargs["budgeter"]
        == "MAURO"
    )

    assert (
        service.kwargs["actor"]
        == "tester"
    )

    assert (
        service.kwargs["overrides"]
        == ("decision",)
    )


def test_worker_emits_failure_without_success():
    class FakeService:
        @staticmethod
        def prepare(
            **kwargs,
        ):
            raise RuntimeError(
                "synthetic failure"
            )

    worker = OpexSmartImportWorker(
        service=FakeService(),
        source_path="plantilla.xlsx",
        origin="PB",
        budgeter="MAURO",
        actor="tester",
    )

    succeeded = []
    failed = []

    worker.succeeded.connect(
        succeeded.append
    )

    worker.failed.connect(
        failed.append
    )

    worker.run()

    assert succeeded == []

    assert len(failed) == 1

    assert (
        "RuntimeError: synthetic failure"
        in failed[0]
    )


class FakeWorker:
    def __init__(
        self,
        running,
    ):
        self._running = running

    def isRunning(
        self,
    ):
        return self._running


def test_dialog_detects_running_analysis():
    holder = SimpleNamespace(
        _worker=FakeWorker(
            True
        )
    )

    assert (
        OpexSmartImportDialog
        ._analysis_running(
            holder
        )
    )


def test_dialog_detects_idle_analysis():
    holder = SimpleNamespace(
        _worker=None
    )

    assert not (
        OpexSmartImportDialog
        ._analysis_running(
            holder
        )
    )
