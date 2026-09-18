from copy import deepcopy
from decimal import (
    Decimal,
    InvalidOperation,
    ROUND_HALF_UP,
)

from app.config.budget_module_config import (
    BudgetModule,
    BudgetModuleConfig,
)
from app.config.presupuesto_schema import MONTHS


CENT = Decimal("0.01")
NUMERIC_QUANTUM = Decimal("0.000000001")
ZERO = Decimal("0")


class BudgetRowEditError(ValueError):
    pass


class BudgetRowEditService:
    def __init__(self, config: BudgetModuleConfig):
        self._config = config
        self._type_map = config.insert_type_map
        self._quantum = (
            CENT
            if config.module == BudgetModule.OPEX
            else NUMERIC_QUANTUM
        )
        self._families = self._build_amount_families()

    @property
    def editable_columns(self) -> tuple[str, ...]:
        return self._config.insert_columns

    def _build_amount_families(self):
        suffixes = []
        for column, value_type in self._config.insert_column_types:
            if value_type != "NUMERIC":
                continue
            for month in MONTHS:
                prefix = f"{month}_"
                if column.startswith(prefix):
                    suffix = column[len(prefix):]
                    if suffix and suffix not in suffixes:
                        suffixes.append(suffix)
                    break

        families = {}
        for suffix in suffixes:
            months = tuple(f"{month}_{suffix}" for month in MONTHS)
            annual = f"anio_{suffix}"
            if self._type_map.get(annual) != "NUMERIC":
                continue
            if not all(self._type_map.get(column) == "NUMERIC" for column in months):
                continue
            family = (months, annual)
            for column in (*months, annual):
                families[column] = family
        return families

    @staticmethod
    def _blank(value) -> bool:
        return value is None or (isinstance(value, str) and not value.strip())

    @staticmethod
    def _normalize_numeric_text(value) -> str:
        text = str(value).strip().replace("US$", "").replace("$", "").replace(" ", "")
        if "," in text and "." in text:
            if text.rfind(".") > text.rfind(","):
                text = text.replace(",", "")
            else:
                text = text.replace(".", "").replace(",", ".")
        elif "," in text:
            text = text.replace(",", ".")
        return text

    def _numeric(self, value, *, field_name: str) -> Decimal:
        if self._blank(value):
            raise BudgetRowEditError(f"{field_name} no puede quedar vacio.")
        if isinstance(value, bool):
            raise BudgetRowEditError(f"{field_name} debe ser numerico.")
        try:
            amount = value if isinstance(value, Decimal) else Decimal(self._normalize_numeric_text(value))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise BudgetRowEditError(f"{field_name} debe ser numerico.") from exc
        if not amount.is_finite():
            raise BudgetRowEditError(f"{field_name} debe ser finito.")
        if amount < ZERO:
            raise BudgetRowEditError(f"{field_name} no puede ser negativo.")
        return amount.quantize(self._quantum, rounding=ROUND_HALF_UP)

    def _existing_numeric(self, value, *, field_name: str) -> Decimal:
        if value is None:
            return ZERO
        return self._numeric(value, field_name=field_name)

    @staticmethod
    def _string(value):
        if value is None:
            return None
        text = str(value).strip()
        return text if text else None

    @staticmethod
    def _integer(value, *, field_name: str) -> int:
        if value is None or (isinstance(value, str) and not value.strip()):
            raise BudgetRowEditError(f"{field_name} no puede quedar vacio.")
        if isinstance(value, bool):
            raise BudgetRowEditError(f"{field_name} debe ser entero.")
        try:
            number = Decimal(str(value).strip())
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise BudgetRowEditError(f"{field_name} debe ser entero.") from exc
        if not number.is_finite():
            raise BudgetRowEditError(f"{field_name} debe ser finito.")
        integral = number.to_integral_value()
        if number != integral:
            raise BudgetRowEditError(f"{field_name} debe ser entero sin decimales.")
        result = int(integral)
        if result < 0:
            raise BudgetRowEditError(f"{field_name} no puede ser negativo.")
        return result

    def _normalize(self, column: str, value):
        value_type = self._type_map.get(column)
        if value_type is None:
            raise BudgetRowEditError(
                "La columna no pertenece al contrato editable del modulo: "
                f"{column}"
            )
        if value_type == "STRING":
            return self._string(value)
        if value_type == "INTEGER":
            return self._integer(value, field_name=column)
        if value_type == "NUMERIC":
            return self._numeric(value, field_name=column)
        raise BudgetRowEditError(f"Tipo editable no soportado para {column}: {value_type}")

    def _set_month(self, row, *, column, value, month_columns, annual_column):
        result = deepcopy(dict(row))
        result[column] = self._numeric(value, field_name=column)
        total = sum(
            (self._existing_numeric(result.get(month), field_name=month) for month in month_columns),
            ZERO,
        ).quantize(self._quantum, rounding=ROUND_HALF_UP)
        result[annual_column] = total
        return result

    def _set_annual(self, row, *, value, month_columns, annual_column):
        target = self._numeric(value, field_name=annual_column)
        result = deepcopy(dict(row))
        editable_months = [column for column in month_columns if row.get(column) is not None]
        if not editable_months:
            if target == ZERO:
                result[annual_column] = target
                return result
            raise BudgetRowEditError(f"No existen meses con base para redistribuir {annual_column}.")

        basis = {
            column: self._existing_numeric(row.get(column), field_name=column)
            for column in editable_months
        }
        current_total = sum(basis.values(), ZERO).quantize(self._quantum, rounding=ROUND_HALF_UP)

        if target == ZERO:
            zero = ZERO.quantize(self._quantum)
            for column in editable_months:
                result[column] = zero
            result[annual_column] = target
            return result

        if current_total == ZERO:
            raise BudgetRowEditError(
                f"No existe una distribucion mensual previa para {annual_column}."
            )

        allocated = {
            column: (target * amount / current_total).quantize(
                self._quantum,
                rounding=ROUND_HALF_UP,
            )
            for column, amount in basis.items()
        }
        residual = (target - sum(allocated.values(), ZERO)).quantize(
            self._quantum,
            rounding=ROUND_HALF_UP,
        )
        if residual != ZERO:
            correction_column = max(
                editable_months,
                key=lambda column: (abs(basis[column]), -editable_months.index(column)),
            )
            allocated[correction_column] = (
                allocated[correction_column] + residual
            ).quantize(self._quantum, rounding=ROUND_HALF_UP)

        final_total = sum(allocated.values(), ZERO).quantize(
            self._quantum,
            rounding=ROUND_HALF_UP,
        )
        if final_total != target:
            raise BudgetRowEditError("No fue posible conservar exactamente el total anual.")

        for column, amount in allocated.items():
            result[column] = amount
        result[annual_column] = target
        return result

    def edit_value(self, row, column: str, value) -> dict:
        column_value = str(column).strip()
        if column_value not in self._type_map:
            raise BudgetRowEditError(
                "La columna no pertenece al contrato editable del modulo: "
                f"{column_value}"
            )

        family = self._families.get(column_value)
        if family is not None:
            month_columns, annual_column = family
            if column_value == annual_column:
                return self._set_annual(
                    row,
                    value=value,
                    month_columns=month_columns,
                    annual_column=annual_column,
                )
            return self._set_month(
                row,
                column=column_value,
                value=value,
                month_columns=month_columns,
                annual_column=annual_column,
            )

        result = deepcopy(dict(row))
        result[column_value] = self._normalize(column_value, value)
        return result
