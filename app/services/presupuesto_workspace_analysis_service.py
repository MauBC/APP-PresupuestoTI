from collections import defaultdict
from decimal import Decimal

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

    def get_page(
        self,
        *,
        page_index: int,
        page_size: int,
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

        start = page_index * page_size
        end = start + page_size

        selected_rows = []

        for index, row in enumerate(
            self._workspace.iter_rows()
        ):
            if index < start:
                continue

            if index >= end:
                break

            item = {
                column: row.get(column)
                for column in self._app_columns
            }

            item[SESSION_ROW_ID] = row[
                SESSION_ROW_ID
            ]

            selected_rows.append(item)

        return PageResult(
            rows=tuple(selected_rows),
            columns=self._app_columns,
            total_rows=self._workspace.row_count,
            page_index=page_index,
            page_size=page_size,
        )

    def get_grouped_totals(
        self,
        group_columns,
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
    ) -> DashboardResult:
        total_usd = ZERO
        active_rows = 0

        countries = set()
        budgeters = set()

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

            active_rows += 1

            amount = self._decimal(
                row.get(
                    self._config.annual_column
                )
            )

            total_usd += amount

            country_column = (
                self._config
                .country_column
            )

            budgeter_column = (
                self._config
                .budgeter_column
            )

            country = (
                self._text(
                    row.get(
                        country_column
                    )
                )
                if country_column
                else ""
            )

            country = (
                country
                or "(Sin pais)"
            )

            budgeter = (
                self._text(
                    row.get(
                        budgeter_column
                    )
                )
                if budgeter_column
                else ""
            )

            budgeter = (
                budgeter
                or "(Sin presupuestador)"
            )

            if country != "(Sin pais)":
                countries.add(country)

            if (
                budgeter
                != "(Sin presupuestador)"
            ):
                budgeters.add(budgeter)

            by_country[country][
                "registros"
            ] += 1

            by_country[country][
                "total_usd"
            ] += amount

            by_budgeter[budgeter][
                "registros"
            ] += 1

            by_budgeter[budgeter][
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
                "presupuestador": budgeter,
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

        return DashboardResult(
            total_usd=total_usd,
            total_rows=active_rows,
            total_countries=len(countries),
            total_budgeters=len(budgeters),
            by_country=tuple(country_rows),
            by_budgeter=tuple(
                budgeter_rows
            ),
        )
