from datetime import (
    datetime,
    timezone,
)
from decimal import Decimal
from typing import (
    Any,
    Callable,
    Mapping,
)
from uuid import uuid4

from app.config.budget_module_config import (
    BudgetModuleConfig,
)
from app.models.new_budget_row import (
    NewBudgetRowDraft,
)


ZERO = Decimal("0.00")


class NewBudgetRowError(
    ValueError
):
    pass


def generate_new_row_id(
) -> str:
    return str(
        uuid4()
    )


class NewBudgetRowService:
    def __init__(
        self,
        module_config:
            BudgetModuleConfig,
        *,
        row_id_factory:
            Callable[[], str]
            = generate_new_row_id,
    ):
        self._config = module_config
        self._row_id_factory = (
            row_id_factory
        )

    @property
    def module_config(
        self,
    ):
        return self._config

    def create_draft(
        self,
        dimensions:
            Mapping[str, Any],
        *,
        actor: str,
        timestamp:
            datetime | None = None,
    ) -> NewBudgetRowDraft:
        actor_value = str(
            actor
            if actor is not None
            else ""
        ).strip()

        if not actor_value:
            raise NewBudgetRowError(
                "actor no puede estar vacio."
            )

        if timestamp is None:
            effective_time = (
                datetime.now(
                    timezone.utc
                )
            )

        else:
            effective_time = timestamp

        if (
            effective_time.tzinfo
            is None
            or effective_time
            .utcoffset()
            is None
        ):
            raise NewBudgetRowError(
                "timestamp debe incluir "
                "zona horaria."
            )

        supplied = dict(
            dimensions
        )

        invalid = sorted(
            set(supplied)
            - set(
                self._config
                .dimension_columns
            )
        )

        if invalid:
            raise NewBudgetRowError(
                "Columnas no validas para "
                f"{self._config.label}: "
                + ", ".join(
                    invalid
                )
            )

        row_id = str(
            self._row_id_factory()
        ).strip()

        if not row_id:
            raise NewBudgetRowError(
                "row_id no puede estar vacio."
            )

        row = {
            column:
                self._normalize_dimension(
                    supplied.get(
                        column
                    )
                )
            for column
            in self._config
            .dimension_columns
        }

        for (
            column,
            value_type,
        ) in (
            self._config
            .insert_column_types
        ):
            if column in row:
                continue

            if value_type == "NUMERIC":
                row[column] = ZERO

            else:
                row[column] = None

        row.update(
            {
                "row_id":
                    row_id,
                "habilitado":
                    True,
                "version":
                    1,
                "created_at":
                    effective_time,
                "created_by":
                    actor_value,
                "updated_at":
                    effective_time,
                "updated_by":
                    actor_value,
            }
        )

        return NewBudgetRowDraft(
            module=(
                self._config
                .module
                .value
            ),
            row=row,
        )

    @staticmethod
    def _normalize_dimension(
        value,
    ):
        if value is None:
            return None

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

        return value
