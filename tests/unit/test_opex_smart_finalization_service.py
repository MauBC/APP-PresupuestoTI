from datetime import (
    datetime,
    timezone,
)
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.config.budget_modules import (
    OPEX_MODULE_CONFIG,
)
from app.config.presupuesto_schema import (
    AMOUNT_GROUPS,
    MONTHS,
)
from app.models.opex_smart_enrichment import (
    OpexSmartEnrichedRow,
)
from app.models.opex_smart_finalization import (
    OpexSmartInsertionContext,
)
from app.services.new_budget_row_service import (
    NewBudgetRowService,
)
from app.services.opex_smart_finalization_service import (
    OpexSmartFinalizationError,
    OpexSmartFinalizationService,
)


pytestmark = pytest.mark.unit


NOW = datetime(
    2026,
    9,
    12,
    3,
    0,
    tzinfo=timezone.utc,
)


def enrichment(
    *,
    ceco="001234",
):
    return SimpleNamespace(
        pais="PER",
        compania="RANSA PERU",
        ceco=ceco,
        centro_beneficio="001230",
        numero_cuenta="635610007",
        nombre_cuenta="SERVICIOS TI",
        gyp="GASTOS DE ADMINISTRACIÓN",
        desc_cebe="CEBE TEST",
        macroservicio_cg="TECNOLOGIA",
        tipo_servicio_cg="SOFTWARE",
        sede_cg="LIMA",
        region_cg="PERU",
        categoria_gasto="SOFTWARE",
        atributo_2="GASTOS TI",
        segmentacion="TI",
    )


def row(
    *,
    ceco="001234",
    tipo="MENSUAL",
    monto_ceco="100",
):
    return OpexSmartEnrichedRow(
        sheet_name="GASTO 1",
        excel_row=8,
        nombre_gasto="LICENCIAS",
        proveedor="PROVEEDOR",
        moneda_facturacion="USD",
        numero_cuenta="635610007",
        tipo=tipo,
        monto_presupuesto=(
            Decimal("1000")
        ),
        ceco=ceco,
        monto_ceco=Decimal(
            monto_ceco
        ),
        enrichment=enrichment(
            ceco=ceco
        ),
    )


class FakeStateService:
    def __init__(
        self,
        rows,
        *,
        ready=True,
    ):
        self.rows = tuple(
            rows
        )
        self.ready = ready
        self.ready_calls = 0
        self.build_calls = 0

    def workbook_ready(
        self,
        workbook_state,
    ):
        self.ready_calls += 1
        return self.ready

    def build_workbook_rows(
        self,
        workbook_state,
    ):
        self.build_calls += 1
        return self.rows


class FakeWorkspace:
    def __init__(
        self,
    ):
        self.calls = []

    def add_new_rows(
        self,
        rows,
        *,
        description,
    ):
        rows = tuple(
            dict(row)
            for row in rows
        )

        self.calls.append(
            (
                rows,
                description,
            )
        )

        return tuple(
            range(
                len(rows)
            )
        )


def mirror_amount_provider(
    periodized,
):
    monthly = (
        periodized.monthly_map()
    )

    return {
        f"{month}_{group}":
            monthly[month]
        for group in AMOUNT_GROUPS
        for month in MONTHS
    }


def service(
    rows,
    *,
    ready=True,
):
    ids = iter(
        (
            "row-001",
            "row-002",
            "row-003",
        )
    )

    return (
        OpexSmartFinalizationService(
            state_service=(
                FakeStateService(
                    rows,
                    ready=ready,
                )
            ),
            amount_provider=(
                mirror_amount_provider
            ),
            row_service=(
                NewBudgetRowService(
                    OPEX_MODULE_CONFIG,
                    row_id_factory=(
                        lambda: next(ids)
                    ),
                )
            ),
        )
    )


def context():
    return (
        OpexSmartInsertionContext(
            origen="Local",
            presupuestador=(
                "MAURO TEST"
            ),
        )
    )


def test_builds_2027_business_dimensions():
    result = (
        service(
            (
                row(),
            )
        )
        .build_rows(
            object(),
            context=context(),
            actor="tester",
            timestamp=NOW,
        )
    )

    assert len(result) == 1

    value = result[0]

    assert (
        value["origen"]
        == "Local"
    )

    assert (
        value["presupuestador"]
        == "MAURO TEST"
    )

    assert (
        value["periodo"]
        == "2027 PB"
    )

    assert (
        value["pais"]
        == "PER"
    )

    assert (
        value["compania"]
        == "RANSA PERU"
    )

    assert (
        value["ceco"]
        == "001234"
    )

    assert (
        value["centro_beneficio"]
        == "001230"
    )

    assert (
        value["numero_cuenta"]
        == "635610007"
    )

    assert (
        value["nombre_gasto"]
        == "LICENCIAS"
    )

    assert (
        value["proveedor"]
        == "PROVEEDOR"
    )


