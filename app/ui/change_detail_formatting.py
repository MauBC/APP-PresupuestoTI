from decimal import (
    Decimal,
    InvalidOperation,
)


ACRONYMS = {
    "cebe": "CEBE",
    "ceco": "CECO",
    "gyp": "GYP",
    "mf": "MF",
    "ml": "ML",
    "ti": "TI",
    "usd": "USD",
    "vp": "VP",
}


def change_amount_unit(
    column,
) -> str | None:
    normalized = str(
        column or ""
    ).strip().lower()

    normalized = (
        normalized
        .replace(" ", "_")
        .replace("-", "_")
    )

    tokens = tuple(
        token
        for token
        in normalized.split("_")
        if token
    )

    # Habilitar/deshabilitar usa como impacto
    # el total anual USD de la fila.
    if normalized == "habilitado":
        return "US$"

    if (
        "usd" in tokens
        or normalized.endswith("usd")
    ):
        return "US$"

    if (
        "ml" in tokens
        or normalized.endswith("ml")
    ):
        return "ML"

    if (
        "mf" in tokens
        or normalized.endswith("mf")
    ):
        return "MF"

    return None


def change_field_label(
    column,
) -> str:
    if column == "habilitado":
        return "Estado"

    parts = [
        part
        for part
        in str(
            column or ""
        )
        .strip()
        .split("_")
        if part
    ]

    if not parts:
        return ""

    if parts[0].lower() in (
        "anio",
        "ano",
        "annual",
    ):
        parts = [
            "total",
            "anual",
            *parts[1:],
        ]

    result = []

    for part in parts:
        normalized = (
            part.lower()
        )

        if normalized in ACRONYMS:
            result.append(
                ACRONYMS[
                    normalized
                ]
            )
        else:
            result.append(
                part.capitalize()
            )

    return " ".join(
        result
    )


def _decimal_value(
    value,
) -> Decimal | None:
    if isinstance(
        value,
        bool,
    ):
        return None

    if isinstance(
        value,
        Decimal,
    ):
        return value

    if isinstance(
        value,
        (int, float),
    ):
        try:
            return Decimal(
                str(value)
            )
        except (
            InvalidOperation,
            ValueError,
            TypeError,
        ):
            return None

    return None


def format_change_value(
    column,
    value,
) -> str:
    if value is None:
        return ""

    if isinstance(
        value,
        bool,
    ):
        return (
            "Habilitado"
            if value
            else "Deshabilitado"
        )

    unit = change_amount_unit(
        column
    )

    decimal_value = (
        _decimal_value(
            value
        )
    )

    if (
        unit is not None
        and decimal_value is not None
    ):
        return (
            f"{unit} "
            f"{decimal_value:,.2f}"
        )

    return str(
        value
    )


def format_change_difference(
    column,
    value,
) -> str:
    if value is None:
        return "-"

    decimal_value = (
        _decimal_value(
            value
        )
    )

    if decimal_value is None:
        return str(
            value
        )

    unit = change_amount_unit(
        column
    )

    absolute = abs(
        decimal_value
    )

    if unit is not None:
        amount = (
            f"{unit} "
            f"{absolute:,.2f}"
        )
    else:
        amount = (
            f"{absolute:,.2f}"
        )

    if decimal_value > 0:
        return (
            f"+{amount}"
        )

    if decimal_value < 0:
        return (
            f"-{amount}"
        )

    if unit is not None:
        return (
            f"{unit} 0.00"
        )

    return "0.00"
