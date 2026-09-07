from dataclasses import dataclass

from google.api_core.exceptions import (
    NotFound,
)
from google.cloud import bigquery

from database.persistence.bigquery_contract import (
    PersistenceTableSpec,
    build_persistence_table_specs,
)


class PersistenceMigrationError(
    RuntimeError
):
    pass


@dataclass(
    frozen=True,
    slots=True,
)
class PersistenceTableMigrationResult:
    table_id: str
    status: str


@dataclass(
    frozen=True,
    slots=True,
)
class PersistenceMigrationResult:
    project: str
    dataset: str
    location: str

    tables: tuple[
        PersistenceTableMigrationResult,
        ...
    ]

    @property
    def created_count(self) -> int:
        return sum(
            result.status == "CREATED"
            for result in self.tables
        )

    @property
    def existing_count(self) -> int:
        return sum(
            result.status == "EXISTS"
            for result in self.tables
        )

    @property
    def pending_count(self) -> int:
        return sum(
            result.status
            == "WOULD_CREATE"
            for result in self.tables
        )


def _required_text(
    value,
    field_name: str,
) -> str:
    text = str(
        value
        if value is not None
        else ""
    ).strip()

    if not text:
        raise PersistenceMigrationError(
            f"{field_name} no puede "
            "estar vacio."
        )

    return text


def _normalized_schema(
    schema,
):
    return tuple(
        (
            field.name,
            field.field_type.upper(),
            field.mode.upper(),
        )
        for field in schema
    )


def validate_existing_table(
    table,
    spec: PersistenceTableSpec,
) -> None:
    expected = _normalized_schema(
        spec.schema
    )

    actual = _normalized_schema(
        table.schema
    )

    if actual == expected:
        return

    expected_map = {
        name: (
            field_type,
            mode,
        )
        for (
            name,
            field_type,
            mode,
        ) in expected
    }

    actual_map = {
        name: (
            field_type,
            mode,
        )
        for (
            name,
            field_type,
            mode,
        ) in actual
    }

    missing = [
        column
        for column in expected_map
        if column not in actual_map
    ]

    extra = [
        column
        for column in actual_map
        if column not in expected_map
    ]

    changed = [
        column
        for column in expected_map
        if (
            column in actual_map
            and actual_map[column]
            != expected_map[column]
        )
    ]

    details = []

    if missing:
        details.append(
            "faltan: "
            + ", ".join(
                missing
            )
        )

    if extra:
        details.append(
            "sobran: "
            + ", ".join(
                extra
            )
        )

    if changed:
        details.append(
            "tipo/modo distinto: "
            + ", ".join(
                changed
            )
        )

    if not details:
        details.append(
            "orden de columnas distinto"
        )

    raise PersistenceMigrationError(
        "La tabla existente "
        f"{table.project}."
        f"{table.dataset_id}."
        f"{table.table_id} "
        "no coincide con el contrato "
        "de persistencia ("
        + "; ".join(
            details
        )
        + ")."
    )


def ensure_persistence_tables(
    client,
    *,
    project: str,
    dataset: str,
    location: str,
    apply: bool = False,
) -> PersistenceMigrationResult:
    project_value = _required_text(
        project,
        "project",
    )

    dataset_value = _required_text(
        dataset,
        "dataset",
    )

    location_value = _required_text(
        location,
        "location",
    ).upper()

    dataset_id = (
        f"{project_value}."
        f"{dataset_value}"
    )

    try:
        dataset_info = (
            client.get_dataset(
                dataset_id
            )
        )

    except NotFound as exc:
        raise PersistenceMigrationError(
            "No existe el dataset: "
            f"{dataset_id}"
        ) from exc

    actual_location = str(
        dataset_info.location
        or ""
    ).strip().upper()

    if (
        actual_location
        and actual_location
        != location_value
    ):
        raise PersistenceMigrationError(
            "La ubicacion del dataset "
            "no coincide con la configuracion: "
            f"{actual_location} != "
            f"{location_value}"
        )

    specs = (
        build_persistence_table_specs()
    )

    existing = {}
    missing = []

    for spec in specs:
        table_id = spec.table_id(
            project=project_value,
            dataset=dataset_value,
        )

        try:
            table = (
                client.get_table(
                    table_id
                )
            )

        except NotFound:
            missing.append(
                spec
            )

            continue

        validate_existing_table(
            table,
            spec,
        )

        existing[
            table_id
        ] = table

    results = []

    for spec in specs:
        table_id = spec.table_id(
            project=project_value,
            dataset=dataset_value,
        )

        if table_id in existing:
            results.append(
                PersistenceTableMigrationResult(
                    table_id=table_id,
                    status="EXISTS",
                )
            )

            continue

        if not apply:
            results.append(
                PersistenceTableMigrationResult(
                    table_id=table_id,
                    status="WOULD_CREATE",
                )
            )

            continue

        table = bigquery.Table(
            table_id,
            schema=list(
                spec.schema
            ),
        )

        client.create_table(
            table,
            exists_ok=True,
        )

        created_table = (
            client.get_table(
                table_id
            )
        )

        validate_existing_table(
            created_table,
            spec,
        )

        results.append(
            PersistenceTableMigrationResult(
                table_id=table_id,
                status="CREATED",
            )
        )

    return PersistenceMigrationResult(
        project=project_value,
        dataset=dataset_value,
        location=location_value,
        tables=tuple(
            results
        ),
    )
