from dataclasses import dataclass
from decimal import (
    Decimal,
    InvalidOperation,
    ROUND_HALF_UP,
)
from typing import Any

from app.config.presupuesto_app_config import (
    HABILITADO_COLUMN,
)
from app.services.presupuesto_workspace import (
    PresupuestoWorkspace,
)


CENT = Decimal("0.01")
ZERO = Decimal("0.00")


@dataclass(frozen=True)
class VariationBreakdown:
    key: str
    original_total: Decimal
    simulated_total: Decimal
    difference: Decimal
    variation_percent: Decimal | None


@dataclass(frozen=True)
class ChangeContextValue:
    column: str
    label: str
    value: str


@dataclass(frozen=True)
class ChangeDetail:
    session_row_id: int

    context: tuple[
        ChangeContextValue,
        ...
    ]

    column: str
    before: Any
    after: Any

    difference: Decimal | None
    variation_percent: Decimal | None

    @property
    def context_map(
        self,
    ) -> dict[str, str]:
        return {
            item.column: item.value
            for item in self.context
        }

    def context_value(
        self,
        column: str,
    ) -> str:
        return self.context_map.get(
            column,
            "(Sin valor)",
        )

    @property
    def pais(self) -> str:
        return self.context_value(
            "pais"
        )

    @property
    def presupuestador(
        self,
    ) -> str:
        return self.context_value(
            "presupuestador"
        )

    @property
    def nombre_gasto(
        self,
    ) -> str:
        return self.context_value(
            "nombre_gasto"
        )

    @property
    def proveedor(
        self,
    ) -> str:
        return self.context_value(
            "proveedor"
        )

    @property
    def ceco(
        self,
    ) -> str:
        return self.context_value(
            "ceco"
        )


@dataclass(frozen=True)
class ChangeSummary:
    original_total: Decimal
    simulated_total: Decimal
    difference: Decimal
    variation_percent: Decimal | None

    pending_rows: int
    pending_fields: int

    by_country: tuple[
        VariationBreakdown,
        ...
    ]

    by_budgeter: tuple[
        VariationBreakdown,
        ...
    ]

    details: tuple[
        ChangeDetail,
        ...
    ]


