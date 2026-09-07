from dataclasses import dataclass
from decimal import (
    Decimal,
    ROUND_HALF_UP,
)
from typing import Any

from app.config.presupuesto_app_config import (
    HABILITADO_COLUMN,
    USD_TOTAL_COLUMN,
)
from app.services.presupuesto_workspace import (
    SESSION_ROW_ID,
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
class ChangeDetail:
    session_row_id: int
    pais: str
    presupuestador: str
    nombre_gasto: str
    column: str
    before: Any
    after: Any


@dataclass(frozen=True)
class ChangeSummary:
    original_total: Decimal
    simulated_total: Decimal
    difference: Decimal
    variation_percent: Decimal | None
    pending_rows: int
    pending_fields: int
    by_country: tuple[VariationBreakdown, ...]
    by_budgeter: tuple[VariationBreakdown, ...]
    details: tuple[ChangeDetail, ...]


class PresupuestoChangeSummaryService:
    def __init__(
        self,
        workspace: PresupuestoWorkspace,
    ):
        self._workspace = workspace

    def build(self) -> ChangeSummary:
        pending = (
            self._workspace
            .get_pending_changes()
        )

        simulated_total = ZERO

        for row in self._workspace.iter_rows():
            if self._is_enabled(row):
                simulated_total += self._amount(
                    row.get(
                        USD_TOTAL_COLUMN
                    )
                )

        simulated_total = self._money(
            simulated_total
        )

        difference_total = ZERO

        country_totals = {}
        budgeter_totals = {}

        details = []

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

            country = self._label(
                current.get("pais")
                or original.get("pais")
            )

            budgeter = self._label(
                current.get("presupuestador")
                or original.get("presupuestador")
            )

            self._accumulate(
                country_totals,
                country,
                original_amount,
                simulated_amount,
            )

            self._accumulate(
                budgeter_totals,
                budgeter,
                original_amount,
                simulated_amount,
            )

            for field_change in (
                row_change.changes
            ):
                details.append(
                    ChangeDetail(
                        session_row_id=row_id,
                        pais=country,
                        presupuestador=budgeter,
                        nombre_gasto=self._label(
                            current.get(
                                "nombre_gasto"
                            )
                            or original.get(
                                "nombre_gasto"
                            )
                        ),
                        column=(
                            field_change.column
                        ),
                        before=(
                            field_change.before
                        ),
                        after=(
                            field_change.after
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
            len(row_change.changes)
            for row_change in pending
        )

        return ChangeSummary(
            original_total=original_total,
            simulated_total=simulated_total,
            difference=difference_total,
            variation_percent=(
                variation_percent
            ),
            pending_rows=len(pending),
            pending_fields=pending_fields,
            by_country=self._build_breakdown(
                country_totals
            ),
            by_budgeter=self._build_breakdown(
                budgeter_totals
            ),
            details=tuple(details),
        )

    def _active_annual(
        self,
        row,
    ) -> Decimal:
        if not self._is_enabled(row):
            return ZERO

        return self._money(
            self._amount(
                row.get(
                    USD_TOTAL_COLUMN
                )
            )
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

        if isinstance(value, Decimal):
            return value

        return Decimal(
            str(value)
        )

    @staticmethod
    def _money(
        value: Decimal,
    ) -> Decimal:
        return value.quantize(
            CENT,
            rounding=ROUND_HALF_UP,
        )

    @staticmethod
    def _label(
        value,
    ) -> str:
        if value is None:
            return "(Sin valor)"

        text = str(value).strip()

        if not text:
            return "(Sin valor)"

        return text

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

        for key, values in totals.items():
            original = self._money(
                values[0]
            )

            simulated = self._money(
                values[1]
            )

            difference = self._money(
                simulated - original
            )

            if difference == ZERO:
                continue

            rows.append(
                VariationBreakdown(
                    key=key,
                    original_total=original,
                    simulated_total=simulated,
                    difference=difference,
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

        return tuple(rows)

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