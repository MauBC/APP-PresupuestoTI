from decimal import Decimal
from typing import Any

from app.config.capex_schema import (
    CAPEX_AMOUNT_COLUMNS,
    CAPEX_CODE_COLUMNS,
    CAPEX_EXPECTED_YEAR,
    CAPEX_FREE_TEXT_COLUMNS,
    CAPEX_HEADER_ALIASES,
    CAPEX_INTEGER_COLUMNS,
    CAPEX_INTERNAL_TO_RAW,
    CAPEX_ML_MONTH_COLUMNS,
    CAPEX_ML_TOTAL_COLUMN,
    CAPEX_NULLABLE_TEXT_COLUMNS,
    CAPEX_RAW_TO_INTERNAL,
    CAPEX_STRING_COLUMNS,
    CAPEX_USD_MONTH_COLUMNS,
    CAPEX_USD_TOTAL_COLUMN,
)
from app.models.capex_import import (
    CapexCleanRowResult,
    CapexImportIssue,
    CapexIssueSeverity,
)
from app.services.capex_cleaner import (
    BIGQUERY_NUMERIC_QUANTUM,
    CapexCleaningError,
    clean_capex_amount,
    clean_capex_integer,
    clean_capex_text,
    is_blank_like,
    is_excel_error_token,
)


ZERO = Decimal(
    "0.000000000"
)

TOTAL_NOISE_TOLERANCE = Decimal(
    "0.000001"
)

TOTAL_TOLERANCE = Decimal(
    "0.01"
)


def _normalize_headers(
    raw_row: dict[str, Any],
) -> dict[str, Any]:
    normalized = {}

    for key, value in raw_row.items():
        header = (
            ""
            if key is None
            else str(key).strip()
        )

        header = (
            CAPEX_HEADER_ALIASES
            .get(
                header,
                header,
            )
        )

        if not header:
            continue

        normalized[
            header
        ] = value

    return normalized


def _issue(
    *,
    row_number,
    column,
    code,
    message,
    severity,
    raw_value=None,
):
    return CapexImportIssue(
        row_number=row_number,
        column=column,
        code=code,
        message=message,
        severity=severity,
        raw_value=raw_value,
    )


def _raw_value(
    normalized,
    internal_column,
):
    raw_header = (
        CAPEX_INTERNAL_TO_RAW[
            internal_column
        ]
    )

    return normalized.get(
        raw_header
    )


def clean_and_validate_capex_row(
    raw_row: dict[str, Any],
    *,
    row_number: int,
    expected_year:
        int | None
        = CAPEX_EXPECTED_YEAR,
) -> CapexCleanRowResult:
    normalized = (
        _normalize_headers(
            raw_row
        )
    )

    cleaned = {}
    issues = []

    unknown_headers = tuple(
        header
        for header in normalized
        if (
            header
            not in CAPEX_RAW_TO_INTERNAL
        )
    )

    for header in unknown_headers:
        issues.append(
            _issue(
                row_number=row_number,
                column=header,
                code="UNKNOWN_COLUMN",
                message=(
                    "La columna no pertenece "
                    "al contrato CAPEX."
                ),
                severity=(
                    CapexIssueSeverity.WARNING
                ),
                raw_value=(
                    normalized[header]
                ),
            )
        )

    for column in (
        CAPEX_STRING_COLUMNS
    ):
        value = _raw_value(
            normalized,
            column,
        )

        if (
            column
            in CAPEX_NULLABLE_TEXT_COLUMNS
            and is_excel_error_token(
                value
            )
        ):
            cleaned[column] = None

            issues.append(
                _issue(
                    row_number=row_number,
                    column=column,
                    code=(
                        "NULLABLE_TEXT_NORMALIZED"
                    ),
                    message=(
                        "El error de Excel fue "
                        "normalizado a NULL porque "
                        "la columna permite valores "
                        "vac?os."
                    ),
                    severity=(
                        CapexIssueSeverity.INFO
                    ),
                    raw_value=value,
                )
            )

            continue

        try:
            cleaned[column] = (
                clean_capex_text(
                    value,
                    collapse_whitespace=(
                        column
                        not in
                        CAPEX_FREE_TEXT_COLUMNS
                    ),
                )
            )

        except CapexCleaningError as exc:
            cleaned[column] = None

            issues.append(
                _issue(
                    row_number=row_number,
                    column=column,
                    code="INVALID_TEXT",
                    message=str(exc),
                    severity=(
                        CapexIssueSeverity.ERROR
                    ),
                    raw_value=value,
                )
            )

    for column in (
        CAPEX_INTEGER_COLUMNS
    ):
        value = _raw_value(
            normalized,
            column,
        )

        try:
            cleaned[column] = (
                clean_capex_integer(
                    value
                )
            )

        except CapexCleaningError as exc:
            cleaned[column] = None

            issues.append(
                _issue(
                    row_number=row_number,
                    column=column,
                    code="INVALID_INTEGER",
                    message=str(exc),
                    severity=(
                        CapexIssueSeverity.ERROR
                    ),
                    raw_value=value,
                )
            )

    if cleaned.get("anio") is None:
        issues.append(
            _issue(
                row_number=row_number,
                column="anio",
                code="YEAR_REQUIRED",
                message=(
                    "El anio es obligatorio."
                ),
                severity=(
                    CapexIssueSeverity.ERROR
                ),
                raw_value=_raw_value(
                    normalized,
                    "anio",
                ),
            )
        )

    elif (
        expected_year is not None
        and cleaned["anio"]
        != expected_year
    ):
        issues.append(
            _issue(
                row_number=row_number,
                column="anio",
                code="YEAR_MISMATCH",
                message=(
                    "El anio no corresponde "
                    f"al periodo esperado "
                    f"{expected_year}."
                ),
                severity=(
                    CapexIssueSeverity.ERROR
                ),
                raw_value=_raw_value(
                    normalized,
                    "anio",
                ),
            )
        )

    raw_quantity = _raw_value(
        normalized,
        "cantidad",
    )

    if cleaned.get("cantidad") is None:
        if is_blank_like(
            raw_quantity
        ):
            cleaned["cantidad"] = 1

            issues.append(
                _issue(
                    row_number=row_number,
                    column="cantidad",
                    code="QUANTITY_DEFAULTED",
                    message=(
                        "Cantidad estaba vacia "
                        "y se asigno 1 "
                        "automaticamente."
                    ),
                    severity=(
                        CapexIssueSeverity.INFO
                    ),
                    raw_value=(
                        raw_quantity
                    ),
                )
            )

    elif cleaned["cantidad"] < 0:
        issues.append(
            _issue(
                row_number=row_number,
                column="cantidad",
                code="NEGATIVE_QUANTITY",
                message=(
                    "Cantidad no puede ser "
                    "negativa."
                ),
                severity=(
                    CapexIssueSeverity.ERROR
                ),
                raw_value=(
                    raw_quantity
                ),
            )
        )

    amount_parse_ok = {}

    for column in (
        CAPEX_AMOUNT_COLUMNS
    ):
        value = _raw_value(
            normalized,
            column,
        )

        try:
            cleaned[column] = (
                clean_capex_amount(
                    value
                )
            )

            amount_parse_ok[
                column
            ] = True

        except CapexCleaningError as exc:
            cleaned[column] = ZERO

            amount_parse_ok[
                column
            ] = False

            issues.append(
                _issue(
                    row_number=row_number,
                    column=column,
                    code="INVALID_AMOUNT",
                    message=str(exc),
                    severity=(
                        CapexIssueSeverity.ERROR
                    ),
                    raw_value=value,
                )
            )

    _validate_total(
        normalized=normalized,
        cleaned=cleaned,
        amount_parse_ok=(
            amount_parse_ok
        ),
        month_columns=(
            CAPEX_ML_MONTH_COLUMNS
        ),
        total_column=(
            CAPEX_ML_TOTAL_COLUMN
        ),
        row_number=row_number,
        issues=issues,
    )

    _validate_total(
        normalized=normalized,
        cleaned=cleaned,
        amount_parse_ok=(
            amount_parse_ok
        ),
        month_columns=(
            CAPEX_USD_MONTH_COLUMNS
        ),
        total_column=(
            CAPEX_USD_TOTAL_COLUMN
        ),
        row_number=row_number,
        issues=issues,
    )

    return CapexCleanRowResult(
        row=cleaned,
        issues=tuple(
            issues
        ),
    )


