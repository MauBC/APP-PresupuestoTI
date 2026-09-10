
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pandas as pd

from app.config.budget_module_config import (
    BudgetModule,
)
from app.config.capex_schema import (
    CAPEX_BUSINESS_COLUMNS,
    CAPEX_EXCEL_SHEET,
    CAPEX_EXPECTED_YEAR,
)
from app.models.budget_excel_import import (
    BudgetExcelImportResult,
    BudgetImportIssue,
    BudgetImportIssueSeverity,
)
from app.services.capex_excel_loader import (
    CapexWorkbookError,
    load_capex_workbook,
)
from database.bootstrap.capex_persistence_enricher import (
    enrich_capex_for_persistence,
)
from database.bootstrap.cleaner import (
    CleaningError,
    clean_dataframe,
)
from database.bootstrap.persistence_enricher import (
    enrich_for_persistence,
    generate_row_id,
)
from database.bootstrap.projector import (
    ProjectionError,
    project_dataframe,
)
from database.bootstrap.source_loader import (
    SourceLoadError,
    load_source,
)


TECHNICAL_COLUMNS = (
    "row_id",
    "habilitado",
    "version",
    "created_at",
    "created_by",
    "updated_at",
    "updated_by",
)


class BudgetExcelImportError(
    ValueError
):
    pass


