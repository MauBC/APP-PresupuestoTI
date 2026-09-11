from collections import defaultdict
from decimal import (
    Decimal,
    ROUND_HALF_UP,
)

from app.config.presupuesto_app_config import (
    HABILITADO_COLUMN,
)
from app.models.aggregation_result import (
    AggregationResult,
)
from app.models.dashboard_result import (
    DashboardResult,
)
from app.models.page_result import (
    PageResult,
)
from app.services.presupuesto_workspace import (
    SESSION_ROW_ID,
    PresupuestoWorkspace,
)


ZERO = Decimal("0")
CENT = Decimal("0.01")


class PresupuestoWorkspaceAnalysisService:
    MAX_GROUP_COLUMNS = 3

    def __init__(
        self,
        workspace: PresupuestoWorkspace,
    ):
        self._workspace = workspace
        self._config = (
            workspace.module_config
        )

        self._app_columns = (
            *self._config.dimension_columns,
            HABILITADO_COLUMN,
            *self._config.amount_columns,
        )

    @property
    def module_config(
        self,
    ):
        return self._config

    @staticmethod
    def _decimal(value) -> Decimal:
        if value is None:
            return ZERO

        if isinstance(value, Decimal):
            return value

        return Decimal(str(value))

    @staticmethod
    def _text(value) -> str:
        if value is None:
            return ""

        return str(value).strip()

    @staticmethod
    def _is_enabled(row) -> bool:
        return bool(
            row.get(
                HABILITADO_COLUMN,
                True,
            )
        )

    def _dashboard_country_value(
        self,
        row,
    ) -> str:
        column = (
            self._config
            .country_column
        )

        value = (
            self._text(
                row.get(column)
            )
            if column
            else ""
        )

        return (
            value
            or "(Sin pais)"
        )

    def _dashboard_budgeter_value(
        self,
        row,
    ) -> str:
        column = (
            self._config
            .budgeter_column
        )

        value = (
            self._text(
                row.get(column)
            )
            if column
            else ""
        )

        return (
            value
            or "(Sin presupuestador)"
        )

    def _matches_dashboard_filters(
        self,
        row,
        *,
        country_filter=None,
        budgeter_filter=None,
    ) -> bool:
        country = self._text(
            country_filter
        )

        budgeter = self._text(
            budgeter_filter
        )

        if (
            country
            and self._dashboard_country_value(
                row
            ) != country
        ):
            return False

        if (
            budgeter
            and self._dashboard_budgeter_value(
                row
            ) != budgeter
        ):
            return False

        return True

    def get_dashboard_filter_options(
        self,
    ) -> dict[
        str,
        tuple[str, ...],
    ]:
        countries = set()
        budgeters = set()

        for row in (
            self._workspace.iter_rows()
        ):
            if not self._is_enabled(row):
                continue

            countries.add(
                self._dashboard_country_value(
                    row
                )
            )

            budgeters.add(
                self._dashboard_budgeter_value(
                    row
                )
            )

        return {
            "countries": tuple(
                sorted(
                    countries,
                    key=str.casefold,
                )
            ),
            "budgeters": tuple(
                sorted(
                    budgeters,
                    key=str.casefold,
                )
            ),
        }

    def get_page(
        self,
        *,
        page_index: int,
        page_size: int,
        enabled_filter: str = "all",
    ) -> PageResult:
        if page_index < 0:
            raise ValueError(
                "page_index no puede ser negativo."
            )

        if page_size <= 0:
            raise ValueError(
                "page_size debe ser mayor a cero."
            )

        if page_size > 1000:
            raise ValueError(
                "page_size no puede superar 1000."
            )

        filter_value = str(
            enabled_filter
        ).strip().lower()

        valid_filters = {
            "all",
            "enabled",
            "disabled",
        }

        if filter_value not in valid_filters:
            raise ValueError(
                "enabled_filter no valido: "
                f"{enabled_filter}"
            )

        start = (
            page_index
            * page_size
        )

        end = (
            start
            + page_size
        )

        selected_rows = []
        matched_rows = 0

        for row in (
            self._workspace.iter_rows()
        ):
            enabled = (
                self._is_enabled(
                    row
                )
            )

            if (
                filter_value == "enabled"
                and not enabled
            ):
                continue

            if (
                filter_value == "disabled"
                and enabled
            ):
                continue

            current_position = (
                matched_rows
            )

            matched_rows += 1

            if (
                current_position < start
                or
                current_position >= end
            ):
                continue

            item = {
                column:
                    row.get(column)
                for column
                in self._app_columns
            }

            item[
                SESSION_ROW_ID
            ] = row[
                SESSION_ROW_ID
            ]

            selected_rows.append(
                item
            )

        return PageResult(
            rows=tuple(
                selected_rows
            ),
            columns=self._app_columns,
            total_rows=matched_rows,
            page_index=page_index,
            page_size=page_size,
        )

    def get_grouped_totals(
        self,
        group_columns,
        *,
        country_filter=None,
        budgeter_filter=None,
    ) -> AggregationResult:
        columns = tuple(group_columns)

        if not columns:
            raise ValueError(
                "Debe seleccionar al menos "
                "una columna."
            )

        if (
            len(columns)
            > self.MAX_GROUP_COLUMNS
        ):
            raise ValueError(
                "Solo se permiten hasta "
                f"{self.MAX_GROUP_COLUMNS} "
                "niveles de agrupacion."
            )

        if len(columns) != len(set(columns)):
            raise ValueError(
                "No se puede repetir una columna "
                "en la agrupacion."
            )

        invalid = [
            column
            for column in columns
            if column not in self._config.groupable_columns
        ]

        if invalid:
            raise ValueError(
                "Columnas de agrupacion no validas: "
                + ", ".join(invalid)
            )

        groups = {}

        for row in self._workspace.iter_rows():
            if not self._is_enabled(row):
                continue

            if not self._matches_dashboard_filters(
                row,
                country_filter=country_filter,
                budgeter_filter=budgeter_filter,
            ):
                continue

            key = tuple(
                row.get(column)
                for column in columns
            )

            if key not in groups:
                groups[key] = {
                    "registros": 0,
                    **{
                        column: ZERO
                        for column in self._config.amount_columns
                    },
                }

            group = groups[key]

            group["registros"] += 1

            for amount_column in (
                self._config.amount_columns
            ):
                group[amount_column] += (
                    self._decimal(
                        row.get(
                            amount_column
                        )
                    )
                )

        result_rows = []

        for key, values in groups.items():
            item = {
                column: value
                for column, value in zip(
                    columns,
                    key,
                )
            }

            item.update(values)

            result_rows.append(item)

        result_rows.sort(
            key=lambda row: self._decimal(
                row.get(
                    self._config.annual_column
                )
            ),
            reverse=True,
        )

        return AggregationResult(
            rows=tuple(result_rows),
            columns=(
                *columns,
                "registros",
                *self._config.amount_columns,
            ),
            group_columns=columns,
        )

    def get_dashboard(
        self,
        *,
        country_filter=None,
        budgeter_filter=None,
    ) -> DashboardResult:
        total_usd = ZERO
        active_rows = 0

        countries = set()
        budgeters = set()

        monthly_totals = {
            column: ZERO
            for column
            in self._config.month_columns
        }

        by_country = defaultdict(
            lambda: {
                "registros": 0,
                "total_usd": ZERO,
            }
        )

        by_budgeter = defaultdict(
            lambda: {
                "registros": 0,
                "total_usd": ZERO,
            }
        )

        for row in self._workspace.iter_rows():
            if not self._is_enabled(row):
                continue

            if not self._matches_dashboard_filters(
                row,
                country_filter=country_filter,
                budgeter_filter=budgeter_filter,
            ):
                continue

            active_rows += 1

            amount = self._decimal(
                row.get(
                    self._config.annual_column
                )
            )

            total_usd += amount

            for column in (
                self._config.month_columns
            ):
                monthly_totals[
                    column
                ] += self._decimal(
                    row.get(
                        column
                    )
                )

            country = (
                self._dashboard_country_value(
                    row
                )
            )

            budgeter = (
                self._dashboard_budgeter_value(
                    row
                )
            )

            if country != "(Sin pais)":
                countries.add(country)

            if (
                budgeter
                != "(Sin presupuestador)"
            ):
                budgeters.add(
                    budgeter
                )

            by_country[
                country
            ][
                "registros"
            ] += 1

            by_country[
                country
            ][
                "total_usd"
            ] += amount

            by_budgeter[
                budgeter
            ][
                "registros"
            ] += 1

            by_budgeter[
                budgeter
            ][
                "total_usd"
            ] += amount

        country_rows = [
            {
                "pais": country,
                "registros": values[
                    "registros"
                ],
                "total_usd": values[
                    "total_usd"
                ],
            }
            for country, values
            in by_country.items()
        ]

        country_rows.sort(
            key=lambda row: row[
                "total_usd"
            ],
            reverse=True,
        )

        budgeter_rows = [
            {
                "presupuestador":
                    budgeter,
                "registros": values[
                    "registros"
                ],
                "total_usd": values[
                    "total_usd"
                ],
            }
            for budgeter, values
            in by_budgeter.items()
        ]

        budgeter_rows.sort(
            key=lambda row: row[
                "total_usd"
            ],
            reverse=True,
        )

        if active_rows:
            average_usd_per_row = (
                total_usd
                / Decimal(
                    active_rows
                )
            ).quantize(
                CENT,
                rounding=ROUND_HALF_UP,
            )
        else:
            average_usd_per_row = ZERO

        monthly_rows = tuple(
            {
                "column": column,
                "total_usd":
                    monthly_totals[
                        column
                    ],
            }
            for column
            in self._config.month_columns
        )

        return DashboardResult(
            total_usd=total_usd,
            total_rows=active_rows,
            total_countries=len(
                countries
            ),
            total_budgeters=len(
                budgeters
            ),
            by_country=tuple(
                country_rows
            ),
            by_budgeter=tuple(
                budgeter_rows
            ),
            average_usd_per_row=(
                average_usd_per_row
            ),
            monthly_totals=(
                monthly_rows
            ),
        )
