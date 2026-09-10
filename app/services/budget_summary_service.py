
import hashlib
import json
from datetime import (
    date,
    datetime,
)
from decimal import (
    Decimal,
    InvalidOperation,
)


ZERO = Decimal("0")


class BudgetSummaryError(
    RuntimeError
):
    pass


class BudgetSummaryIntegrityError(
    BudgetSummaryError
):
    pass


class BudgetSummaryService:
    def __init__(
        self,
        repository,
    ):
        self._repository = (
            repository
        )

    def build(
        self,
        definition,
    ):
        from app.models.budget_summary import (
            BudgetSummaryResult,
            BudgetSummaryRow,
        )

        raw_rows = (
            self._repository
            .get_summary_rows(
                definition
            )
        )

        if not raw_rows:
            return (
                BudgetSummaryResult(
                    definition=definition,
                    rows=(),
                    source_row_count=0,
                    source_total_usd=ZERO,
                )
            )

        source_row_count = (
            self._required_non_negative_int(
                raw_rows[0].get(
                    "_source_row_count"
                ),
                "_source_row_count",
            )
        )

        source_total_usd = (
            self._decimal(
                raw_rows[0].get(
                    "_source_total_usd"
                ),
                "_source_total_usd",
            )
        )

        result_rows = []

        seen_keys = set()

        for index, raw in enumerate(
            raw_rows,
            start=1,
        ):
            current_source_rows = (
                self._required_non_negative_int(
                    raw.get(
                        "_source_row_count"
                    ),
                    "_source_row_count",
                )
            )

            current_source_total = (
                self._decimal(
                    raw.get(
                        "_source_total_usd"
                    ),
                    "_source_total_usd",
                )
            )

            if (
                current_source_rows
                != source_row_count
                or
                current_source_total
                != source_total_usd
            ):
                raise (
                    BudgetSummaryIntegrityError(
                        "BigQuery devolvio "
                        "controles globales "
                        "inconsistentes."
                    )
                )

            registros_origen = (
                self._required_positive_int(
                    raw.get(
                        "registros_origen"
                    ),
                    (
                        "registros_origen "
                        f"fila {index}"
                    ),
                )
            )

            total_usd = (
                self._decimal(
                    raw.get(
                        "total_usd"
                    ),
                    (
                        "total_usd "
                        f"fila {index}"
                    ),
                )
            )

            dimensions = tuple(
                (
                    column,
                    raw.get(
                        column
                    ),
                )
                for column
                in definition.group_by
            )

            summary_key = (
                self.build_summary_key(
                    definition,
                    dimensions,
                )
            )

            if summary_key in seen_keys:
                raise (
                    BudgetSummaryIntegrityError(
                        "Se genero una "
                        "summary_key duplicada."
                    )
                )

            seen_keys.add(
                summary_key
            )

            result_rows.append(
                BudgetSummaryRow(
                    summary_key=(
                        summary_key
                    ),
                    dimensions=(
                        dimensions
                    ),
                    registros_origen=(
                        registros_origen
                    ),
                    total_usd=(
                        total_usd
                    ),
                )
            )

        result = (
            BudgetSummaryResult(
                definition=definition,
                rows=tuple(
                    result_rows
                ),
                source_row_count=(
                    source_row_count
                ),
                source_total_usd=(
                    source_total_usd
                ),
            )
        )

        if not result.rows_balanced:
            raise (
                BudgetSummaryIntegrityError(
                    "El total de registros "
                    "del resumen no coincide "
                    "con el origen. "
                    f"Origen="
                    f"{result.source_row_count}, "
                    f"Resumen="
                    f"{result.summarized_row_count}."
                )
            )

        if not result.amounts_balanced:
            raise (
                BudgetSummaryIntegrityError(
                    "El total USD del resumen "
                    "no coincide con BigQuery. "
                    f"Diferencia="
                    f"{result.difference_usd}."
                )
            )

        return result

    @classmethod
    def build_summary_key(
        cls,
        definition,
        dimensions,
    ) -> str:
        payload = {
            "module":
                str(
                    definition.module
                ).strip().upper(),
            "summary":
                str(
                    definition.name
                ).strip(),
            "dimensions": [
                [
                    str(column),
                    cls._canonical_value(
                        value
                    ),
                ]
                for column, value
                in dimensions
            ],
        }

        encoded = (
            json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(
                    ",",
                    ":",
                ),
            )
            .encode(
                "utf-8"
            )
        )

        return (
            hashlib
            .sha256(
                encoded
            )
            .hexdigest()
        )

    @staticmethod
    def _canonical_value(
        value,
    ):
        if value is None:
            return None

        if isinstance(
            value,
            Decimal,
        ):
            return format(
                value,
                "f",
            )

        if isinstance(
            value,
            (
                datetime,
                date,
            ),
        ):
            return (
                value.isoformat()
            )

        if isinstance(
            value,
            str,
        ):
            clean = value.strip()

            return (
                clean
                if clean
                else None
            )

        if isinstance(
            value,
            (
                bool,
                int,
                float,
            ),
        ):
            return value

        return str(
            value
        )

    @staticmethod
    def _decimal(
        value,
        field_name,
    ) -> Decimal:
        if value is None:
            return ZERO

        if isinstance(
            value,
            bool,
        ):
            raise (
                BudgetSummaryIntegrityError(
                    f"{field_name} no puede "
                    "ser booleano."
                )
            )

        if isinstance(
            value,
            Decimal,
        ):
            return value

        try:
            return Decimal(
                str(value)
            )

        except (
            InvalidOperation,
            TypeError,
            ValueError,
        ) as exc:
            raise (
                BudgetSummaryIntegrityError(
                    f"{field_name} no contiene "
                    "un valor numerico valido."
                )
            ) from exc

    @staticmethod
    def _required_non_negative_int(
        value,
        field_name,
    ) -> int:
        if (
            isinstance(
                value,
                bool,
            )
        ):
            raise (
                BudgetSummaryIntegrityError(
                    f"{field_name} debe "
                    "ser entero."
                )
            )

        try:
            result = int(
                value
            )

        except (
            TypeError,
            ValueError,
        ) as exc:
            raise (
                BudgetSummaryIntegrityError(
                    f"{field_name} debe "
                    "ser entero."
                )
            ) from exc

        if result < 0:
            raise (
                BudgetSummaryIntegrityError(
                    f"{field_name} no puede "
                    "ser negativo."
                )
            )

        return result

    @classmethod
    def _required_positive_int(
        cls,
        value,
        field_name,
    ) -> int:
        result = (
            cls
            ._required_non_negative_int(
                value,
                field_name,
            )
        )

        if result < 1:
            raise (
                BudgetSummaryIntegrityError(
                    f"{field_name} debe "
                    "ser mayor a cero."
                )
            )

        return result