class BudgetExcelImportService:
    def __init__(
        self,
        module_config,
    ):
        self._config = (
            module_config
        )

    @property
    def module_config(
        self,
    ):
        return self._config

    def prepare(
        self,
        file_path,
        *,
        actor: str,
        sheet_name=None,
        expected_year=CAPEX_EXPECTED_YEAR,
        timestamp: datetime | None = None,
        row_id_factory=generate_row_id,
    ) -> BudgetExcelImportResult:
        actor_value = str(
            actor
            if actor is not None
            else ""
        ).strip()

        if not actor_value:
            raise BudgetExcelImportError(
                "actor no puede estar vacio."
            )

        source = (
            Path(file_path)
            .expanduser()
            .resolve()
        )

        if not source.exists():
            raise BudgetExcelImportError(
                "No existe el archivo: "
                f"{source}"
            )

        module = (
            self._config
            .module
        )

        if module == BudgetModule.OPEX:
            return self._prepare_opex(
                source,
                actor=actor_value,
                sheet_name=(
                    0
                    if sheet_name is None
                    else sheet_name
                ),
                timestamp=timestamp,
                row_id_factory=(
                    row_id_factory
                ),
            )

        if module == BudgetModule.CAPEX:
            return self._prepare_capex(
                source,
                actor=actor_value,
                sheet_name=(
                    CAPEX_EXCEL_SHEET
                    if sheet_name is None
                    else str(
                        sheet_name
                    )
                ),
                expected_year=(
                    expected_year
                ),
                timestamp=timestamp,
                row_id_factory=(
                    row_id_factory
                ),
            )

        raise BudgetExcelImportError(
            "Modulo no soportado para "
            f"importacion: {module}"
        )

    def _prepare_opex(
        self,
        source,
        *,
        actor,
        sheet_name,
        timestamp,
        row_id_factory,
    ):
        try:
            dataframe = load_source(
                source,
                sheet_name=sheet_name,
            )

            source_row_count = len(
                dataframe
            )

            source_column_count = len(
                dataframe.columns
            )

            cleaning = clean_dataframe(
                dataframe
            )

        except (
            SourceLoadError,
            CleaningError,
        ) as exc:
            raise BudgetExcelImportError(
                str(exc)
            ) from exc

        issues = [
            BudgetImportIssue(
                row_number=(
                    issue.row_number
                ),
                column=(
                    issue.column
                ),
                code="INVALID_VALUE",
                message=(
                    issue.message
                ),
                severity=(
                    BudgetImportIssueSeverity
                    .ERROR
                ),
                raw_value=(
                    issue.value
                ),
            )
            for issue in (
                cleaning.issues
            )
        ]

        for column in (
            cleaning.extra_columns
        ):
            issues.append(
                BudgetImportIssue(
                    row_number=1,
                    column=column,
                    code="EXTRA_COLUMN",
                    message=(
                        "La columna no forma "
                        "parte del contrato OPEX "
                        "y sera ignorada."
                    ),
                    severity=(
                        BudgetImportIssueSeverity
                        .INFO
                    ),
                )
            )

        if source_row_count < 1:
            issues.append(
                BudgetImportIssue(
                    row_number=0,
                    column="",
                    code="EMPTY_FILE",
                    message=(
                        "El archivo no contiene "
                        "filas para importar."
                    ),
                    severity=(
                        BudgetImportIssueSeverity
                        .ERROR
                    ),
                )
            )

        if any(
            issue.severity
            == BudgetImportIssueSeverity.ERROR
            for issue in issues
        ):
            return BudgetExcelImportResult(
                module="OPEX",
                source_path=str(
                    source
                ),
                sheet_name=str(
                    sheet_name
                ),
                rows_read=(
                    source_row_count
                ),
                source_column_count=(
                    source_column_count
                ),
                rows=(),
                issues=tuple(
                    issues
                ),
            )

        try:
            projection = (
                project_dataframe(
                    cleaning.dataframe
                )
            )

            prepared = (
                enrich_for_persistence(
                    projection.dataframe,
                    actor=actor,
                    timestamp=timestamp,
                    row_id_factory=(
                        row_id_factory
                    ),
                )
            )

        except ProjectionError as exc:
            raise BudgetExcelImportError(
                str(exc)
            ) from exc

        rows = self._records(
            prepared
        )

        self._validate_prepared_rows(
            rows
        )

        return BudgetExcelImportResult(
            module="OPEX",
            source_path=str(
                source
            ),
            sheet_name=str(
                sheet_name
            ),
            rows_read=(
                source_row_count
            ),
            source_column_count=(
                source_column_count
            ),
            rows=rows,
            issues=tuple(
                issues
            ),
        )

    def _prepare_capex(
        self,
        source,
        *,
        actor,
        sheet_name,
        expected_year,
        timestamp,
        row_id_factory,
    ):
        try:
            import_result = (
                load_capex_workbook(
                    source,
                    expected_year=(
                        expected_year
                    ),
                    sheet_name=(
                        sheet_name
                    ),
                )
            )

        except CapexWorkbookError as exc:
            raise BudgetExcelImportError(
                str(exc)
            ) from exc

        issues = tuple(
            BudgetImportIssue(
                row_number=(
                    issue.row_number
                ),
                column=(
                    issue.column
                ),
                code=(
                    issue.code
                ),
                message=(
                    issue.message
                ),
                severity=(
                    BudgetImportIssueSeverity(
                        issue.severity.value
                    )
                ),
                raw_value=(
                    issue.raw_value
                ),
            )
            for issue in (
                import_result.issues
            )
        )

        if import_result.rows_read < 1:
            issues = (
                *issues,
                BudgetImportIssue(
                    row_number=0,
                    column="",
                    code="EMPTY_FILE",
                    message=(
                        "El archivo no contiene "
                        "filas CAPEX para importar."
                    ),
                    severity=(
                        BudgetImportIssueSeverity
                        .ERROR
                    ),
                ),
            )

        if any(
            issue.severity
            == BudgetImportIssueSeverity.ERROR
            for issue in issues
        ):
            return BudgetExcelImportResult(
                module="CAPEX",
                source_path=str(
                    source
                ),
                sheet_name=(
                    import_result.sheet_name
                ),
                rows_read=(
                    import_result.rows_read
                ),
                source_column_count=(
                    len(
                        CAPEX_BUSINESS_COLUMNS
                    )
                ),
                rows=(),
                issues=issues,
            )

        records = [
            result.row
            for result in (
                import_result
                .valid_results
            )
        ]

        business_dataframe = (
            pd.DataFrame(
                records,
                columns=(
                    CAPEX_BUSINESS_COLUMNS
                ),
            )
        )

        prepared = (
            enrich_capex_for_persistence(
                business_dataframe,
                actor=actor,
                timestamp=timestamp,
                row_id_factory=(
                    row_id_factory
                ),
            )
        )

        rows = self._records(
            prepared
        )

        self._validate_prepared_rows(
            rows
        )

        return BudgetExcelImportResult(
            module="CAPEX",
            source_path=str(
                source
            ),
            sheet_name=(
                import_result.sheet_name
            ),
            rows_read=(
                import_result.rows_read
            ),
            source_column_count=(
                len(
                    CAPEX_BUSINESS_COLUMNS
                )
            ),
            rows=rows,
            issues=issues,
        )

    def _validate_prepared_rows(
        self,
        rows,
    ):
        if not rows:
            raise BudgetExcelImportError(
                "No existen filas preparadas."
            )

        required = {
            *self._config
            .insert_columns,
            *TECHNICAL_COLUMNS,
        }

        seen = set()

        for index, row in enumerate(
            rows,
            start=1,
        ):
            missing = (
                required
                - set(row)
            )

            if missing:
                raise BudgetExcelImportError(
                    "Fila preparada "
                    f"{index} incompleta: "
                    + ", ".join(
                        sorted(missing)
                    )
                )

            row_id = str(
                row.get(
                    "row_id",
                    "",
                )
                or ""
            ).strip()

            if not row_id:
                raise BudgetExcelImportError(
                    "Existe una fila preparada "
                    "sin row_id."
                )

            if row_id in seen:
                raise BudgetExcelImportError(
                    "Se generaron row_id "
                    "duplicados."
                )

            seen.add(
                row_id
            )

            if (
                row.get("version")
                != 1
            ):
                raise BudgetExcelImportError(
                    "Toda fila importada debe "
                    "iniciar con version 1."
                )

    @classmethod
    def _records(
        cls,
        dataframe,
    ):
        return tuple(
            {
                column:
                    cls._python_value(
                        value
                    )
                for column, value
                in record.items()
            }
            for record in (
                dataframe
                .to_dict(
                    orient="records"
                )
            )
        )

    @staticmethod
    def _python_value(
        value,
    ):
        if value is None:
            return None

        if isinstance(
            value,
            Decimal,
        ):
            return value

        try:
            missing = pd.isna(
                value
            )

            if (
                isinstance(
                    missing,
                    bool,
                )
                and missing
            ):
                return None

        except (
            TypeError,
            ValueError,
        ):
            pass

        if hasattr(
            value,
            "to_pydatetime",
        ):
            try:
                return (
                    value
                    .to_pydatetime()
                )
            except Exception:
                pass

        if (
            hasattr(
                value,
                "item",
            )
            and not isinstance(
                value,
                (
                    str,
                    bytes,
                ),
            )
        ):
            try:
                return value.item()
            except Exception:
                pass

        return value
