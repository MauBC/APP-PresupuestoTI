from dataclasses import dataclass
from datetime import (
    datetime,
    timezone,
)
from decimal import (
    Decimal,
    InvalidOperation,
    ROUND_HALF_UP,
)
from typing import (
    Any,
    Mapping,
)

from app.config.budget_module_config import (
    BudgetModule,
)
from app.config.budget_modules import (
    OPEX_MODULE_CONFIG,
)
from app.services.new_budget_row_service import (
    NewBudgetRowError,
    NewBudgetRowService,
)
from app.services.proportional_allocation_service import (
    ProportionalAllocationError,
    ProportionalAllocationService,
)


CENT = Decimal("0.01")
ZERO = Decimal("0.00")
HUNDRED = Decimal("100.00")


class OpexSmartInsertError(
    ValueError
):
    pass


@dataclass(
    frozen=True,
    slots=True,
)
class OpexSmartInsertItem:
    ceco: str
    annual_total: Decimal
    dimensions: tuple[
        tuple[str, Any],
        ...,
    ]
    ambiguous_values: tuple[
        tuple[
            str,
            tuple[str, ...],
        ],
        ...,
    ]
    no_data_columns: tuple[
        str,
        ...,
    ]
    matching_row_count: int
    blockers: tuple[
        str,
        ...,
    ]
    row: dict[str, Any] | None

    @property
    def is_ready(
        self,
    ) -> bool:
        return (
            self.row is not None
            and not self.blockers
        )

    @property
    def dimension_map(
        self,
    ) -> dict[str, Any]:
        return dict(
            self.dimensions
        )

    @property
    def ambiguous_map(
        self,
    ) -> dict[
        str,
        tuple[str, ...],
    ]:
        return dict(
            self.ambiguous_values
        )


@dataclass(
    frozen=True,
    slots=True,
)
class OpexSmartInsertPreview:
    mode: str
    source_total: Decimal
    allocated_total: Decimal
    monthly_percentages: tuple[
        tuple[str, Decimal],
        ...,
    ]
    items: tuple[
        OpexSmartInsertItem,
        ...,
    ]

    @property
    def row_count(
        self,
    ) -> int:
        return len(
            self.items
        )

    @property
    def ready_count(
        self,
    ) -> int:
        return sum(
            1
            for item in self.items
            if item.is_ready
        )

    @property
    def blocked_count(
        self,
    ) -> int:
        return (
            self.row_count
            - self.ready_count
        )

    @property
    def is_ready(
        self,
    ) -> bool:
        return (
            self.row_count > 0
            and
            self.blocked_count == 0
        )


