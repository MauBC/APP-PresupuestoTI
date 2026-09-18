from types import SimpleNamespace

import pytest

from app.ui.dialogs.opex_assisted_insert_dialog import (
    build_opex_assisted_base_dimensions,
    build_opex_assisted_inference_values,
    format_opex_assisted_inference,
)


pytestmark = pytest.mark.unit


def values(
    **overrides,
):
    result = {
        "presupuestador":
            "ANA TEST",
        "origen":
            "Local",
        "nombre_gasto":
            "LICENCIAS",
        "proveedor":
            "",
        "ceco":
            "001234",
    }

    result.update(
        overrides
    )

    return result


def test_base_dimensions_keep_user_values():
    result = (
        build_opex_assisted_base_dimensions(
            values()
        )
    )

    assert (
        result["presupuestador"]
        == "ANA TEST"
    )

    assert (
        result["origen"]
        == "Local"
    )

    assert (
        result["ceco"]
        == "001234"
    )


def test_inference_excludes_user_owned_dimensions():
    result = (
        build_opex_assisted_inference_values(
            values()
        )
    )

    assert (
        "presupuestador"
        not in result
    )

    assert "origen" not in result

    assert result == {
        "nombre_gasto":
            "LICENCIAS",
        "ceco":
            "001234",
    }


def test_required_user_dimensions_are_validated():
    with pytest.raises(
        ValueError,
        match="Presupuestador",
    ):
        (
            build_opex_assisted_base_dimensions(
                values(
                    presupuestador="   ",
                )
            )
        )


def test_at_least_one_historical_clue_is_required():
    with pytest.raises(
        ValueError,
        match="al menos un dato",
    ):
        (
            build_opex_assisted_base_dimensions(
                values(
                    nombre_gasto="",
                    proveedor="",
                    ceco="",
                )
            )
        )


def test_summary_hides_user_owned_historical_values():
    result = SimpleNamespace(
        matching_row_count=3,
        inferred_values=(
            (
                "pais",
                "Perú",
            ),
            (
                "presupuestador",
                "HISTORICO",
            ),
        ),
        ambiguous_values=(
            (
                "categoria_gasto",
                (
                    "SOFTWARE",
                    "LICENCIAS",
                ),
            ),
            (
                "origen",
                (
                    "Local",
                    "Regional",
                ),
            ),
        ),
        no_data_columns=(
            "segmentacion",
            "presupuestador",
        ),
    )

    text = (
        format_opex_assisted_inference(
            result
        )
    )

    assert (
        "Coincidencias historicas: 3"
        in text
    )

    assert "Pais: Perú" in text

    assert (
        "Categoria Gasto"
        in text
    )

    assert "Segmentacion" in text
    assert "HISTORICO" not in text
    assert "Regional" not in text

def test_allocation_parser_preserves_ceco_zeroes():
    from app.ui.dialogs.opex_assisted_insert_dialog import (
        parse_opex_assisted_allocations,
    )

    result = (
        parse_opex_assisted_allocations(
            """
            001001;20
            001002;30
            001003;50
            """
        )
    )

    assert result == (
        (
            "001001",
            "20",
        ),
        (
            "001002",
            "30",
        ),
        (
            "001003",
            "50",
        ),
    )


def test_allocation_parser_accepts_equals():
    from app.ui.dialogs.opex_assisted_insert_dialog import (
        parse_opex_assisted_allocations,
    )

    result = (
        parse_opex_assisted_allocations(
            "001001=100.50"
        )
    )

    assert result == (
        (
            "001001",
            "100.50",
        ),
    )


def test_allocation_parser_rejects_duplicates():
    from app.ui.dialogs.opex_assisted_insert_dialog import (
        parse_opex_assisted_allocations,
    )

    with pytest.raises(
        ValueError,
        match="duplicado",
    ):
        (
            parse_opex_assisted_allocations(
                """
                001001;50
                001001;50
                """
            )
        )


