
from decimal import (
    Decimal,
    InvalidOperation,
)

from app.models.sharepoint_summary_sync import (
    SharePointDesiredItem,
)


class SharePointSummaryMappingError(
    RuntimeError
):
    pass


class SharePointSummaryMapper:
    def __init__(
        self,
        *,
        field_mapping,
        compare_fields,
        title_source,
        module=None,
    ):
        self._field_mapping = dict(
            field_mapping
        )

        self._compare_fields = tuple(
            compare_fields
        )

        self._title_source = str(
            title_source
        ).strip()

        self._module = (
            str(module).strip().upper()
            if module is not None
            else None
        )

        if not self._title_source:
            raise ValueError(
                "title_source no puede "
                "estar vacio."
            )

        if (
            "Modulo"
            in self._compare_fields
            and not self._module
        ):
            raise ValueError(
                "module es obligatorio "
                "cuando Modulo forma parte "
                "del contrato SharePoint."
            )

    def map_result(
        self,
        summary_result,
    ) -> tuple[
        SharePointDesiredItem,
        ...
    ]:
        result = []

        keys = set()

        for row in (
            summary_result.rows
        ):
            item = (
                self.map_row(
                    row
                )
            )

            if (
                item.summary_key
                in keys
            ):
                raise (
                    SharePointSummaryMappingError(
                        "SummaryKey duplicada "
                        "en el resumen deseado: "
                        f"{item.summary_key}"
                    )
                )

            keys.add(
                item.summary_key
            )

            result.append(
                item
            )

        return tuple(
            result
        )

    def map_row(
        self,
        row,
    ) -> SharePointDesiredItem:
        source = (
            row.as_dict()
        )

        summary_key = str(
            source.get(
                "summary_key",
                "",
            )
            or ""
        ).strip()

        if not summary_key:
            raise (
                SharePointSummaryMappingError(
                    "El resumen no contiene "
                    "SummaryKey."
                )
            )

        title = self._text(
            source.get(
                self._title_source
            ),
            self._title_source,
            max_length=255,
        )

        fields = {
            "Title":
                title,
        }

        if (
            "Modulo"
            in self._compare_fields
        ):
            fields[
                "Modulo"
            ] = self._module

        for (
            sharepoint_field,
            source_field,
        ) in self._field_mapping.items():

            value = source.get(
                source_field
            )

            if (
                sharepoint_field
                == "SummaryKey"
            ):
                fields[
                    sharepoint_field
                ] = summary_key

            elif (
                sharepoint_field
                == "TotalUSD"
            ):
                decimal_value = (
                    self._decimal(
                        value,
                        source_field,
                    )
                )

                fields[
                    sharepoint_field
                ] = float(
                    decimal_value
                    .quantize(
                        Decimal(
                            "0.01"
                        )
                    )
                )

            elif (
                sharepoint_field
                == "RegistrosOrigen"
            ):
                fields[
                    sharepoint_field
                ] = self._positive_int(
                    value,
                    source_field,
                )

            else:
                fields[
                    sharepoint_field
                ] = self._nullable_text(
                    value,
                    source_field,
                    max_length=255,
                )

        missing = [
            field
            for field
            in self._compare_fields
            if field not in fields
        ]

        if missing:
            raise (
                SharePointSummaryMappingError(
                    "Faltan campos SharePoint "
                    "en el mapper: "
                    + ", ".join(
                        missing
                    )
                )
            )

        ordered_fields = tuple(
            (
                field,
                fields[field],
            )
            for field
            in self._compare_fields
        )

        return (
            SharePointDesiredItem(
                summary_key=(
                    summary_key
                ),
                fields=(
                    ordered_fields
                ),
            )
        )

    @staticmethod
    def _text(
        value,
        field_name,
        *,
        max_length,
    ) -> str:
        text = str(
            value
            if value is not None
            else ""
        ).strip()

        if not text:
            raise (
                SharePointSummaryMappingError(
                    f"{field_name} no puede "
                    "estar vacio."
                )
            )

        if len(text) > max_length:
            raise (
                SharePointSummaryMappingError(
                    f"{field_name} supera "
                    f"{max_length} caracteres."
                )
            )

        return text

    @staticmethod
    def _nullable_text(
        value,
        field_name,
        *,
        max_length,
    ):
        if value is None:
            return None

        text = str(
            value
        ).strip()

        if not text:
            return None

        if len(text) > max_length:
            raise (
                SharePointSummaryMappingError(
                    f"{field_name} supera "
                    f"{max_length} caracteres."
                )
            )

        return text

    @staticmethod
    def _decimal(
        value,
        field_name,
    ) -> Decimal:
        if isinstance(
            value,
            bool,
        ):
            raise (
                SharePointSummaryMappingError(
                    f"{field_name} no puede "
                    "ser booleano."
                )
            )

        try:
            result = Decimal(
                str(
                    value
                    if value is not None
                    else "0"
                )
            )

        except (
            InvalidOperation,
            ValueError,
            TypeError,
        ) as exc:
            raise (
                SharePointSummaryMappingError(
                    f"{field_name} no contiene "
                    "un numero valido."
                )
            ) from exc

        if not result.is_finite():
            raise (
                SharePointSummaryMappingError(
                    f"{field_name} no contiene "
                    "un numero finito."
                )
            )

        return result

    @staticmethod
    def _positive_int(
        value,
        field_name,
    ) -> int:
        if isinstance(
            value,
            bool,
        ):
            raise (
                SharePointSummaryMappingError(
                    f"{field_name} debe "
                    "ser entero."
                )
            )

        try:
            result = int(
                value
            )

        except (
            ValueError,
            TypeError,
        ) as exc:
            raise (
                SharePointSummaryMappingError(
                    f"{field_name} debe "
                    "ser entero."
                )
            ) from exc

        if result < 1:
            raise (
                SharePointSummaryMappingError(
                    f"{field_name} debe ser "
                    "mayor a cero."
                )
            )

        return result
