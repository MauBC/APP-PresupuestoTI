from decimal import (
    Decimal,
    InvalidOperation,
)

import pandas as pd

from app.config.presupuesto_schema import (
    AMOUNT_COLUMNS,
    LEGACY_EXPECTED_COLUMNS,
    STRING_COLUMNS,
)
from database.bootstrap.models import (
    CleaningIssue,
    CleaningResult,
    CleaningStats,
)


class CleaningError(ValueError):
    pass


def normalize_column_names(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    normalized = dataframe.copy()

    normalized.columns = [
        str(column)
        .strip()
        .lower()
        for column in normalized.columns
    ]

    return normalized


def validate_columns(
    dataframe: pd.DataFrame,
) -> tuple[str, ...]:
    actual_columns = set(
        dataframe.columns
    )

    expected_columns = set(
        LEGACY_EXPECTED_COLUMNS
    )

    missing = sorted(
        expected_columns
        - actual_columns
    )

    if missing:
        raise CleaningError(
            "Faltan columnas obligatorias: "
            + ", ".join(missing)
        )

    extra = sorted(
        actual_columns
        - expected_columns
    )

    return tuple(extra)


def clean_string(
    value,
):
    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (
        TypeError,
        ValueError,
    ):
        pass

    text = str(value).strip()

    if not text:
        return None

    if text.endswith(".0"):
        numeric_part = text[:-2]

        if numeric_part.isdigit():
            return numeric_part

    return text


def clean_amount(
    value,
):
    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (
        TypeError,
        ValueError,
    ):
        pass

    if isinstance(
        value,
        Decimal,
    ):
        return value

    text = str(value).strip()

    if text == "-":
        return Decimal("0")

    if not text:
        return None

    normalized = text.replace(
        ",",
        "",
    )

    try:
        return Decimal(
            normalized
        )
    except InvalidOperation as exc:
        raise ValueError(
            "Valor monetario invalido: "
            f"{value!r}"
        ) from exc


def clean_dataframe(
    dataframe: pd.DataFrame,
) -> CleaningResult:
    normalized = (
        normalize_column_names(
            dataframe
        )
    )

    extra_columns = (
        validate_columns(
            normalized
        )
    )

    cleaned = normalized[
        list(
            LEGACY_EXPECTED_COLUMNS
        )
    ].copy()

    for column in STRING_COLUMNS:
        cleaned[column] = (
            cleaned[column]
            .map(clean_string)
        )

    issues = []
    dash_count = 0
    empty_amount_count = 0
    amount_count = 0

    for column in AMOUNT_COLUMNS:
        cleaned_values = []

        for (
            excel_row_number,
            (_, value),
        ) in enumerate(
            cleaned[column].items(),
            start=2,
        ):
            raw_text = (
                ""
                if value is None
                else str(value).strip()
            )

            if raw_text == "-":
                dash_count += 1

            try:
                cleaned_value = (
                    clean_amount(value)
                )
            except ValueError as exc:
                issues.append(
                    CleaningIssue(
                        row_number=(
                            excel_row_number
                        ),
                        column=column,
                        value=value,
                        message=str(exc),
                    )
                )

                cleaned_value = None

            if cleaned_value is None:
                empty_amount_count += 1
            else:
                amount_count += 1

            cleaned_values.append(
                cleaned_value
            )

        cleaned[column] = (
            cleaned_values
        )

    stats = CleaningStats(
        row_count=len(cleaned),
        column_count=len(
            cleaned.columns
        ),
        amount_count=amount_count,
        dash_count=dash_count,
        empty_amount_count=(
            empty_amount_count
        ),
        error_count=len(issues),
    )

    return CleaningResult(
        dataframe=cleaned,
        issues=tuple(issues),
        extra_columns=extra_columns,
        stats=stats,
    )