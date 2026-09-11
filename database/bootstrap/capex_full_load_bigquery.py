from dataclasses import dataclass

from google.cloud import bigquery

from database.bootstrap.capex_bigquery_contract import (
    build_capex_append_load_config,
)
from database.bootstrap.capex_full_load_validation import (
    CapexFullLoadMetrics,
    validate_capex_full_load_metrics,
)
from database.migrations.capex_main_table import (
    capex_schema_matches,
)


class CapexFullLoadBigQueryError(
    RuntimeError
):
    pass


@dataclass(
    frozen=True,
    slots=True,
)
class CapexFullLoadBigQueryResult:
    table_id: str
    rows_loaded: int
    total_rows: int
    unique_row_ids: int
    disabled_rows: int
    min_version: int
    max_version: int
    years: tuple[
        int,
        ...
    ]


def get_capex_table_row_count(
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


def read_capex_full_load_metrics(
    client,
    *,
    table_id: str,
    location: str,
) -> CapexFullLoadMetrics:
    sql = f"""
        SELECT
            COUNT(*) AS total_rows,

            COUNT(
                DISTINCT row_id
            ) AS unique_row_ids,

            COUNTIF(
                habilitado = FALSE
            ) AS disabled_rows,

            MIN(
                version
            ) AS min_version,

            MAX(
                version
            ) AS max_version,

            ARRAY(
                SELECT DISTINCT
                    anio
                FROM `{table_id}`
                WHERE anio IS NOT NULL
                ORDER BY anio
            ) AS years

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

    years = tuple(
        int(
            value
        )
        for value
        in (
            row.years
            or ()
        )
    )

    return CapexFullLoadMetrics(
        total_rows=int(
            row.total_rows
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
        years=years,
    )


def delete_capex_rows(
    client,
    *,
    table_id: str,
    location: str,
    row_ids: list[str],
) -> None:
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


def run_capex_full_load(
    client,
    dataframe,
    *,
    table_id: str,
    location: str,
    expected_rows: int,
    expected_year: int | None,
) -> CapexFullLoadBigQueryResult:
    if dataframe.empty:
        raise CapexFullLoadBigQueryError(
            "El DataFrame CAPEX "
            "esta vacio."
        )

    if (
        len(
            dataframe
        )
        != expected_rows
    ):
        raise CapexFullLoadBigQueryError(
            "El DataFrame CAPEX no tiene "
            "la cantidad esperada. "
            f"Esperadas={expected_rows}; "
            f"encontradas="
            f"{len(dataframe)}."
        )

    table = client.get_table(
        table_id
    )

    if not capex_schema_matches(
        table.schema
    ):
        raise CapexFullLoadBigQueryError(
            "El schema remoto CAPEX "
            "no coincide con el contrato."
        )

    preexisting_rows = (
        get_capex_table_row_count(
            client,
            table_id=table_id,
            location=location,
        )
    )

    if preexisting_rows != 0:
        raise CapexFullLoadBigQueryError(
            "La tabla CAPEX debe estar "
            "vacia antes de la carga "
            "completa. "
            f"Filas actuales="
            f"{preexisting_rows}."
        )

    row_ids = [
        str(
            value
        ).strip()
        for value
        in (
            dataframe[
                "row_id"
            ]
            .tolist()
        )
    ]

    if any(
        not row_id
        for row_id
        in row_ids
    ):
        raise CapexFullLoadBigQueryError(
            "Existen row_id CAPEX "
            "vacios."
        )

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
        raise CapexFullLoadBigQueryError(
            "El DataFrame CAPEX "
            "contiene row_id duplicados."
        )

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

    try:
        metrics = (
            read_capex_full_load_metrics(
                client,
                table_id=table_id,
                location=location,
            )
        )

        validate_capex_full_load_metrics(
            metrics,
            expected_rows=expected_rows,
            expected_year=expected_year,
        )

    except Exception as exc:
        cleanup_error = None

        try:
            delete_capex_rows(
                client,
                table_id=table_id,
                location=location,
                row_ids=row_ids,
            )

            remaining_rows = (
                get_capex_table_row_count(
                    client,
                    table_id=table_id,
                    location=location,
                )
            )

            if remaining_rows != 0:
                cleanup_error = RuntimeError(
                    "El cleanup automatico "
                    "no dejo la tabla vacia. "
                    f"Filas restantes="
                    f"{remaining_rows}."
                )

        except Exception as delete_exc:
            cleanup_error = (
                delete_exc
            )

        if cleanup_error is not None:
            raise CapexFullLoadBigQueryError(
                "La validacion de la carga "
                "CAPEX fallo y tambien fallo "
                "el cleanup automatico."
            ) from cleanup_error

        raise CapexFullLoadBigQueryError(
            "La validacion de la carga "
            "CAPEX fallo. Las filas de "
            "esta carga fueron eliminadas."
        ) from exc

    return CapexFullLoadBigQueryResult(
        table_id=table_id,
        rows_loaded=len(
            dataframe
        ),
        total_rows=(
            metrics.total_rows
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
        years=(
            metrics.years
        ),
    )
