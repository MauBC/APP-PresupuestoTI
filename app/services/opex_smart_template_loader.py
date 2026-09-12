from decimal import (
    Decimal,
    InvalidOperation,
)
from pathlib import Path
import re
import unicodedata

import pandas as pd

from app.models.opex_smart_template import (
    OpexSmartTemplateWorkbook,
    OpexTemplateBudget,
    OpexTemplateDistribution,
)


ZERO = Decimal("0")
ONE = Decimal("1")


class OpexSmartTemplateError(
    ValueError
):
    pass


_METADATA_FIELDS = {
    "NOMBRE DEL GASTO":
        "nombre_gasto",

    "PROVEEDOR":
        "proveedor",

    "MONEDA DE FACTURACION":
        "moneda_facturacion",

    "NUMERO DE CUENTA":
        "numero_cuenta",

    "TIPO":
        "tipo",

    "MONTO":
        "monto",
}


_DISTRIBUTION_FIELDS = {
    "CECOS":
        "ceco",

    "CECO":
        "ceco",

    "PORCENTAJE":
        "percentage",

    "IMPORTE":
        "amount",
}


_ALLOWED_TYPES = {
    "MENSUAL",
    "ANUAL",
}


def _normalized_label(
    value,
) -> str:
    if value is None:
        return ""

    text = str(
        value
    ).strip()

    if not text:
        return ""

    text = unicodedata.normalize(
        "NFKD",
        text,
    )

    text = "".join(
        char
        for char in text
        if not unicodedata.combining(
            char
        )
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.upper()


def _is_blank(
    value,
) -> bool:
    if value is None:
        return True

    if isinstance(
        value,
        str,
    ):
        return not value.strip()

    try:
        result = pd.isna(
            value
        )

        return bool(
            result
        )

    except (
        TypeError,
        ValueError,
    ):
        return False


def _text(
    value,
    *,
    field,
    sheet,
) -> str:
    if _is_blank(
        value
    ):
        raise OpexSmartTemplateError(
            f"{sheet}: {field} "
            "no puede estar vacio."
        )

    return str(
        value
    ).strip()


def _code_text(
    value,
    *,
    field,
    sheet,
) -> str:
    if _is_blank(
        value
    ):
        raise OpexSmartTemplateError(
            f"{sheet}: {field} "
            "no puede estar vacio."
        )

    if isinstance(
        value,
        bool,
    ):
        raise OpexSmartTemplateError(
            f"{sheet}: {field} "
            "no tiene un codigo valido."
        )

    if isinstance(
        value,
        int,
    ):
        return str(
            value
        )

    if isinstance(
        value,
        float,
    ):
        if value.is_integer():
            return str(
                int(
                    value
                )
            )

        return str(
            value
        ).strip()

    text = str(
        value
    ).strip()

    if (
        text.endswith(
            ".0"
        )
        and
        text[:-2].isdigit()
    ):
        return text[:-2]

    return text


def _normalize_number_text(
    value,
) -> str:
    text = str(
        value
    ).strip()

    text = (
        text
        .replace(
            "US$",
            "",
        )
        .replace(
            "$",
            "",
        )
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


def _decimal(
    value,
    *,
    field,
    sheet,
    excel_row=None,
) -> Decimal:
    if _is_blank(
        value
    ):
        raise OpexSmartTemplateError(
            _location(
                sheet,
                excel_row,
            )
            + f": {field} "
            "no puede estar vacio."
        )

    if isinstance(
        value,
        bool,
    ):
        raise OpexSmartTemplateError(
            _location(
                sheet,
                excel_row,
            )
            + f": {field} "
            "debe ser numerico."
        )

    try:
        result = (
            value
            if isinstance(
                value,
                Decimal,
            )
            else Decimal(
                _normalize_number_text(
                    value
                )
            )
        )

    except (
        InvalidOperation,
        TypeError,
        ValueError,
    ) as exc:
        raise OpexSmartTemplateError(
            _location(
                sheet,
                excel_row,
            )
            + f": {field} "
            "debe ser numerico."
        ) from exc

    if not result.is_finite():
        raise OpexSmartTemplateError(
            _location(
                sheet,
                excel_row,
            )
            + f": {field} "
            "debe ser finito."
        )

    return result


def _optional_decimal(
    value,
    *,
    field,
    sheet,
    excel_row,
) -> Decimal | None:
    if _is_blank(
        value
    ):
        return None

    return _decimal(
        value,
        field=field,
        sheet=sheet,
        excel_row=excel_row,
    )


def _percentage(
    value,
    *,
    sheet,
    excel_row,
) -> Decimal | None:
    if _is_blank(
        value
    ):
        return None

    if (
        isinstance(
            value,
            str,
        )
        and
        value.strip().endswith(
            "%"
        )
    ):
        raw = value.strip()[:-1]

        percentage = (
            _decimal(
                raw,
                field="PORCENTAJE",
                sheet=sheet,
                excel_row=excel_row,
            )
            / Decimal(
                "100"
            )
        )

    else:
        percentage = (
            _decimal(
                value,
                field="PORCENTAJE",
                sheet=sheet,
                excel_row=excel_row,
            )
        )

    if (
        percentage < ZERO
        or percentage > ONE
    ):
        raise OpexSmartTemplateError(
            _location(
                sheet,
                excel_row,
            )
            + ": PORCENTAJE debe estar "
            "entre 0% y 100%. "
            "Si escribes 40%, usa formato "
            "porcentaje o el texto 40%."
        )

    return percentage


def _location(
    sheet,
    excel_row=None,
):
    if excel_row is None:
        return str(
            sheet
        )

    return (
        f"{sheet}, fila "
        f"{excel_row}"
    )


class OpexSmartTemplateLoader:
    def load(
        self,
        file_path,
    ) -> OpexSmartTemplateWorkbook:
        path = (
            Path(
                file_path
            )
            .expanduser()
            .resolve()
        )

        if not path.exists():
            raise OpexSmartTemplateError(
                f"No existe el archivo: {path}"
            )

        if (
            path.suffix.lower()
            not in {
                ".xlsx",
                ".xlsm",
            }
        ):
            raise OpexSmartTemplateError(
                "La plantilla inteligente OPEX "
                "debe ser XLSX o XLSM."
            )

        try:
            workbook = pd.ExcelFile(
                path
            )

        except Exception as exc:
            raise OpexSmartTemplateError(
                "No se pudo abrir la plantilla "
                f"OPEX: {exc}"
            ) from exc

        if not workbook.sheet_names:
            raise OpexSmartTemplateError(
                "El Excel no contiene hojas."
            )

        budgets = []

        for sheet_name in (
            workbook.sheet_names
        ):
            dataframe = pd.read_excel(
                workbook,
                sheet_name=sheet_name,
                header=None,
                dtype=object,
                keep_default_na=False,
            )

            budgets.append(
                self._parse_sheet(
                    sheet_name,
                    dataframe,
                )
            )

        return OpexSmartTemplateWorkbook(
            source_path=str(
                path
            ),
            budgets=tuple(
                budgets
            ),
        )

    def _parse_sheet(
        self,
        sheet_name,
        dataframe,
    ) -> OpexTemplateBudget:
        if len(
            dataframe
        ) < 8:
            raise OpexSmartTemplateError(
                f"{sheet_name}: la hoja debe "
                "contener las 6 filas de "
                "cabecera, encabezados de "
                "distribucion y al menos "
                "un CECO."
            )

        metadata = (
            self._read_metadata(
                sheet_name,
                dataframe,
            )
        )

        columns = (
            self._read_distribution_headers(
                sheet_name,
                dataframe,
            )
        )

        distributions = (
            self._read_distributions(
                sheet_name,
                dataframe,
                columns,
            )
        )

        tipo = str(
            metadata["tipo"]
        ).strip().upper()

        if tipo not in _ALLOWED_TYPES:
            raise OpexSmartTemplateError(
                f"{sheet_name}: TIPO debe ser "
                "MENSUAL o ANUAL. "
                f"Valor recibido: {tipo!r}."
            )

        monto = _decimal(
            metadata["monto"],
            field="MONTO",
            sheet=sheet_name,
        )

        if monto < ZERO:
            raise OpexSmartTemplateError(
                f"{sheet_name}: MONTO no puede "
                "ser negativo."
            )

        return OpexTemplateBudget(
            sheet_name=sheet_name,

            nombre_gasto=_text(
                metadata[
                    "nombre_gasto"
                ],
                field="Nombre del Gasto",
                sheet=sheet_name,
            ),

            proveedor=_text(
                metadata[
                    "proveedor"
                ],
                field="Proveedor",
                sheet=sheet_name,
            ),

            moneda_facturacion=_text(
                metadata[
                    "moneda_facturacion"
                ],
                field=(
                    "Moneda de Facturacion"
                ),
                sheet=sheet_name,
            ).upper(),

            numero_cuenta=_code_text(
                metadata[
                    "numero_cuenta"
                ],
                field="Numero de cuenta",
                sheet=sheet_name,
            ),

            tipo=tipo,
            monto=monto,

            distributions=(
                distributions
            ),
        )

    def _read_metadata(
        self,
        sheet_name,
        dataframe,
    ):
        result = {}

        for index in range(
            min(
                6,
                len(
                    dataframe
                ),
            )
        ):
            label = (
                _normalized_label(
                    dataframe.iat[
                        index,
                        0,
                    ]
                )
            )

            if not label:
                continue

            field = (
                _METADATA_FIELDS.get(
                    label
                )
            )

            if field is None:
                raise OpexSmartTemplateError(
                    f"{sheet_name}, fila "
                    f"{index + 1}: campo de "
                    "cabecera no reconocido: "
                    f"{label!r}."
                )

            if field in result:
                raise OpexSmartTemplateError(
                    f"{sheet_name}: campo "
                    f"duplicado: {label}."
                )

            result[
                field
            ] = dataframe.iat[
                index,
                1,
            ]

        missing = sorted(
            set(
                _METADATA_FIELDS.values()
            )
            - set(
                result
            )
        )

        if missing:
            raise OpexSmartTemplateError(
                f"{sheet_name}: faltan campos "
                "obligatorios de cabecera: "
                + ", ".join(
                    missing
                )
            )

        return result

    def _read_distribution_headers(
        self,
        sheet_name,
        dataframe,
    ):
        header_row = 6

        result = {}

        for column_index in range(
            dataframe.shape[
                1
            ]
        ):
            label = (
                _normalized_label(
                    dataframe.iat[
                        header_row,
                        column_index,
                    ]
                )
            )

            if not label:
                continue

            field = (
                _DISTRIBUTION_FIELDS.get(
                    label
                )
            )

            if field is None:
                raise OpexSmartTemplateError(
                    f"{sheet_name}, fila 7: "
                    "columna de distribucion "
                    "no reconocida: "
                    f"{label!r}."
                )

            if field in result:
                raise OpexSmartTemplateError(
                    f"{sheet_name}: columna "
                    f"duplicada: {label}."
                )

            result[
                field
            ] = column_index

        if "ceco" not in result:
            raise OpexSmartTemplateError(
                f"{sheet_name}: fila 7 debe "
                "contener CECOS."
            )

        if not (
            "percentage" in result
            or "amount" in result
        ):
            raise OpexSmartTemplateError(
                f"{sheet_name}: la distribucion "
                "debe tener PORCENTAJE, "
                "IMPORTE o ambos."
            )

        return result

    def _read_distributions(
        self,
        sheet_name,
        dataframe,
        columns,
    ):
        rows = []
        seen_cecos = set()

        for index in range(
            7,
            len(
                dataframe
            ),
        ):
            excel_row = (
                index
                + 1
            )

            ceco_value = (
                dataframe.iat[
                    index,
                    columns["ceco"],
                ]
            )

            percentage_value = (
                dataframe.iat[
                    index,
                    columns["percentage"],
                ]
                if "percentage"
                in columns
                else None
            )

            amount_value = (
                dataframe.iat[
                    index,
                    columns["amount"],
                ]
                if "amount"
                in columns
                else None
            )

            if (
                _is_blank(
                    ceco_value
                )
                and
                _is_blank(
                    percentage_value
                )
                and
                _is_blank(
                    amount_value
                )
            ):
                continue

            ceco = _code_text(
                ceco_value,
                field="CECO",
                sheet=_location(
                    sheet_name,
                    excel_row,
                ),
            )

            if ceco in seen_cecos:
                raise OpexSmartTemplateError(
                    f"{sheet_name}, fila "
                    f"{excel_row}: CECO repetido "
                    f"dentro del mismo "
                    f"presupuesto: {ceco}."
                )

            percentage = _percentage(
                percentage_value,
                sheet=sheet_name,
                excel_row=excel_row,
            )

            amount = (
                _optional_decimal(
                    amount_value,
                    field="IMPORTE",
                    sheet=sheet_name,
                    excel_row=excel_row,
                )
            )

            if (
                amount is not None
                and amount < ZERO
            ):
                raise OpexSmartTemplateError(
                    f"{sheet_name}, fila "
                    f"{excel_row}: IMPORTE "
                    "no puede ser negativo."
                )

            if (
                percentage is None
                and amount is None
            ):
                raise OpexSmartTemplateError(
                    f"{sheet_name}, fila "
                    f"{excel_row}: el CECO "
                    f"{ceco} no tiene "
                    "PORCENTAJE ni IMPORTE."
                )

            seen_cecos.add(
                ceco
            )

            rows.append(
                OpexTemplateDistribution(
                    excel_row=excel_row,
                    ceco=ceco,
                    percentage=percentage,
                    amount=amount,
                )
            )

        if not rows:
            raise OpexSmartTemplateError(
                f"{sheet_name}: no se "
                "encontraron CECOs."
            )

        return tuple(
            rows
        )
