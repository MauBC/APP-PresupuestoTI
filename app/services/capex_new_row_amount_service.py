from copy import deepcopy

from app.config.budget_module_config import (
    BudgetModule,
)
from app.config.capex_schema import (
    CAPEX_EXPECTED_YEAR,
    CAPEX_ML_MONTH_COLUMNS,
    CAPEX_ML_TOTAL_COLUMN,
    CAPEX_USD_MONTH_COLUMNS,
    CAPEX_USD_TOTAL_COLUMN,
)
from app.models.new_budget_row import (
    NewBudgetRowDraft,
)
from app.services.capex_cleaner import (
    BIGQUERY_NUMERIC_QUANTUM,
    CapexCleaningError,
    clean_capex_amount,
)


class CapexNewRowAmountError(
    ValueError
):
    pass


class CapexNewRowAmountService:
    def apply(
        self,
        draft: NewBudgetRowDraft,
        *,
        ml_values,
        usd_values,
    ) -> NewBudgetRowDraft:
        if (
            draft.module
            != BudgetModule.CAPEX.value
        ):
            raise CapexNewRowAmountError(
                "El draft debe pertenecer "
                "a CAPEX."
            )

        row = deepcopy(
            draft.row
        )

        self._validate_dimensions(
            row
        )

        ml = self._clean_family(
            ml_values,
            CAPEX_ML_MONTH_COLUMNS,
            label="ML",
        )

        usd = self._clean_family(
            usd_values,
            CAPEX_USD_MONTH_COLUMNS,
            label="USD",
        )

        for column, value in ml.items():
            row[column] = value

        for column, value in usd.items():
            row[column] = value

        row[
            CAPEX_ML_TOTAL_COLUMN
        ] = self._sum_family(
            ml
        )

        row[
            CAPEX_USD_TOTAL_COLUMN
        ] = self._sum_family(
            usd
        )

        return NewBudgetRowDraft(
            module=draft.module,
            row=row,
        )

    @staticmethod
    def _validate_dimensions(
        row,
    ):
        year = row.get(
            "anio"
        )

        if year != CAPEX_EXPECTED_YEAR:
            raise CapexNewRowAmountError(
                "El anio CAPEX debe ser "
                f"{CAPEX_EXPECTED_YEAR}."
            )

        quantity = row.get(
            "cantidad"
        )

        if (
            isinstance(
                quantity,
                bool,
            )
            or not isinstance(
                quantity,
                int,
            )
        ):
            raise CapexNewRowAmountError(
                "Cantidad debe ser "
                "un numero entero."
            )

        if quantity < 0:
            raise CapexNewRowAmountError(
                "Cantidad no puede ser "
                "negativa."
            )

    @staticmethod
    def _clean_family(
        supplied,
        expected_columns,
        *,
        label,
    ):
        try:
            values = dict(
                supplied
            )
        except Exception as exc:
            raise (
                CapexNewRowAmountError(
                    f"Los importes {label} "
                    "no tienen un formato "
                    "valido."
                )
            ) from exc

        expected = set(
            expected_columns
        )

        received = set(
            values
        )

        missing = sorted(
            expected
            - received
        )

        extra = sorted(
            received
            - expected
        )

        if missing:
            raise CapexNewRowAmountError(
                f"Faltan meses {label}: "
                + ", ".join(
                    missing
                )
            )

        if extra:
            raise CapexNewRowAmountError(
                f"Meses {label} no validos: "
                + ", ".join(
                    extra
                )
            )

        cleaned = {}

        for column in (
            expected_columns
        ):
            try:
                cleaned[
                    column
                ] = clean_capex_amount(
                    values[column]
                )

            except (
                CapexCleaningError
            ) as exc:
                raise (
                    CapexNewRowAmountError(
                        f"{label} / "
                        f"{column}: "
                        f"{exc}"
                    )
                ) from exc

        return cleaned

    @staticmethod
    def _sum_family(
        values,
    ):
        return sum(
            values.values()
        ).quantize(
            BIGQUERY_NUMERIC_QUANTUM
        )
