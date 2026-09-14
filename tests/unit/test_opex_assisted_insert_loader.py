import pytest

from app.ui.workers.opex_assisted_insert_loader import (
    OpexAssistedInferenceLoadThread,
)


pytestmark = pytest.mark.unit


def test_worker_emits_loaded_service():
    module_config = object()
    service = object()

    calls = []

    def factory(
        received_config,
    ):
        calls.append(
            received_config
        )

        return service

    worker = (
        OpexAssistedInferenceLoadThread(
            module_config,
            service_factory=factory,
        )
    )

    loaded = []
    failed = []

    worker.loaded.connect(
        loaded.append
    )

    worker.failed.connect(
        failed.append
    )

    worker.run()

    assert calls == [
        module_config
    ]

    assert loaded == [
        service
    ]

    assert failed == []


def test_worker_emits_failure():
    def factory(
        _,
    ):
        raise RuntimeError(
            "snapshot failed"
        )

    worker = (
        OpexAssistedInferenceLoadThread(
            object(),
            service_factory=factory,
        )
    )

    loaded = []
    failed = []

    worker.loaded.connect(
        loaded.append
    )

    worker.failed.connect(
        failed.append
    )

    worker.run()

    assert loaded == []

    assert len(failed) == 1

    assert (
        "RuntimeError"
        in failed[0]
    )

    assert (
        "snapshot failed"
        in failed[0]
    )
