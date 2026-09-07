from unittest.mock import MagicMock

import pytest

from app.services.presupuesto_service import (
    PresupuestoService,
)


@pytest.mark.unit
def test_page_zero_uses_zero_offset():
    repository = MagicMock()

    service = PresupuestoService(
        repository
    )

    service.get_page(
        page_index=0,
        page_size=250,
    )

    repository.get_page.assert_called_once_with(
        limit=250,
        offset=0,
    )


@pytest.mark.unit
def test_page_two_calculates_offset():
    repository = MagicMock()

    service = PresupuestoService(
        repository
    )

    service.get_page(
        page_index=2,
        page_size=250,
    )

    repository.get_page.assert_called_once_with(
        limit=250,
        offset=500,
    )


@pytest.mark.unit
def test_rejects_negative_page():
    service = PresupuestoService(
        MagicMock()
    )

    with pytest.raises(ValueError):
        service.get_page(
            page_index=-1,
            page_size=250,
        )


@pytest.mark.unit
def test_rejects_page_size_over_limit():
    service = PresupuestoService(
        MagicMock()
    )

    with pytest.raises(ValueError):
        service.get_page(
            page_index=0,
            page_size=1001,
        )