class OpexSmartInsertService:
    def __init__(
        self,
        inference_service,
        *,
        row_service=None,
    ):
        self._inference = (
            inference_service
        )

        self._row_service = (
            row_service
            if row_service is not None
            else NewBudgetRowService(
                OPEX_MODULE_CONFIG
            )
        )

        config = (
            self._row_service
            .module_config
        )

        if (
            config.module
            != BudgetModule.OPEX
        ):
            raise OpexSmartInsertError(
                "La insercion inteligente "
                "solo admite OPEX."
            )

        self._config = config

    def preview_percentages(
        self,
        *,
        base_dimensions,
        allocations,
        annual_total,
        actor,
        monthly_percentages=None,
        timestamp=None,
    ) -> OpexSmartInsertPreview:
        dimensions = (
            self._normalize_base_dimensions(
                base_dimensions
            )
        )

        actor_value = (
            self._actor(
                actor
            )
        )

        effective_time = (
            self._timestamp(
                timestamp
            )
        )

        total = self._money(
            annual_total,
            label="total anual",
        )

        percentages = (
            self._normalize_allocations(
                allocations,
                value_parser=(
                    self._percentage
                ),
                value_label=(
                    "porcentaje"
                ),
            )
        )

        percentage_total = sum(
            (
                value
                for _, value
                in percentages
            ),
            ZERO,
        ).quantize(
            CENT,
            rounding=ROUND_HALF_UP,
        )

        if (
            percentage_total
            != HUNDRED
        ):
            raise OpexSmartInsertError(
                "La distribucion por CECO "
                "debe sumar 100.00%. "
                f"Actual={percentage_total}%."
            )

        try:
            allocated = (
                ProportionalAllocationService
                .allocate(
                    percentages,
                    total,
                )
            )

        except (
            ProportionalAllocationError
        ) as exc:
            raise OpexSmartInsertError(
                str(exc)
            ) from exc

        allocation_rows = tuple(
            (
                ceco,
                allocated[ceco],
            )
            for ceco, _
            in percentages
        )

        return self._build_preview(
            mode="PERCENTAGE",
            base_dimensions=dimensions,
            allocation_rows=(
                allocation_rows
            ),
            source_total=total,
            actor=actor_value,
            monthly_percentages=(
                monthly_percentages
            ),
            timestamp=effective_time,
        )

    def preview_amounts(
        self,
        *,
        base_dimensions,
        allocations,
        actor,
        monthly_percentages=None,
        timestamp=None,
    ) -> OpexSmartInsertPreview:
        dimensions = (
            self._normalize_base_dimensions(
                base_dimensions
            )
        )

        actor_value = self._actor(
            actor
        )

        effective_time = (
            self._timestamp(
                timestamp
            )
        )

        amounts = (
            self._normalize_allocations(
                allocations,
                value_parser=(
                    lambda value:
                        self._money(
                            value,
                            label=(
                                "importe CECO"
                            ),
                        )
                ),
                value_label="importe",
            )
        )

        total = sum(
            (
                amount
                for _, amount
                in amounts
            ),
            ZERO,
        ).quantize(
            CENT,
            rounding=ROUND_HALF_UP,
        )

        return self._build_preview(
            mode="AMOUNT",
            base_dimensions=dimensions,
            allocation_rows=amounts,
            source_total=total,
            actor=actor_value,
            monthly_percentages=(
                monthly_percentages
            ),
            timestamp=effective_time,
        )

    def build_rows(
        self,
        preview:
            OpexSmartInsertPreview,
    ) -> tuple[
        dict[str, Any],
        ...,
    ]:
        if not isinstance(
            preview,
            OpexSmartInsertPreview,
        ):
            raise TypeError(
                "preview debe ser "
                "OpexSmartInsertPreview."
            )

        blocked = tuple(
            item.ceco
            for item in preview.items
            if not item.is_ready
        )

        if blocked:
            raise OpexSmartInsertError(
                "No se pueden generar las "
                "filas porque existen CECOs "
                "pendientes de resolver: "
                + ", ".join(
                    blocked
                )
            )

        return tuple(
            dict(
                item.row
            )
            for item in preview.items
            if item.row is not None
        )

    def add_to_workspace(
        self,
        preview:
            OpexSmartInsertPreview,
        workspace,
        *,
        description: str = (
            "Insercion inteligente OPEX"
        ),
    ):
        if (
            workspace
            .module_config
            .module
            != BudgetModule.OPEX
        ):
            raise OpexSmartInsertError(
                "El Workspace debe "
                "pertenecer a OPEX."
            )

        rows = self.build_rows(
            preview
        )

        if not rows:
            raise OpexSmartInsertError(
                "No existen filas para "
                "agregar al Workspace."
            )

        return (
            workspace
            .add_new_rows(
                rows,
                description=(
                    str(description)
                    .strip()
                    or
                    "Insercion inteligente OPEX"
                ),
            )
        )

    def _build_preview(
        self,
        *,
        mode,
        base_dimensions,
        allocation_rows,
        source_total,
        actor,
        monthly_percentages,
        timestamp,
    ):
        month_distribution = (
            self._monthly_percentages(
                monthly_percentages
            )
        )

        items = []

        for (
            ceco,
            annual_amount,
        ) in allocation_rows:
            known = dict(
                base_dimensions
            )

            known[
                self._config
                .ceco_column
            ] = ceco

            inference = (
                self._inference
                .infer(
                    known
                )
            )

            blockers = []

            if not (
                inference
                .has_historical_match
            ):
                blockers.append(
                    "SIN_HISTORIAL"
                )

            for (
                column,
                _,
            ) in (
                inference
                .ambiguous_values
            ):
                blockers.append(
                    "AMBIGUO:"
                    f"{column}"
                )

            row = None

            if not blockers:
                try:
                    draft = (
                        self._row_service
                        .create_draft(
                            inference
                            .resolved_values,
                            actor=actor,
                            timestamp=timestamp,
                        )
                    )

                    draft = (
                        self._row_service
                        .with_monthly_distribution(
                            draft,
                            percentages=dict(
                                month_distribution
                            ),
                            annual_total=(
                                annual_amount
                            ),
                        )
                    )

                    row = dict(
                        draft.row
                    )

                except (
                    NewBudgetRowError
                ) as exc:
                    raise (
                        OpexSmartInsertError(
                            "No se pudo generar "
                            f"el CECO {ceco}: "
                            f"{exc}"
                        )
                    ) from exc

            items.append(
                OpexSmartInsertItem(
                    ceco=ceco,
                    annual_total=(
                        annual_amount
                    ),
                    dimensions=tuple(
                        inference
                        .resolved_values
                        .items()
                    ),
                    ambiguous_values=(
                        inference
                        .ambiguous_values
                    ),
                    no_data_columns=(
                        inference
                        .no_data_columns
                    ),
                    matching_row_count=(
                        inference
                        .matching_row_count
                    ),
                    blockers=tuple(
                        blockers
                    ),
                    row=row,
                )
            )

        allocated_total = sum(
            (
                item.annual_total
                for item in items
            ),
            ZERO,
        ).quantize(
            CENT,
            rounding=ROUND_HALF_UP,
        )

        if (
            allocated_total
            != source_total
        ):
            raise OpexSmartInsertError(
                "La suma generada no "
                "coincide con el total. "
                f"Origen={source_total}; "
                f"generado={allocated_total}."
            )

        return OpexSmartInsertPreview(
            mode=mode,
            source_total=(
                source_total
            ),
            allocated_total=(
                allocated_total
            ),
            monthly_percentages=(
                month_distribution
            ),
            items=tuple(
                items
            ),
        )

    def _normalize_base_dimensions(
        self,
        values,
    ) -> dict[str, Any]:
        try:
            supplied = dict(
                values or {}
            )
        except Exception as exc:
            raise OpexSmartInsertError(
                "Los datos base no tienen "
                "un formato valido."
            ) from exc

        if (
            self._config
            .ceco_column
            in supplied
        ):
            raise OpexSmartInsertError(
                "CECO debe definirse en "
                "la distribucion, no en "
                "los datos base."
            )

        allowed = set(
            self._config
            .dimension_columns
        )

        invalid = sorted(
            set(supplied)
            - allowed
        )

        if invalid:
            raise OpexSmartInsertError(
                "Columnas OPEX no validas: "
                + ", ".join(
                    invalid
                )
            )

        result = {}

        for column in (
            self._config
            .dimension_columns
        ):
            if column not in supplied:
                continue

            value = supplied[
                column
            ]

            if value is None:
                continue

            if isinstance(
                value,
                str,
            ):
                value = value.strip()

                if not value:
                    continue

            result[
                column
            ] = value

        if not result:
            raise OpexSmartInsertError(
                "Debe indicar al menos "
                "un dato base del gasto."
            )

        return result

    def _normalize_allocations(
        self,
        allocations,
        *,
        value_parser,
        value_label,
    ):
        if isinstance(
            allocations,
            Mapping,
        ):
            raw = tuple(
                allocations.items()
            )
        else:
            try:
                raw = tuple(
                    allocations
                )
            except Exception as exc:
                raise (
                    OpexSmartInsertError(
                        "La distribucion por "
                        "CECO no tiene un "
                        "formato valido."
                    )
                ) from exc

        if not raw:
            raise OpexSmartInsertError(
                "Debe indicar al menos "
                "un CECO."
            )

        result = []
        seen = set()

        for item in raw:
            try:
                (
                    raw_ceco,
                    raw_value,
                ) = item
            except Exception as exc:
                raise (
                    OpexSmartInsertError(
                        "Cada distribucion "
                        "debe contener CECO "
                        "y valor."
                    )
                ) from exc

            ceco = str(
                raw_ceco
                if raw_ceco is not None
                else ""
            ).strip()

            if not ceco:
                raise OpexSmartInsertError(
                    "CECO no puede estar "
                    "vacio."
                )

            if ceco in seen:
                raise OpexSmartInsertError(
                    "CECO duplicado en la "
                    "distribucion: "
                    f"{ceco}."
                )

            seen.add(
                ceco
            )

            value = value_parser(
                raw_value
            )

            if value < ZERO:
                raise OpexSmartInsertError(
                    f"El {value_label} de "
                    f"{ceco} no puede ser "
                    "negativo."
                )

            result.append(
                (
                    ceco,
                    value,
                )
            )

        return tuple(
            result
        )

    def _monthly_percentages(
        self,
        supplied,
    ):
        if supplied is not None:
            try:
                values = dict(
                    supplied
                )
            except Exception as exc:
                raise (
                    OpexSmartInsertError(
                        "La distribucion mensual "
                        "no tiene un formato "
                        "valido."
                    )
                ) from exc

            return tuple(
                (
                    column,
                    values.get(
                        column,
                        ZERO,
                    ),
                )
                for column in (
                    self._config
                    .month_columns
                )
            )

        columns = tuple(
            self._config
            .month_columns
        )

        base = (
            HUNDRED
            / Decimal(
                len(columns)
            )
        ).quantize(
            CENT,
            rounding=ROUND_HALF_UP,
        )

        result = {
            column:
                base
            for column in columns
        }

        residual = (
            HUNDRED
            - sum(
                result.values(),
                ZERO,
            )
        ).quantize(
            CENT,
            rounding=ROUND_HALF_UP,
        )

        result[
            columns[-1]
        ] += residual

        return tuple(
            (
                column,
                result[column],
            )
            for column in columns
        )

    @staticmethod
    def _actor(
        actor,
    ) -> str:
        value = str(
            actor
            if actor is not None
            else ""
        ).strip()

        if not value:
            raise OpexSmartInsertError(
                "actor no puede estar "
                "vacio."
            )

        return value

    @staticmethod
    def _timestamp(
        value,
    ):
        result = (
            datetime.now(
                timezone.utc
            )
            if value is None
            else value
        )

        if (
            result.tzinfo
            is None
            or
            result.utcoffset()
            is None
        ):
            raise OpexSmartInsertError(
                "timestamp debe incluir "
                "zona horaria."
            )

        return result

    @staticmethod
    def _decimal(
        value,
        *,
        label,
    ) -> Decimal:
        if isinstance(
            value,
            bool,
        ):
            raise OpexSmartInsertError(
                f"{label} no es numerico."
            )

        try:
            parsed = Decimal(
                str(
                    value
                ).strip()
            )

        except (
            InvalidOperation,
            TypeError,
            ValueError,
        ) as exc:
            raise OpexSmartInsertError(
                f"{label} no es numerico."
            ) from exc

        if not parsed.is_finite():
            raise OpexSmartInsertError(
                f"{label} debe ser finito."
            )

        return parsed

    @classmethod
    def _money(
        cls,
        value,
        *,
        label,
    ) -> Decimal:
        parsed = cls._decimal(
            value,
            label=label,
        ).quantize(
            CENT,
            rounding=ROUND_HALF_UP,
        )

        if parsed < ZERO:
            raise OpexSmartInsertError(
                f"{label} no puede ser "
                "negativo."
            )

        return parsed

    @classmethod
    def _percentage(
        cls,
        value,
    ) -> Decimal:
        return cls._decimal(
            value,
            label="porcentaje",
        ).quantize(
            CENT,
            rounding=ROUND_HALF_UP,
        )
