from dataclasses import dataclass


class CapexFullLoadValidationError(
    RuntimeError
):
    pass


@dataclass(
    frozen=True,
    slots=True,
)
class CapexFullLoadMetrics:
    total_rows: int
    unique_row_ids: int
    disabled_rows: int
    min_version: int | None
    max_version: int | None
    years: tuple[
        int,
        ...
    ]


def validate_capex_full_load_metrics(
    metrics: CapexFullLoadMetrics,
    *,
    expected_rows: int,
    expected_year: int | None,
) -> None:
    if expected_rows < 1:
        raise CapexFullLoadValidationError(
            "expected_rows debe ser "
            "mayor que cero."
        )

    if (
        metrics.total_rows
        != expected_rows
    ):
        raise CapexFullLoadValidationError(
            "Cantidad total CAPEX "
            "incorrecta. "
            f"Esperadas={expected_rows}; "
            f"encontradas="
            f"{metrics.total_rows}."
        )

    if (
        metrics.unique_row_ids
        != expected_rows
    ):
        raise CapexFullLoadValidationError(
            "Los row_id CAPEX "
            "no son unicos."
        )

    if (
        metrics.disabled_rows
        != 0
    ):
        raise CapexFullLoadValidationError(
            "La carga CAPEX contiene "
            "filas deshabilitadas."
        )

    if (
        metrics.min_version != 1
        or metrics.max_version != 1
    ):
        raise CapexFullLoadValidationError(
            "La version inicial CAPEX "
            "debe ser 1."
        )

    if (
        expected_year is not None
        and metrics.years
        != (
            expected_year,
        )
    ):
        raise CapexFullLoadValidationError(
            "Los anios cargados no "
            "coinciden con el periodo "
            "esperado. "
            f"Esperado={expected_year}; "
            f"encontrados="
            f"{metrics.years}."
        )
