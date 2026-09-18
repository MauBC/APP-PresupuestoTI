from dataclasses import dataclass
from typing import Any, Mapping

from app.config.budget_module_config import (
    BudgetModule,
)
from app.config.budget_modules import (
    OPEX_MODULE_CONFIG,
)


class OpexSmartInferenceError(
    ValueError
):
    pass


@dataclass(
    frozen=True,
    slots=True,
)
class OpexSmartInferenceResult:
    provided_values: tuple[
        tuple[str, str],
        ...,
    ]
    inferred_values: tuple[
        tuple[str, str],
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

    @property
    def resolved_values(
        self,
    ) -> dict[str, str]:
        return dict(
            (
                *self.provided_values,
                *self.inferred_values,
            )
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

    @property
    def has_historical_match(
        self,
    ) -> bool:
        return (
            self.matching_row_count
            > 0
        )


class OpexSmartInferenceService:
    def __init__(
        self,
        module_config=(
            OPEX_MODULE_CONFIG
        ),
    ):
        if (
            module_config.module
            != BudgetModule.OPEX
        ):
            raise (
                OpexSmartInferenceError(
                    "La inferencia inteligente "
                    "solo admite OPEX."
                )
            )

        self._config = (
            module_config
        )

    @property
    def module_config(
        self,
    ):
        return self._config

    def infer(
        self,
        known_values:
            Mapping[str, Any],
        historical_rows,
    ) -> OpexSmartInferenceResult:
        known = (
            self._normalize_known_values(
                known_values
            )
        )

        candidates = tuple(
            row
            for row in historical_rows
            if (
                self._is_enabled(row)
                and
                self._matches(
                    row,
                    known,
                )
            )
        )

        provided = tuple(
            (
                column,
                known[column],
            )
            for column
            in self._config
            .dimension_columns
            if column in known
        )

        missing_columns = tuple(
            column
            for column
            in self._config
            .dimension_columns
            if column not in known
        )

        if not candidates:
            return (
                OpexSmartInferenceResult(
                    provided_values=(
                        provided
                    ),
                    inferred_values=(),
                    ambiguous_values=(),
                    no_data_columns=(
                        missing_columns
                    ),
                    matching_row_count=0,
                )
            )

        inferred = []
        ambiguous = []
        no_data = []

        for column in (
            missing_columns
        ):
            options = (
                self._distinct_values(
                    candidates,
                    column,
                )
            )

            if len(options) == 1:
                inferred.append(
                    (
                        column,
                        options[0],
                    )
                )
                continue

            if len(options) > 1:
                ambiguous.append(
                    (
                        column,
                        options,
                    )
                )
                continue

            no_data.append(
                column
            )

        return (
            OpexSmartInferenceResult(
                provided_values=(
                    provided
                ),
                inferred_values=tuple(
                    inferred
                ),
                ambiguous_values=tuple(
                    ambiguous
                ),
                no_data_columns=tuple(
                    no_data
                ),
                matching_row_count=len(
                    candidates
                ),
            )
        )

    def _normalize_known_values(
        self,
        values,
    ) -> dict[str, str]:
        try:
            supplied = dict(
                values or {}
            )
        except Exception as exc:
            raise (
                OpexSmartInferenceError(
                    "Los datos conocidos "
                    "no tienen un formato "
                    "valido."
                )
            ) from exc

        allowed = set(
            self._config
            .dimension_columns
        )

        invalid = sorted(
            set(supplied)
            - allowed
        )

        if invalid:
            raise (
                OpexSmartInferenceError(
                    "Columnas OPEX no "
                    "validas: "
                    + ", ".join(
                        invalid
                    )
                )
            )

        normalized = {}

        for column in (
            self._config
            .dimension_columns
        ):
            if column not in supplied:
                continue

            value = self._normalize(
                supplied[column]
            )

            if value is not None:
                normalized[
                    column
                ] = value

        if not normalized:
            raise (
                OpexSmartInferenceError(
                    "Debe proporcionar al "
                    "menos un dato OPEX."
                )
            )

        return normalized

    @classmethod
    def _matches(
        cls,
        row,
        known,
    ) -> bool:
        return all(
            cls._normalize(
                row.get(column)
            )
            == value
            for column, value
            in known.items()
        )

    @classmethod
    def _distinct_values(
        cls,
        rows,
        column,
    ) -> tuple[str, ...]:
        values = {
            value
            for row in rows
            if (
                value := cls._normalize(
                    row.get(column)
                )
            )
            is not None
        }

        return tuple(
            sorted(
                values
            )
        )

    @staticmethod
    def _is_enabled(
        row,
    ) -> bool:
        return bool(
            row.get(
                "habilitado",
                True,
            )
        )

    @staticmethod
    def _normalize(
        value,
    ) -> str | None:
        if value is None:
            return None

        clean = str(
            value
        ).strip()

        return (
            clean
            if clean
            else None
        )
