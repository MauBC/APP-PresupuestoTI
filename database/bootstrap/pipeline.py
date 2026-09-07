from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

import pandas as pd

from database.bootstrap.cleaner import (
    CleaningResult,
    clean_dataframe,
)
from database.bootstrap.persistence_enricher import (
    enrich_for_persistence,
    generate_row_id,
)
from database.bootstrap.projector import (
    ProjectionResult,
    project_dataframe,
)
from database.bootstrap.source_loader import (
    load_source,
)


class BootstrapPreparationError(
    ValueError
):
    def __init__(
        self,
        message: str,
        *,
        cleaning_result: CleaningResult | None = None,
    ):
        super().__init__(
            message
        )

        self.cleaning_result = (
            cleaning_result
        )


@dataclass
class BootstrapPreparationResult:
    source_path: Path
    actor: str
    source_row_count: int
    source_column_count: int
    cleaning: CleaningResult
    projection: ProjectionResult
    dataframe: pd.DataFrame

    @property
    def final_row_count(
        self,
    ) -> int:
        return len(
            self.dataframe
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
            ].nunique()
        )


def prepare_budget(
    file_path: str | Path,
    *,
    actor: str,
    sheet_name=0,
    timestamp: datetime | None = None,
    row_id_factory: Callable[
        [],
        str,
    ] = generate_row_id,
) -> BootstrapPreparationResult:
    source_path = (
        Path(file_path)
        .expanduser()
        .resolve()
    )

    source = load_source(
        source_path,
        sheet_name=sheet_name,
    )

    source_row_count = len(
        source
    )

    source_column_count = len(
        source.columns
    )

    cleaning = clean_dataframe(
        source
    )

    if not cleaning.is_valid:
        raise BootstrapPreparationError(
            "El archivo contiene "
            f"{cleaning.stats.error_count} "
            "errores de limpieza.",
            cleaning_result=cleaning,
        )

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

    if (
        len(prepared)
        != source_row_count
    ):
        raise BootstrapPreparationError(
            "La cantidad de filas cambio "
            "durante la preparacion."
        )

    if (
        prepared["row_id"].nunique()
        != len(prepared)
    ):
        raise BootstrapPreparationError(
            "Los row_id finales "
            "no son unicos."
        )

    return BootstrapPreparationResult(
        source_path=source_path,
        actor=str(
            actor
        ).strip(),
        source_row_count=(
            source_row_count
        ),
        source_column_count=(
            source_column_count
        ),
        cleaning=cleaning,
        projection=projection,
        dataframe=prepared,
    )