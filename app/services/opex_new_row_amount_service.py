from copy import deepcopy
from decimal import (
    Decimal,
    InvalidOperation,
    ROUND_HALF_UP,
)

from app.config.budget_module_config import (
    BudgetModule,
)
from app.config.presupuesto_schema import (
    AMOUNT_GROUPS,
    MONTHS,
)
from app.models.new_budget_row import (
    NewBudgetRowDraft,
)


CENT = Decimal("0.01")
ZERO = Decimal("0.00")


class OpexNewRowAmountError(
    ValueError
):
    pass


def clean_opex_new_row_amount(
    value,
) -> Decimal:
    if value is None:
        return ZERO

    if isinstance(
        value,
        str,
    ):
        text = value.strip()

        if not text:
            return ZERO

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

        value = text

    if isinstance(
        value,
        bool,
    ):
        raise OpexNewRowAmountError(
            "El importe debe ser numerico."
        )

    try:
        amount = (
            value
            if isinstance(
                value,
                Decimal,
            )
            else Decimal(
                str(value)
            )
        )

    except (
        InvalidOperation,
        TypeError,
        ValueError,
    ) as exc:
        raise OpexNewRowAmountError(
            "El importe debe ser numerico."
        ) from exc

    if not amount.is_finite():
        raise OpexNewRowAmountError(
            "El importe debe ser finito."
        )

    if amount < ZERO:
        raise OpexNewRowAmountError(
            "El importe no puede ser negativo."
        )

    return amount.quantize(
        CENT,
        rounding=ROUND_HALF_UP,
    )


class OpexNewRowAmountService:
    @staticmethod
    def month_columns():
        return tuple(
            f"{month}_{group}"
            for group in AMOUNT_GROUPS
            for month in MONTHS
        )

    @staticmethod
    def annual_column(
        group,
    ):
        return f"anio_{group}"

    def apply(
        self,
        draft: NewBudgetRowDraft,
        *,
        monthly_values,
    ) -> NewBudgetRowDraft:
        if (
            draft.module
            != BudgetModule.OPEX.value
        ):
            raise OpexNewRowAmountError(
                "El draft debe pertenecer "
                "a OPEX."
            )

        try:
            supplied = dict(
                monthly_values
            )

        except Exception as exc:
            raise OpexNewRowAmountError(
                "Los importes OPEX no tienen "
                "un formato valido."
            ) from exc

        expected_columns = (
            self.month_columns()
        )

        expected = set(
            expected_columns
        )

        received = set(
            supplied
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
            raise OpexNewRowAmountError(
                "Faltan importes mensuales OPEX: "
                + ", ".join(
                    missing
                )
            )

        if extra:
            raise OpexNewRowAmountError(
                "Importes OPEX no validos: "
                + ", ".join(
                    extra
                )
            )

        row = deepcopy(
            draft.row
        )

        for group in AMOUNT_GROUPS:
            group_total = ZERO

            for month in MONTHS:
                column = (
                    f"{month}_{group}"
                )

                try:
                    amount = (
                        clean_opex_new_row_amount(
                            supplied[column]
                        )
                    )

                except (
                    OpexNewRowAmountError
                ) as exc:
                    raise OpexNewRowAmountError(
                        f"{column}: {exc}"
                    ) from exc

                row[column] = amount
                group_total += amount

            row[
                self.annual_column(
                    group
                )
            ] = group_total.quantize(
                CENT,
                rounding=ROUND_HALF_UP,
            )

        return NewBudgetRowDraft(
            module=draft.module,
            row=row,
        )
