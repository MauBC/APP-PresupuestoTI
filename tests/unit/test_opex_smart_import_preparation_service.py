from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.services.opex_smart_import_preparation_service import (
    OpexSmartImportPreparationError,
    OpexSmartImportPreparationService,
)


pytestmark = pytest.mark.unit


def valid_file(
    tmp_path,
):
    path = (
        tmp_path
        / "plantilla.xlsx"
    )

    path.write_bytes(
        b"x"
    )

    return path


def test_validate_request_normalizes_values(
    tmp_path,
):
    path = valid_file(
        tmp_path
    )

    result = (
        OpexSmartImportPreparationService
        .validate_request(
            source_path=path,
            origin="  PB  ",
            budgeter="  MAURO TEST  ",
            actor="  actor@test  ",
        )
    )

    assert result == (
        path.resolve(),
        "PB",
        "MAURO TEST",
        "actor@test",
    )


def test_validate_request_rejects_missing_file(
    tmp_path,
):
    with pytest.raises(
        OpexSmartImportPreparationError,
        match="no existe",
    ):
        (
            OpexSmartImportPreparationService
            .validate_request(
                source_path=(
                    tmp_path
                    / "missing.xlsx"
                ),
                origin="PB",
                budgeter="MAURO",
                actor="actor",
            )
        )


def test_validate_request_requires_origin(
    tmp_path,
):
    with pytest.raises(
        OpexSmartImportPreparationError,
        match="Origen",
    ):
        (
            OpexSmartImportPreparationService
            .validate_request(
                source_path=(
                    valid_file(
                        tmp_path
                    )
                ),
                origin=" ",
                budgeter="MAURO",
                actor="actor",
            )
        )


def test_validate_request_requires_budgeter(
    tmp_path,
):
    with pytest.raises(
        OpexSmartImportPreparationError,
        match="Presupuestador",
    ):
        (
            OpexSmartImportPreparationService
            .validate_request(
                source_path=(
                    valid_file(
                        tmp_path
                    )
                ),
                origin="PB",
                budgeter=" ",
                actor="actor",
            )
        )


def test_validate_request_requires_actor(
    tmp_path,
):
    with pytest.raises(
        OpexSmartImportPreparationError,
        match="usuario actual",
    ):
        (
            OpexSmartImportPreparationService
            .validate_request(
                source_path=(
                    valid_file(
                        tmp_path
                    )
                ),
                origin="PB",
                budgeter="MAURO",
                actor=" ",
            )
        )


def test_build_result_creates_business_summary(
    tmp_path,
):
    source = valid_file(
        tmp_path
    )

    account = SimpleNamespace(
        nombre_cuenta="SOFTWARE ADM",
        atributo_2="GASTOS TI",
    )

    distribution = SimpleNamespace(
        mode="IMPORTE"
    )

    cebe = SimpleNamespace(
        tipo_servicio_cg="TESORERIA"
    )

    state_a = SimpleNamespace(
        account_selection=account,
        resolved_distribution=(
            distribution
        ),
        cebe_selections={
            "51IC000000": cebe,
        },
    )

    state_b = SimpleNamespace(
        account_selection=account,
        resolved_distribution=(
            distribution
        ),
        cebe_selections={},
    )

    workbook = SimpleNamespace(
        budgets=(
            object(),
            object(),
        )
    )

    workbook_state = SimpleNamespace(
        budgets={
            "Sheet1": state_a,
            "Sheet2": state_b,
        }
    )

    rows = (
        {
            "anio_usd":
                Decimal("100.50"),
            "pais": "PE",
            "moneda_facturacion":
                "USD",
        },
        {
            "anio_usd":
                Decimal("25.25"),
            "pais": "CO",
            "moneda_facturacion":
                "PEN",
        },
        {
            "anio_usd":
                Decimal("10.00"),
            "pais": "CO",
            "moneda_facturacion":
                "USD",
        },
    )

    result = (
        OpexSmartImportPreparationService
        ._build_result(
            source=source,
            workbook=workbook,
            workbook_state=(
                workbook_state
            ),
            rows=rows,
        )
    )

    assert (
        result.total_usd
        == Decimal("135.75")
    )

    assert (
        result.budget_count
        == 2
    )

    assert (
        result.auto_cebe_count
        == 1
    )

    assert (
        result.country_counts
        == (
            (
                "CO",
                2,
            ),
            (
                "PE",
                1,
            ),
        )
    )

    assert (
        result.invoice_currency_counts
        == (
            (
                "PEN",
                1,
            ),
            (
                "USD",
                2,
            ),
        )
    )

    assert (
        result.decisions[0]
        .cebe_decisions[0]
        .tipo_servicio_cg
        == "TESORERIA"
    )