class PresupuestoChangeSummaryService:
    def __init__(
        self,
        workspace: PresupuestoWorkspace,
    ):
        self._workspace = workspace
        self._config = (
            workspace.module_config
        )

    def build(
        self,
    ) -> ChangeSummary:
        pending = (
            self._workspace
            .get_pending_changes()
        )

        simulated_total = ZERO

        for row in (
            self._workspace.iter_rows()
        ):
            if self._is_enabled(
                row
            ):
                simulated_total += (
                    self._amount(
                        row.get(
                            self._config
                            .annual_column
                        )
                    )
                )

        simulated_total = self._money(
            simulated_total
        )

        difference_total = ZERO

        country_totals = {}
        budgeter_totals = {}

        details = []

        has_country = (
            "pais"
            in self._config.dimension_columns
        )

        has_budgeter = (
            "presupuestador"
            in self._config.dimension_columns
        )

        for row_change in pending:
            row_id = (
                row_change.session_row_id
            )

            original = (
                self._workspace
                .get_original_row(
                    row_id
                )
            )

            current = (
                self._workspace
                .get_row(
                    row_id
                )
            )

            original_amount = (
                self._active_annual(
                    original
                )
            )

            simulated_amount = (
                self._active_annual(
                    current
                )
            )

            difference_total += (
                simulated_amount
                - original_amount
            )

            if has_country:
                country = self._context_label(
                    current,
                    original,
                    "pais",
                )

                self._accumulate(
                    country_totals,
                    country,
                    original_amount,
                    simulated_amount,
                )

            if has_budgeter:
                budgeter = self._context_label(
                    current,
                    original,
                    "presupuestador",
                )

                self._accumulate(
                    budgeter_totals,
                    budgeter,
                    original_amount,
                    simulated_amount,
                )

            context = (
                self._build_context(
                    current,
                    original,
                )
            )

            for field_change in (
                row_change.changes
            ):
                (
                    field_difference,
                    field_variation,
                ) = (
                    self._field_variation(
                        field_change.column,
                        field_change.before,
                        field_change.after,
                    )
                )

                details.append(
                    ChangeDetail(
                        session_row_id=(
                            row_id
                        ),
                        context=context,
                        column=(
                            field_change.column
                        ),
                        before=(
                            field_change.before
                        ),
                        after=(
                            field_change.after
                        ),
                        difference=(
                            field_difference
                        ),
                        variation_percent=(
                            field_variation
                        ),
                    )
                )

        difference_total = self._money(
            difference_total
        )

        original_total = self._money(
            simulated_total
            - difference_total
        )

        variation_percent = (
            self._variation_percent(
                original_total,
                difference_total,
            )
        )

        pending_fields = sum(
            len(
                row_change.changes
            )
            for row_change in pending
        )

        return ChangeSummary(
            original_total=(
                original_total
            ),
            simulated_total=(
                simulated_total
            ),
            difference=(
                difference_total
            ),
            variation_percent=(
                variation_percent
            ),
            pending_rows=len(
                pending
            ),
            pending_fields=(
                pending_fields
            ),
            by_country=(
                self._build_breakdown(
                    country_totals
                )
            ),
            by_budgeter=(
                self._build_breakdown(
                    budgeter_totals
                )
            ),
            details=tuple(
                details
            ),
        )

    def _build_context(
        self,
        current,
        original,
    ) -> tuple[
        ChangeContextValue,
        ...
    ]:
        result = []

        for column in (
            self._config
            .change_detail_columns
        ):
            result.append(
                ChangeContextValue(
                    column=column,
                    label=(
                        self._column_label(
                            column
                        )
                    ),
                    value=(
                        self._context_label(
                            current,
                            original,
                            column,
                        )
                    ),
                )
            )

        return tuple(
            result
        )

    def _active_annual(
        self,
        row,
    ) -> Decimal:
        if not self._is_enabled(
            row
        ):
            return ZERO

        return self._money(
            self._amount(
                row.get(
                    self._config
                    .annual_column
                )
            )
        )

    def _field_variation(
        self,
        column,
        before,
        after,
    ) -> tuple[
        Decimal | None,
        Decimal | None,
    ]:
        if (
            column
            not in
            self._config.amount_columns
        ):
            return (
                None,
                None,
            )

        before_amount = (
            self._amount(
                before
            )
        )

        after_amount = (
            self._amount(
                after
            )
        )

        difference = self._money(
            after_amount
            - before_amount
        )

        return (
            difference,
            self._variation_percent(
                before_amount,
                difference,
            ),
        )

    @staticmethod
    def _is_enabled(
        row,
    ) -> bool:
        return bool(
            row.get(
                HABILITADO_COLUMN,
                True,
            )
        )

    @staticmethod
    def _amount(
        value,
    ) -> Decimal:
        if value is None:
            return ZERO

        if isinstance(
            value,
            bool,
        ):
            return ZERO

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
            ValueError,
            TypeError,
        ):
            return ZERO

    @staticmethod
    def _money(
        value: Decimal,
    ) -> Decimal:
        return value.quantize(
            CENT,
            rounding=ROUND_HALF_UP,
        )

    @classmethod
    def _context_label(
        cls,
        current,
        original,
        column,
    ) -> str:
        current_value = (
            current.get(
                column
            )
        )

        if cls._has_value(
            current_value
        ):
            return cls._label(
                current_value
            )

        return cls._label(
            original.get(
                column
            )
        )

    @staticmethod
    def _has_value(
        value,
    ) -> bool:
        if value is None:
            return False

        if isinstance(
            value,
            str,
        ):
            return bool(
                value.strip()
            )

        return True

    @staticmethod
    def _label(
        value,
    ) -> str:
        if value is None:
            return "(Sin valor)"

        text = str(
            value
        ).strip()

        if not text:
            return "(Sin valor)"

        return text

    @staticmethod
    def _column_label(
        column: str,
    ) -> str:
        labels = {
            "proveedor": "Proveedor",
            "nombre_gasto": "Gasto",
            "pais": "Pais",
            "ceco": "CECO",
            "presupuestador":
                "Presupuestador",
            "proyecto": "Proyecto",
            "responsable": "Responsable",
        }

        return labels.get(
            column,
            column
            .replace("_", " ")
            .title(),
        )

    @staticmethod
    def _accumulate(
        target,
        key,
        original_amount,
        simulated_amount,
    ):
        if key not in target:
            target[key] = [
                ZERO,
                ZERO,
            ]

        target[key][0] += (
            original_amount
        )

        target[key][1] += (
            simulated_amount
        )

    def _build_breakdown(
        self,
        totals,
    ):
        rows = []

        for key, values in (
            totals.items()
        ):
            original = self._money(
                values[0]
            )

            simulated = self._money(
                values[1]
            )

            difference = self._money(
                simulated
                - original
            )

            if difference == ZERO:
                continue

            rows.append(
                VariationBreakdown(
                    key=key,
                    original_total=(
                        original
                    ),
                    simulated_total=(
                        simulated
                    ),
                    difference=(
                        difference
                    ),
                    variation_percent=(
                        self._variation_percent(
                            original,
                            difference,
                        )
                    ),
                )
            )

        rows.sort(
            key=lambda row: abs(
                row.difference
            ),
            reverse=True,
        )

        return tuple(
            rows
        )

    @staticmethod
    def _variation_percent(
        original,
        difference,
    ):
        if original == ZERO:
            return None

        return (
            difference
            / original
            * Decimal("100")
        ).quantize(
            CENT,
            rounding=ROUND_HALF_UP,
        )