def test_insert_dimensions_keep_only_historical_clues():
    from app.ui.dialogs.opex_assisted_insert_dialog import (
        build_opex_assisted_insert_dimensions,
    )

    result = (
        build_opex_assisted_insert_dimensions(
            values()
        )
    )

    assert result == {
        "nombre_gasto":
            "LICENCIAS",
    }

    assert "ceco" not in result
    assert "presupuestador" not in result
    assert "origen" not in result


def test_preview_formatter_exposes_blocked_ceco():
    from decimal import Decimal
    from types import SimpleNamespace

    from app.ui.dialogs.opex_assisted_insert_dialog import (
        format_opex_assisted_preview,
    )

    item = SimpleNamespace(
        ceco="001001",
        annual_total=(
            Decimal("100.00")
        ),
        matching_row_count=2,
        is_ready=False,
        blockers=(
            "AMBIGUO:proveedor",
        ),
        ambiguous_values=(
            (
                "proveedor",
                (
                    "MICROSOFT",
                    "ORACLE",
                ),
            ),
        ),
    )

    preview = SimpleNamespace(
        mode="AMOUNT",
        source_total=(
            Decimal("100.00")
        ),
        allocated_total=(
            Decimal("100.00")
        ),
        row_count=1,
        ready_count=0,
        blocked_count=1,
        items=(
            item,
        ),
    )

    text = (
        format_opex_assisted_preview(
            preview
        )
    )

    assert "001001" in text
    assert "BLOQUEADO" in text
    assert "MICROSOFT" in text
    assert "ORACLE" in text


class RecordingAssistedPreviewService:
    def __init__(
        self,
    ):
        self.calls = []

    def preview_percentages(
        self,
        **kwargs,
    ):
        self.calls.append(
            (
                "PERCENTAGE",
                kwargs,
            )
        )

        return "percentage-preview"

    def preview_amounts(
        self,
        **kwargs,
    ):
        self.calls.append(
            (
                "AMOUNT",
                kwargs,
            )
        )

        return "amount-preview"


def test_preview_request_routes_percentage_mode():
    from app.ui.dialogs.opex_assisted_insert_dialog import (
        build_opex_assisted_preview_request,
    )

    service = (
        RecordingAssistedPreviewService()
    )

    result = (
        build_opex_assisted_preview_request(
            service,
            values=values(),
            mode="PERCENTAGE",
            allocations_text=(
                "001001;40\n"
                "001002;60"
            ),
            annual_total="1000",
            actor="tester",
        )
    )

    assert result == "percentage-preview"

    mode, kwargs = service.calls[0]

    assert mode == "PERCENTAGE"

    assert kwargs["allocations"] == (
        (
            "001001",
            "40",
        ),
        (
            "001002",
            "60",
        ),
    )

    assert kwargs["annual_total"] == "1000"

    assert kwargs["base_dimensions"] == {
        "nombre_gasto":
            "LICENCIAS",
    }

    assert kwargs["row_overrides"] == {
        "presupuestador":
            "ANA TEST",
        "origen":
            "Local",
        "periodo":
            "2027 PB",
    }


def test_preview_request_routes_amount_mode():
    from app.ui.dialogs.opex_assisted_insert_dialog import (
        build_opex_assisted_preview_request,
    )

    service = (
        RecordingAssistedPreviewService()
    )

    result = (
        build_opex_assisted_preview_request(
            service,
            values=values(),
            mode="AMOUNT",
            allocations_text=(
                "001001;250.50\n"
                "001002;749.50"
            ),
            annual_total="NO SE USA",
            actor="tester",
        )
    )

    assert result == "amount-preview"

    mode, kwargs = service.calls[0]

    assert mode == "AMOUNT"

    assert kwargs["allocations"] == (
        (
            "001001",
            "250.50",
        ),
        (
            "001002",
            "749.50",
        ),
    )

    assert (
        "annual_total"
        not in kwargs
    )


def test_preview_request_requires_total_for_percentage():
    from app.ui.dialogs.opex_assisted_insert_dialog import (
        build_opex_assisted_preview_request,
    )

    service = (
        RecordingAssistedPreviewService()
    )

    with pytest.raises(
        ValueError,
        match="total anual",
    ):
        (
            build_opex_assisted_preview_request(
                service,
                values=values(),
                mode="PERCENTAGE",
                allocations_text=(
                    "001001;100"
                ),
                annual_total="   ",
                actor="tester",
            )
        )

    assert service.calls == []


