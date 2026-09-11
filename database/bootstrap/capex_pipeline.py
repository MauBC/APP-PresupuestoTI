from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

import pandas as pd

from app.config.capex_schema import (
    CAPEX_BUSINESS_COLUMNS,
    CAPEX_EXPECTED_COLUMNS,
)
from app.services.capex_excel_loader import (
    CapexExcelLoadResult,
    load_capex_workbook,
)
from database.bootstrap.capex_persistence_enricher import (
    enrich_capex_for_persistence,
)
from database.bootstrap.persistence_enricher import (
    generate_row_id,
)


class CapexBootstrapPreparationError(
    ValueError
):
    pass


@dataclass(
    frozen=True,
    slots=True,
)
class CapexBootstrapPreparationResult:
    source_path: Path
    actor: str
    import_result: CapexExcelLoadResult
    business_dataframe: pd.DataFrame
    dataframe: pd.DataFrame

    @property
    def source_row_count(
        self,
    ) -> int:
        return (
            self.import_result
            .rows_read
        )

    @property
    def final_row_count(
        self,
    ) -> int:
        return len(
            self.dataframe
        )

    @property
    def business_column_count(
        self,
    ) -> int:
        return len(
            self.business_dataframe
            .columns
        )

    @property
    def final_column_count(
        self,
    ) -> int:
        return len(
            self.dataframe.columns
        )

    @property
    def unique_row_id_count(
        self,
    ) -> int:
        return int(
            self.dataframe[
                "row_id"
            ]
            .nunique()
        )


def _build_business_dataframe(
    import_result:
        CapexExcelLoadResult,
) -> pd.DataFrame:
    if (
        import_result.invalid_count
        > 0
    ):
        raise CapexBootstrapPreparationError(
            "El archivo CAPEX contiene "
            f"{import_result.invalid_count} "
            "filas con errores."
        )

    if (
        import_result.rows_read
        < 1
    ):
        raise CapexBootstrapPreparationError(
            "El archivo CAPEX no contiene "
            "filas para cargar."
        )

    records = [
        result.row
        for result
        in import_result.valid_results
    ]

    dataframe = pd.DataFrame(
        records,
        columns=(
            CAPEX_BUSINESS_COLUMNS
        ),
    )

    if (
        len(dataframe)
        != import_result.rows_read
    ):
        raise CapexBootstrapPreparationError(
            "La cantidad de filas CAPEX "
            "cambio durante la preparacion."
        )

    if tuple(
        dataframe.columns
    ) != tuple(
        CAPEX_BUSINESS_COLUMNS
    ):
        raise CapexBootstrapPreparationError(
            "El DataFrame CAPEX de negocio "
            "no tiene el contrato esperado."
        )

    return dataframe


def prepare_capex_bootstrap(
    file_path: str | Path,
    *,
    actor: str,
    expected_year:
        int | None = 2027,
    timestamp:
        datetime | None = None,
    row_id_factory: Callable[
        [],
        str,
    ] = generate_row_id,
) -> CapexBootstrapPreparationResult:
    source_path = (
        Path(file_path)
        .expanduser()
        .resolve()
    )

    actor_value = str(
        actor
    ).strip()

    if not actor_value:
        raise CapexBootstrapPreparationError(
            "El actor CAPEX no puede "
            "estar vacio."
        )

    import_result = (
        load_capex_workbook(
            source_path,
            expected_year=(
                expected_year
            ),
        )
    )

    business_dataframe = (
        _build_business_dataframe(
            import_result
        )
    )

    prepared = (
        enrich_capex_for_persistence(
            business_dataframe,
            actor=actor_value,
            timestamp=timestamp,
            row_id_factory=(
                row_id_factory
            ),
        )
    )

    if tuple(
        prepared.columns
    ) != tuple(
        CAPEX_EXPECTED_COLUMNS
    ):
        raise CapexBootstrapPreparationError(
            "El DataFrame CAPEX final "
            "no tiene las 57 columnas "
            "esperadas."
        )

    if (
        len(prepared)
        != import_result.rows_read
    ):
        raise CapexBootstrapPreparationError(
            "La cantidad de filas CAPEX "
            "cambio al agregar persistencia."
        )

    if (
        prepared[
            "row_id"
        ]
        .nunique()
        != len(
            prepared
        )
    ):
        raise CapexBootstrapPreparationError(
            "Los row_id CAPEX finales "
            "no son unicos."
        )

    return (
        CapexBootstrapPreparationResult(
            source_path=source_path,
            actor=actor_value,
            import_result=(
                import_result
            ),
            business_dataframe=(
                business_dataframe
            ),
            dataframe=prepared,
        )
    )
