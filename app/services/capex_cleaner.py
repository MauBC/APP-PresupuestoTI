from decimal import (
    Decimal,
    InvalidOperation,
    ROUND_HALF_UP,
)
import math
import unicodedata


BIGQUERY_NUMERIC_QUANTUM = Decimal(
    "0.000000001"
)

ZERO = Decimal(
    "0.000000000"
)


EXCEL_ERROR_TOKENS = {
    "#N/A",
    "#NA",
    "#VALUE!",
    "#REF!",
    "#DIV/0!",
    "#NAME?",
    "#NUM!",
    "#NULL!",
}


class CapexCleaningError(
    ValueError
):
    pass


def is_blank_like(
    value,
) -> bool:
    if value is None:
        return True

    if isinstance(
        value,
        float,
    ):
        try:
            if math.isnan(value):
                return True
        except TypeError:
            pass

    if isinstance(
        value,
        str,
    ):
        return (
            value.strip()
            in {
                "",
                "-",
            }
        )

    return False


def is_excel_error_token(
    value,
) -> bool:
    if not isinstance(
        value,
        str,
    ):
        return False

    token = (
        value
        .strip()
        .upper()
    )

    return (
        token
        in EXCEL_ERROR_TOKENS
    )


def _check_excel_error(
    value,
):
    if not is_excel_error_token(
        value
    ):
        return

    token = (
        str(value)
        .strip()
        .upper()
    )

    raise CapexCleaningError(
        "La celda contiene un "
        f"error de Excel: {token}"
    )


def clean_capex_text(
    value,
    *,
    collapse_whitespace: bool = True,
) -> str | None:
    if is_blank_like(value):
        return None

    _check_excel_error(
        value
    )

    text = unicodedata.normalize(
        "NFC",
        str(value),
    )

    text = (
        text
        .replace(
            "\r\n",
            "\n",
        )
        .replace(
            "\r",
            "\n",
        )
        .strip()
    )

    if not text:
        return None

    if collapse_whitespace:
        text = " ".join(
            text.split()
        )

    return text


def clean_capex_integer(
    value,
) -> int | None:
    if is_blank_like(value):
        return None

    _check_excel_error(
        value
    )

    if isinstance(
        value,
        bool,
    ):
        raise CapexCleaningError(
            "Se esperaba un entero."
        )

    try:
        number = Decimal(
            str(value).strip()
        )

    except (
        InvalidOperation,
        TypeError,
        ValueError,
    ) as exc:
        raise CapexCleaningError(
            "Se esperaba un entero."
        ) from exc

    if not number.is_finite():
        raise CapexCleaningError(
            "El entero no puede ser "
            "NaN o infinito."
        )

    integral = (
        number
        .to_integral_value()
    )

    if number != integral:
        raise CapexCleaningError(
            "Se esperaba un entero "
            "sin decimales."
        )

    return int(
        integral
    )


def _normalize_amount_text(
    value,
) -> str:
    text = (
        str(value)
        .strip()
        .replace(
            " ",
            "",
        )
    )

    if (
        "," in text
        and "." in text
    ):
        if (
            text.rfind(".")
            > text.rfind(",")
        ):
            text = text.replace(
                ",",
                "",
            )
        else:
            text = (
                text
                .replace(
                    ".",
                    "",
                )
                .replace(
                    ",",
                    ".",
                )
            )

    elif "," in text:
        text = text.replace(
            ",",
            ".",
        )

    return text


def clean_capex_amount(
    value,
) -> Decimal:
    if is_blank_like(value):
        return ZERO

    _check_excel_error(
        value
    )

    if isinstance(
        value,
        bool,
    ):
        raise CapexCleaningError(
            "Se esperaba un importe numerico."
        )

    try:
        if isinstance(
            value,
            Decimal,
        ):
            amount = value

        else:
            amount = Decimal(
                _normalize_amount_text(
                    value
                )
            )

    except (
        InvalidOperation,
        TypeError,
        ValueError,
    ) as exc:
        raise CapexCleaningError(
            "Se esperaba un importe numerico."
        ) from exc

    if not amount.is_finite():
        raise CapexCleaningError(
            "El importe no puede ser "
            "NaN o infinito."
        )

    if amount < ZERO:
        raise CapexCleaningError(
            "El importe no puede ser negativo."
        )

    return amount.quantize(
        BIGQUERY_NUMERIC_QUANTUM,
        rounding=ROUND_HALF_UP,
    )
