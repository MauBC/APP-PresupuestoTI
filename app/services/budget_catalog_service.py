from dataclasses import dataclass
from typing import Any


class BudgetCatalogError(
    ValueError
):
    pass


@dataclass(
    frozen=True,
    slots=True,
)
class BudgetCatalog:
    column: str
    values: tuple[str, ...]
    filters: tuple[
        tuple[
            str,
            str,
        ],
        ...,
    ]

    @property
    def count(
        self,
    ) -> int:
        return len(
            self.values
        )


class BudgetCatalogService:
    def __init__(
        self,
        repository,
    ):
        self._repository = (
            repository
        )

        self._config = (
            repository
            .module_config
        )

    @property
    def module_config(
        self,
    ):
        return self._config

    def values(
        self,
        column: str,
        *,
        filters=None,
        limit: int = 500,
    ) -> BudgetCatalog:
        if (
            column
            not in self._config
            .dimension_columns
        ):
            raise BudgetCatalogError(
                "La columna no pertenece "
                f"al modulo "
                f"{self._config.label}: "
                f"{column}"
            )

        clean_filters = {}

        for (
            key,
            value,
        ) in dict(
            filters or {}
        ).items():
            if (
                key
                not in self._config
                .dimension_columns
            ):
                raise BudgetCatalogError(
                    "Filtro no valido para "
                    f"{self._config.label}: "
                    f"{key}"
                )

            if value is None:
                continue

            clean = str(
                value
            ).strip()

            if clean:
                clean_filters[
                    key
                ] = clean

        values = (
            self._repository
            .get_catalog_values(
                column,
                filters=(
                    clean_filters
                ),
                limit=limit,
            )
        )

        return BudgetCatalog(
            column=column,
            values=tuple(
                values
            ),
            filters=tuple(
                clean_filters
                .items()
            ),
        )

    def common_catalogs(
        self,
        *,
        filters=None,
    ) -> dict[
        str,
        BudgetCatalog,
    ]:
        candidates = (
            self._config
            .country_column,
            self._config
            .budgeter_column,
            self._config
            .ceco_column,
        )

        columns = tuple(
            dict.fromkeys(
                column
                for column
                in candidates
                if column
            )
        )

        return {
            column:
                self.values(
                    column,
                    filters=filters,
                )
            for column
            in columns
        }