def test_hidden_legacy_dimensions_are_not_inserted():
    result = (
        service(
            (
                row(),
            )
        )
        .build_rows(
            object(),
            context=context(),
            actor="tester",
            timestamp=NOW,
        )[0]
    )

    assert "vp" not in result
    assert "vp2" not in result


def test_monthly_periodization_reaches_amount_service():
    result = (
        service(
            (
                row(
                    tipo="MENSUAL",
                    monto_ceco="100.25",
                ),
            )
        )
        .build_rows(
            object(),
            context=context(),
            actor="tester",
            timestamp=NOW,
        )[0]
    )

    for group in AMOUNT_GROUPS:
        assert (
            result[
                f"enero_{group}"
            ]
            == Decimal("100.25")
        )

        assert (
            result[
                f"diciembre_{group}"
            ]
            == Decimal("100.25")
        )

        assert (
            result[
                f"anio_{group}"
            ]
            == Decimal("1203.00")
        )


def test_annual_periodization_reaches_amount_service():
    result = (
        service(
            (
                row(
                    tipo="ANUAL",
                    monto_ceco="1000",
                ),
            )
        )
        .build_rows(
            object(),
            context=context(),
            actor="tester",
            timestamp=NOW,
        )[0]
    )

    for group in AMOUNT_GROUPS:
        monthly = tuple(
            result[
                f"{month}_{group}"
            ]
            for month in MONTHS
        )

        assert (
            sum(
                monthly,
                Decimal("0.00"),
            )
            == Decimal("1000.00")
        )

        assert (
            max(monthly)
            - min(monthly)
            <= Decimal("0.01")
        )

        assert (
            result[
                f"anio_{group}"
            ]
            == Decimal("1000.00")
        )


def test_not_ready_workbook_is_rejected():
    value = service(
        (
            row(),
        ),
        ready=False,
    )

    with pytest.raises(
        OpexSmartFinalizationError,
        match="no esta completamente",
    ):
        value.build_rows(
            object(),
            context=context(),
            actor="tester",
            timestamp=NOW,
        )


@pytest.mark.parametrize(
    (
        "field",
        "value",
    ),
    (
        (
            "origen",
            " ",
        ),
        (
            "presupuestador",
            "",
        ),
    ),
)
def test_required_insertion_context(
    field,
    value,
):
    data = {
        "origen":
            "Local",
        "presupuestador":
            "MAURO TEST",
    }

    data[field] = value

    with pytest.raises(
        OpexSmartFinalizationError,
        match=field,
    ):
        (
            service(
                (
                    row(),
                )
            )
            .build_rows(
                object(),
                context=(
                    OpexSmartInsertionContext(
                        **data
                    )
                ),
                actor="tester",
                timestamp=NOW,
            )
        )


def test_period_other_than_2027_pb_is_rejected():
    with pytest.raises(
        OpexSmartFinalizationError,
        match="2027 PB",
    ):
        (
            service(
                (
                    row(),
                )
            )
            .build_rows(
                object(),
                context=(
                    OpexSmartInsertionContext(
                        origen="Local",
                        presupuestador=(
                            "MAURO TEST"
                        ),
                        periodo="2026 PB",
                    )
                ),
                actor="tester",
                timestamp=NOW,
            )
        )


def test_workspace_receives_all_rows_in_one_call():
    value = service(
        (
            row(
                ceco="001234",
            ),
            row(
                ceco="009999",
            ),
        )
    )

    workspace = FakeWorkspace()

    session_ids = (
        value.add_to_workspace(
            workspace,
            object(),
            context=context(),
            actor="tester",
            timestamp=NOW,
        )
    )

    assert session_ids == (
        0,
        1,
    )

    assert (
        len(
            workspace.calls
        )
        == 1
    )

    rows, description = (
        workspace.calls[0]
    )

    assert len(rows) == 2

    assert (
        description
        == (
            "Insercion inteligente "
            "OPEX 2027"
        )
    )

    assert (
        rows[0]["row_id"]
        == "row-001"
    )

    assert (
        rows[1]["row_id"]
        == "row-002"
    )


def test_technical_metadata_comes_from_new_row_service():
    result = (
        service(
            (
                row(),
            )
        )
        .build_rows(
            object(),
            context=context(),
            actor="tester",
            timestamp=NOW,
        )[0]
    )

    assert (
        result["row_id"]
        == "row-001"
    )

    assert result["habilitado"] is True
    assert result["version"] == 1

    assert (
        result["created_at"]
        == NOW
    )

    assert (
        result["updated_at"]
        == NOW
    )

    assert (
        result["created_by"]
        == "tester"
    )

    assert (
        result["updated_by"]
        == "tester"
    )