def _validate_total(
    *,
    normalized,
    cleaned,
    amount_parse_ok,
    month_columns,
    total_column,
    row_number,
    issues,
):
    calculated = sum(
        (
            cleaned[column]
            for column
            in month_columns
        ),
        ZERO,
    )

    calculated = (
        calculated
        .quantize(
            BIGQUERY_NUMERIC_QUANTUM
        )
    )

    raw_total = _raw_value(
        normalized,
        total_column,
    )

    total_was_blank = (
        is_blank_like(
            raw_total
        )
    )

    parsed_total = (
        cleaned[
            total_column
        ]
    )

    total_parse_ok = (
        amount_parse_ok[
            total_column
        ]
    )

    cleaned[
        total_column
    ] = calculated

    if total_was_blank:
        issues.append(
            _issue(
                row_number=row_number,
                column=total_column,
                code="TOTAL_CALCULATED",
                message=(
                    "El total estaba vacio "
                    "y fue calculado desde "
                    "los 12 meses."
                ),
                severity=(
                    CapexIssueSeverity.WARNING
                ),
                raw_value=raw_total,
            )
        )

        return

    if not total_parse_ok:
        return

    difference = abs(
        parsed_total
        - calculated
    )

    if (
        difference
        <= TOTAL_NOISE_TOLERANCE
    ):
        return

    if (
        difference
        > TOTAL_TOLERANCE
    ):
        issues.append(
            _issue(
                row_number=row_number,
                column=total_column,
                code="TOTAL_MISMATCH",
                message=(
                    "El total informado no "
                    "coincide con la suma "
                    "de los 12 meses. "
                    f"Archivo={parsed_total}; "
                    f"calculado={calculated}; "
                    f"diferencia={difference}."
                ),
                severity=(
                    CapexIssueSeverity.ERROR
                ),
                raw_value=raw_total,
            )
        )

        return

    if difference != ZERO:
        issues.append(
            _issue(
                row_number=row_number,
                column=total_column,
                code=(
                    "TOTAL_ROUNDING_DIFFERENCE"
                ),
                message=(
                    "Existe una diferencia "
                    "menor o igual a un centavo "
                    "entre el total informado "
                    "y la suma de los meses. "
                    f"Archivo={parsed_total}; "
                    f"calculado={calculated}; "
                    f"diferencia={difference}."
                ),
                severity=(
                    CapexIssueSeverity.WARNING
                ),
                raw_value=raw_total,
            )
        )
