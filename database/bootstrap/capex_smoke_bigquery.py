from dataclasses import dataclass

from google.cloud import bigquery

from database.bootstrap.capex_bigquery_contract import (
    build_capex_append_load_config,
)
from database.bootstrap.capex_smoke_validation import (
    CapexSmokeMetrics,
    validate_capex_smoke_metrics,
)
from database.migrations.capex_main_table import (
    capex_schema_matches,
)


class CapexSmokeBigQueryError(
    RuntimeError
):
    pass


@dataclass(
    frozen=True,
    slots=True,
)
class CapexSmokeBigQueryResult:
    table_id: str
    rows_loaded: int
    selected_rows: int
    unique_row_ids: int
    disabled_rows: int
    min_version: int
    max_version: int
    preexisting_rows: int
    final_rows: int
    cleanup_ok: bool


def _table_row_count(
    client,
    *,
    table_id: str,
    location: str,
) -> int:
    sql = f"""
        SELECT
            COUNT(*) AS total_rows
        FROM `{table_id}`
    """

    row = next(
        iter(
            client.query(
                sql,
                location=location,
            ).result()
        )
    )

    return int(
        row.total_rows
    )


def _read_smoke_metrics(
    client,
    *,
    table_id: str,
    location: str,
    row_ids: list[str],
) -> CapexSmokeMetrics:
    sql = f"""
        SELECT
            COUNT(*) AS selected_rows,
            COUNT(
                DISTINCT row_id
            ) AS unique_row_ids,
            COUNTIF(
                habilitado = FALSE
            ) AS disabled_rows,
            MIN(version) AS min_version,
            MAX(version) AS max_version

        FROM `{table_id}`

        WHERE row_id IN UNNEST(
            @row_ids
        )
    """

    config = (
        bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ArrayQueryParameter(
                    "row_ids",
                    "STRING",
                    row_ids,
                )
            ]
        )
    )

    row = next(
        iter(
            client.query(
                sql,
                job_config=config,
                location=location,
            ).result()
        )
    )

    return CapexSmokeMetrics(
        selected_rows=int(
            row.selected_rows
        ),
        unique_row_ids=int(
            row.unique_row_ids
        ),
        disabled_rows=int(
            row.disabled_rows
        ),
        min_version=(
            None
            if row.min_version is None
            else int(
                row.min_version
            )
        ),
        max_version=(
            None
            if row.max_version is None
            else int(
                row.max_version
            )
        ),
    )


def _delete_smoke_rows(
    client,
    *,
    table_id: str,
    location: str,
    row_ids: list[str],
):
    sql = f"""
        DELETE FROM `{table_id}`
        WHERE row_id IN UNNEST(
            @row_ids
        )
    """

    config = (
        bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ArrayQueryParameter(
                    "row_ids",
                    "STRING",
                    row_ids,
                )
            ]
        )
    )

    client.query(
        sql,
        job_config=config,
        location=location,
    ).result()


def run_capex_bigquery_smoke_test(
    client,
    dataframe,
    *,
    table_id: str,
    location: str,
) -> CapexSmokeBigQueryResult:
    if dataframe.empty:
        raise CapexSmokeBigQueryError(
            "El smoke test CAPEX "
            "no contiene filas."
        )

    table = client.get_table(
        table_id
    )

    if not capex_schema_matches(
        table.schema
    ):
        raise CapexSmokeBigQueryError(
            "El schema remoto CAPEX "
            "no coincide con el contrato."
        )

    preexisting_rows = (
        _table_row_count(
            client,
            table_id=table_id,
            location=location,
        )
    )

    if preexisting_rows != 0:
        raise CapexSmokeBigQueryError(
            "La tabla CAPEX debe estar "
            "vacia antes del smoke test. "
            f"Filas actuales="
            f"{preexisting_rows}."
        )

    row_ids = [
        str(value)
        for value in (
            dataframe[
                "row_id"
            ]
            .tolist()
        )
    ]

    if (
        len(
            set(
                row_ids
            )
        )
        != len(
            row_ids
        )
    ):
        raise CapexSmokeBigQueryError(
            "El DataFrame del smoke test "
            "contiene row_id duplicados."
        )

    loaded = False
    metrics = None
    validation_error = None

    try:
        load_job = (
            client
            .load_table_from_dataframe(
                dataframe,
                table_id,
                job_config=(
                    build_capex_append_load_config()
                ),
                location=location,
            )
        )

        load_job.result()

        loaded = True

        metrics = (
            _read_smoke_metrics(
                client,
                table_id=table_id,
                location=location,
                row_ids=row_ids,
            )
        )

        try:
            validate_capex_smoke_metrics(
                metrics,
                expected_rows=len(
                    dataframe
                ),
            )

        except Exception as exc:
            validation_error = exc

    finally:
        if loaded:
            _delete_smoke_rows(
                client,
                table_id=table_id,
                location=location,
                row_ids=row_ids,
            )

    final_rows = (
        _table_row_count(
            client,
            table_id=table_id,
            location=location,
        )
    )

    cleanup_ok = (
        final_rows
        == preexisting_rows
    )

    if not cleanup_ok:
        raise CapexSmokeBigQueryError(
            "El cleanup del smoke test "
            "no restauro la tabla. "
            f"Antes={preexisting_rows}; "
            f"despues={final_rows}."
        )

    if validation_error is not None:
        raise CapexSmokeBigQueryError(
            "La validacion del smoke test "
            "fallo, pero las filas temporales "
            "fueron eliminadas."
        ) from validation_error

    if metrics is None:
        raise CapexSmokeBigQueryError(
            "No se obtuvieron metricas "
            "del smoke test."
        )

    return CapexSmokeBigQueryResult(
        table_id=table_id,
        rows_loaded=len(
            dataframe
        ),
        selected_rows=(
            metrics.selected_rows
        ),
        unique_row_ids=(
            metrics.unique_row_ids
        ),
        disabled_rows=(
            metrics.disabled_rows
        ),
        min_version=int(
            metrics.min_version
        ),
        max_version=int(
            metrics.max_version
        ),
        preexisting_rows=(
            preexisting_rows
        ),
        final_rows=final_rows,
        cleanup_ok=cleanup_ok,
    )
