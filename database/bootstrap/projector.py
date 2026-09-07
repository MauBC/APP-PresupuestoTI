from dataclasses import dataclass

import pandas as pd

from database.bootstrap.schema import (
    IGNORED_SOURCE_COLUMNS,
    STORAGE_BUSINESS_COLUMNS,
)


class ProjectionError(ValueError):
    pass


@dataclass(frozen=True)
class ProjectionResult:
    dataframe: pd.DataFrame
    dropped_columns: tuple[str, ...]

    @property
    def row_count(self) -> int:
        return len(
            self.dataframe
        )

    @property
    def column_count(self) -> int:
        return len(
            self.dataframe.columns
        )


def project_dataframe(
    dataframe: pd.DataFrame,
) -> ProjectionResult:
    source = dataframe.copy(
        deep=True
    )

    missing = tuple(
        column
        for column
        in STORAGE_BUSINESS_COLUMNS
        if column not in source.columns
    )

    if missing:
        raise ProjectionError(
            "Faltan columnas de negocio "
            "requeridas para almacenamiento: "
            + ", ".join(missing)
        )

    dropped = tuple(
        column
        for column
        in IGNORED_SOURCE_COLUMNS
        if column in source.columns
    )

    projected = source[
        list(
            STORAGE_BUSINESS_COLUMNS
        )
    ].copy()

    return ProjectionResult(
        dataframe=projected,
        dropped_columns=dropped,
    )