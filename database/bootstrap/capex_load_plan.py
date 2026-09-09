import pandas as pd

from app.config.capex_schema import (
    CAPEX_EXPECTED_COLUMNS,
)
from app.config.presupuesto_schema import (
    PERSISTENCE_COLUMNS,
)
from database.bootstrap.load_plan import (
    BigQueryLoadPlan,
)


class CapexLoadPlanError(
    ValueError
):
    pass


def _required_text(
    value,
    field_name: str,
) -> str:
    text = str(
        value or ""
    ).strip()

    if not text:
        raise CapexLoadPlanError(
            f"{field_name} "
            "no puede estar vacio."
        )

    return text


def build_capex_load_plan(
    dataframe: pd.DataFrame,
    *,
    project: str,
    dataset: str,
    table: str,
    location: str = "US",
) -> BigQueryLoadPlan:
    expected = tuple(
        CAPEX_EXPECTED_COLUMNS
    )

    actual = tuple(
        dataframe.columns
    )

    if actual != expected:
        raise CapexLoadPlanError(
            "El DataFrame CAPEX no coincide "
            "con el esquema final de "
            "almacenamiento."
        )

    if dataframe.empty:
        raise CapexLoadPlanError(
            "No se permite cargar "
            "un CAPEX vacio."
        )

    for column in (
        PERSISTENCE_COLUMNS
    ):
        if dataframe[
            column
        ].isna().any():
            raise CapexLoadPlanError(
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
        raise CapexLoadPlanError(
            "Existen row_id CAPEX vacios."
        )

    if (
        row_ids.nunique()
        != len(
            dataframe
        )
    ):
        raise CapexLoadPlanError(
            "Existen row_id CAPEX "
            "duplicados."
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
