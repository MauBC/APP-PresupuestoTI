
import pytest

from app.services.sharepoint_sync_queue import (
    SharePointSyncRequestQueue,
)


pytestmark = pytest.mark.unit


def test_first_request_starts_immediately():
    queue = (
        SharePointSyncRequestQueue()
    )

    request = queue.request(
        source_batch_id="batch-1",
    )

    assert request is not None
    assert queue.is_running
    assert not queue.has_pending

    assert (
        request.source_batch_id
        == "batch-1"
    )


def test_second_request_is_queued():
    queue = (
        SharePointSyncRequestQueue()
    )

    queue.request(
        source_batch_id="batch-1",
    )

    result = queue.request(
        source_batch_id="batch-2",
    )

    assert result is None
    assert queue.has_pending


def test_pending_uses_latest_batch():
    queue = (
        SharePointSyncRequestQueue()
    )

    queue.request(
        source_batch_id="batch-1",
    )

    queue.request(
        source_batch_id="batch-2",
    )

    queue.request(
        source_batch_id="batch-3",
    )

    next_request = (
        queue.complete()
    )

    assert next_request is not None

    assert (
        next_request.source_batch_id
        == "batch-3"
    )

    assert queue.is_running
    assert not queue.has_pending


def test_manual_flag_is_preserved_when_coalescing():
    queue = (
        SharePointSyncRequestQueue()
    )

    queue.request(
        source_batch_id="batch-1",
    )

    queue.request(
        source_batch_id="batch-2",
    )

    queue.request(
        manual=True,
    )

    next_request = (
        queue.complete()
    )

    assert next_request.manual

    assert (
        next_request.source_batch_id
        == "batch-2"
    )


def test_complete_without_pending_releases_queue():
    queue = (
        SharePointSyncRequestQueue()
    )

    queue.request(
        source_batch_id="batch-1",
    )

    result = queue.complete()

    assert result is None
    assert not queue.is_running
    assert not queue.has_pending

def test_large_delete_authorization_is_preserved_when_coalescing():
    queue = SharePointSyncRequestQueue()

    queue.request(
        source_batch_id="batch-1",
    )

    queue.request(
        source_batch_id="batch-2",
        allow_large_delete=True,
    )

    queue.request(
        manual=True,
    )

    next_request = queue.complete()

    assert next_request is not None
    assert next_request.allow_large_delete
    assert next_request.manual

    assert (
        next_request.source_batch_id
        == "batch-2"
    )