def test_preview_request_rejects_unknown_mode():
    from app.ui.dialogs.opex_assisted_insert_dialog import (
        build_opex_assisted_preview_request,
    )

    service = (
        RecordingAssistedPreviewService()
    )

    with pytest.raises(
        ValueError,
        match="Modo",
    ):
        (
            build_opex_assisted_preview_request(
                service,
                values=values(),
                mode="UNKNOWN",
                allocations_text=(
                    "001001;100"
                ),
                annual_total="1000",
                actor="tester",
            )
        )

    assert service.calls == []


class RecordingAssistedPreviewService:
    def __init__(
        self,
    ):
        self.calls = []

    def preview_percentages(
        self,
        **kwargs,
    ):
        self.calls.append(
            (
                "PERCENTAGE",
                kwargs,
            )
        )

        return "percentage-preview"

    def preview_amounts(
        self,
        **kwargs,
    ):
        self.calls.append(
            (
                "AMOUNT",
                kwargs,
            )
        )

        return "amount-preview"


def test_preview_request_routes_percentage_mode():
    from app.ui.dialogs.opex_assisted_insert_dialog import (
        build_opex_assisted_preview_request,
    )

    service = (
        RecordingAssistedPreviewService()
    )

    result = (
        build_opex_assisted_preview_request(
            service,
            values=values(),
            mode="PERCENTAGE",
            allocations_text=(
                "001001;40\n"
                "001002;60"
            ),
            annual_total="1000",
            actor="tester",
        )
    )

    assert result == "percentage-preview"

    mode, kwargs = service.calls[0]

    assert mode == "PERCENTAGE"

    assert kwargs["allocations"] == (
        (
            "001001",
            "40",
        ),
        (
            "001002",
            "60",
        ),
    )

    assert kwargs["annual_total"] == "1000"

    assert kwargs["base_dimensions"] == {
        "nombre_gasto":
            "LICENCIAS",
    }

    assert kwargs["row_overrides"] == {
        "presupuestador":
            "ANA TEST",
        "origen":
            "Local",
        "periodo":
            "2027 PB",
    }


def test_preview_request_routes_amount_mode():
    from app.ui.dialogs.opex_assisted_insert_dialog import (
        build_opex_assisted_preview_request,
    )

    service = (
        RecordingAssistedPreviewService()
    )

    result = (
        build_opex_assisted_preview_request(
            service,
            values=values(),
            mode="AMOUNT",
            allocations_text=(
                "001001;250.50\n"
                "001002;749.50"
            ),
            annual_total="NO SE USA",
            actor="tester",
        )
    )

    assert result == "amount-preview"

    mode, kwargs = service.calls[0]

    assert mode == "AMOUNT"

    assert kwargs["allocations"] == (
        (
            "001001",
            "250.50",
        ),
        (
            "001002",
            "749.50",
        ),
    )

    assert (
        "annual_total"
        not in kwargs
    )


def test_preview_request_requires_total_for_percentage():
    from app.ui.dialogs.opex_assisted_insert_dialog import (
        build_opex_assisted_preview_request,
    )

    service = (
        RecordingAssistedPreviewService()
    )

    with pytest.raises(
        ValueError,
        match="total anual",
    ):
        (
            build_opex_assisted_preview_request(
                service,
                values=values(),
                mode="PERCENTAGE",
                allocations_text=(
                    "001001;100"
                ),
                annual_total="   ",
                actor="tester",
            )
        )

    assert service.calls == []


def test_preview_request_rejects_unknown_mode():
    from app.ui.dialogs.opex_assisted_insert_dialog import (
        build_opex_assisted_preview_request,
    )

    service = (
        RecordingAssistedPreviewService()
    )

    with pytest.raises(
        ValueError,
        match="Modo",
    ):
        (
            build_opex_assisted_preview_request(
                service,
                values=values(),
                mode="UNKNOWN",
                allocations_text=(
                    "001001;100"
                ),
                annual_total="1000",
                actor="tester",
            )
        )

    assert service.calls == []
