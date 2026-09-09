from dataclasses import dataclass


class CapexSmokeValidationError(
    RuntimeError
):
    pass


@dataclass(
    frozen=True,
    slots=True,
)
class CapexSmokeMetrics:
    selected_rows: int
    unique_row_ids: int
    disabled_rows: int
    min_version: int | None
    max_version: int | None


def validate_capex_smoke_metrics(
    metrics: CapexSmokeMetrics,
    *,
    expected_rows: int,
) -> None:
    if expected_rows < 1:
        raise CapexSmokeValidationError(
            "expected_rows debe ser "
            "mayor que cero."
        )

    if (
        metrics.selected_rows
        != expected_rows
    ):
        raise CapexSmokeValidationError(
            "Cantidad de filas cargadas "
            "incorrecta. "
            f"Esperadas={expected_rows}; "
            f"encontradas="
            f"{metrics.selected_rows}."
        )

    if (
        metrics.unique_row_ids
        != expected_rows
    ):
        raise CapexSmokeValidationError(
            "Los row_id del smoke test "
            "no son unicos."
        )

    if (
        metrics.disabled_rows
        != 0
    ):
        raise CapexSmokeValidationError(
            "El smoke test contiene "
            "filas deshabilitadas."
        )

    if (
        metrics.min_version != 1
        or metrics.max_version != 1
    ):
        raise CapexSmokeValidationError(
            "La version inicial CAPEX "
            "debe ser 1."
        )
