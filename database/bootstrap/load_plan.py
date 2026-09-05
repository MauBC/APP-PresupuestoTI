from dataclasses import dataclass

import pandas as pd

from database.bootstrap.persistence_enricher import (
    FINAL_STORAGE_COLUMNS,
    TECHNICAL_COLUMNS,
)


class LoadPlanError(ValueError):
    pass


@dataclass(frozen=True)
class BigQueryLoadPlan:
    project: str
    dataset: str
    table: str
    location: str
    row_count: int
    column_count: int
    write_disposition: str

    @property
    def table_id(self) -> str:
        return (
            f"{self.project}."
            f"{self.dataset}."
            f"{self.table}"
        )


def _required_text(
    value,
    field_name: str,
) -> str:
    text = str(
        value or ""
    ).strip()

    if not text:
        raise LoadPlanError(
            f"{field_name} "
            "no puede estar vacio."
        )

    return text


def build_load_plan(
    dataframe: pd.DataFrame,
    *,
    project: str,
    dataset: str,
    table: str,
    location: str = "US",
) -> BigQueryLoadPlan:
    expected = tuple(
        FINAL_STORAGE_COLUMNS
    )

    actual = tuple(
        dataframe.columns
    )

    if actual != expected:
        raise LoadPlanError(
            "El DataFrame no coincide "
            "con el esquema final de "
            "almacenamiento."
        )

    if dataframe.empty:
        raise LoadPlanError(
            "No se permite cargar "
            "un presupuesto vacio."
        )

    for column in TECHNICAL_COLUMNS:
        if dataframe[
            column
        ].isna().any():
            raise LoadPlanError(
                "Existen valores NULL "
                f"en {column}."
            )

    row_ids = (
        dataframe[
            "row_id"
        ]
        .astype(str)
        .str.strip()
    )

    if (
        row_ids.eq("")
        .any()
    ):
        raise LoadPlanError(
            "Existen row_id vacios."
        )

    if (
        row_ids.nunique()
        != len(dataframe)
    ):
        raise LoadPlanError(
            "Existen row_id duplicados."
        )

    project_value = _required_text(
        project,
        "project",
    )

    dataset_value = _required_text(
        dataset,
        "dataset",
    )

    table_value = _required_text(
        table,
        "table",
    )

    location_value = _required_text(
        location,
        "location",
    )

    return BigQueryLoadPlan(
        project=project_value,
        dataset=dataset_value,
        table=table_value,
        location=location_value,
        row_count=len(
            dataframe
        ),
        column_count=len(
            dataframe.columns
        ),
        write_disposition=(
            "WRITE_TRUNCATE"
        ),
    )