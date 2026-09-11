from dataclasses import dataclass

from google.cloud import bigquery
from google.api_core.exceptions import NotFound

from database.bootstrap.capex_bigquery_contract import (
    build_capex_bigquery_schema,
)


class CapexMainTableError(
    RuntimeError
):
    pass


@dataclass(
    frozen=True,
    slots=True,
)
class CapexMainTableStatus:
    table_id: str
    exists: bool
    schema_matches: bool
    created: bool
    column_count: int


def build_capex_table_id(
    *,
    project: str,
    dataset: str,
    table: str,
) -> str:
    project_value = str(
        project or ""
    ).strip()

    dataset_value = str(
        dataset or ""
    ).strip()

    table_value = str(
        table or ""
    ).strip()

    if not project_value:
        raise CapexMainTableError(
            "project no puede estar vacio."
        )

    if not dataset_value:
        raise CapexMainTableError(
            "dataset no puede estar vacio."
        )

    if not table_value:
        raise CapexMainTableError(
            "table no puede estar vacio."
        )

    return (
        f"{project_value}."
        f"{dataset_value}."
        f"{table_value}"
    )


def _schema_signature(
    schema,
) -> tuple[
    tuple[
        str,
        str,
        str,
    ],
    ...
]:
    return tuple(
        sorted(
            (
                field.name,
                field.field_type,
                field.mode,
            )
            for field in schema
        )
    )


def capex_schema_matches(
    schema,
) -> bool:
    expected = (
        build_capex_bigquery_schema()
    )

    return (
        _schema_signature(
            schema
        )
        ==
        _schema_signature(
            expected
        )
    )


def inspect_capex_main_table(
    client,
    *,
    project: str,
    dataset: str,
    table: str,
) -> CapexMainTableStatus:
    table_id = (
        build_capex_table_id(
            project=project,
            dataset=dataset,
            table=table,
        )
    )

    try:
        remote_table = (
            client.get_table(
                table_id
            )
        )

    except NotFound:
        return CapexMainTableStatus(
            table_id=table_id,
            exists=False,
            schema_matches=False,
            created=False,
            column_count=0,
        )

    schema = tuple(
        remote_table.schema
    )

    return CapexMainTableStatus(
        table_id=table_id,
        exists=True,
        schema_matches=(
            capex_schema_matches(
                schema
            )
        ),
        created=False,
        column_count=len(
            schema
        ),
    )


def ensure_capex_main_table(
    client,
    *,
    project: str,
    dataset: str,
    table: str,
    location: str,
    apply: bool = False,
) -> CapexMainTableStatus:
    table_id = (
        build_capex_table_id(
            project=project,
            dataset=dataset,
            table=table,
        )
    )

    dataset_id = (
        f"{str(project).strip()}."
        f"{str(dataset).strip()}"
    )

    try:
        dataset_info = (
            client.get_dataset(
                dataset_id
            )
        )

    except NotFound as exc:
        raise CapexMainTableError(
            "El dataset no existe: "
            f"{dataset_id}"
        ) from exc

    expected_location = str(
        location or ""
    ).strip()

    actual_location = str(
        getattr(
            dataset_info,
            "location",
            "",
        )
        or ""
    ).strip()

    if (
        expected_location
        and actual_location
        and (
            expected_location.upper()
            != actual_location.upper()
        )
    ):
        raise CapexMainTableError(
            "La location del dataset "
            "no coincide con la configuracion. "
            f"Dataset={actual_location}; "
            f"config={expected_location}."
        )

    current = (
        inspect_capex_main_table(
            client,
            project=project,
            dataset=dataset,
            table=table,
        )
    )

    if current.exists:
        if not current.schema_matches:
            raise CapexMainTableError(
                "La tabla CAPEX ya existe "
                "pero su schema no coincide "
                "con el contrato esperado."
            )

        return current

    if not apply:
        return current

    schema = list(
        build_capex_bigquery_schema()
    )

    table_resource = (
        bigquery.Table(
            table_id,
            schema=schema,
        )
    )

    created_table = (
        client.create_table(
            table_resource
        )
    )

    if not capex_schema_matches(
        created_table.schema
    ):
        raise CapexMainTableError(
            "La tabla fue creada, pero "
            "el schema devuelto no coincide "
            "con el contrato CAPEX."
        )

    return CapexMainTableStatus(
        table_id=table_id,
        exists=True,
        schema_matches=True,
        created=True,
        column_count=len(
            created_table.schema
        ),
    )
