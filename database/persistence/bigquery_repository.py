from datetime import datetime
from decimal import Decimal
from typing import Iterable

from google.cloud import bigquery

from app.config.settings import settings
from database.persistence.bigquery_contract import (
    build_staging_schema,
)
from database.persistence.contract import (
    PENDING_STATUS,
    STAGING_COLUMNS,
)
from database.persistence.models import (
    PersistenceBatch,
    StagingRow,
)


class BigQueryPersistenceError(
    RuntimeError
):
    pass


class BigQueryPersistenceRepository:
    def __init__(
        self,
        client,
        *,
        project: str | None = None,
        dataset: str | None = None,
        location: str | None = None,
    ):
        self._client = client

        self._project = self._required_text(
            project
            if project is not None
            else settings.GOOGLE_CLOUD_PROJECT,
            "project",
        )

        self._dataset = self._required_text(
            dataset
            if dataset is not None
            else settings.BIGQUERY_DATASET,
            "dataset",
        )

        self._location = self._required_text(
            location
            if location is not None
            else settings.BIGQUERY_LOCATION,
            "location",
        )

    @property
    def main_table_id(
        self,
    ) -> str:
        return self._table_id(
            settings.BIGQUERY_TABLE
        )

    @property
    def batch_table_id(
        self,
    ) -> str:
        return self._table_id(
            settings.BIGQUERY_BATCH_TABLE
        )

    @property
    def audit_table_id(
        self,
    ) -> str:
        return self._table_id(
            settings.BIGQUERY_AUDIT_TABLE
        )

    @property
    def staging_table_id(
        self,
    ) -> str:
        return self._table_id(
            settings.BIGQUERY_STAGING_TABLE
        )

    @property
    def location(
        self,
    ) -> str:
        return self._location

    def insert_pending_batch(
        self,
        batch: PersistenceBatch,
    ) -> int | None:
        if (
            batch.status
            != PENDING_STATUS
        ):
            raise BigQueryPersistenceError(
                "Solo se puede registrar "
                "un batch PENDING."
            )

        if batch.row_count < 1:
            raise BigQueryPersistenceError(
                "El batch no contiene filas."
            )

        if batch.field_count < 1:
            raise BigQueryPersistenceError(
                "El batch no contiene cambios."
            )

        sql = f"""
            INSERT INTO `{self.batch_table_id}` (
                batch_id,
                status,
                actor,
                created_at,
                completed_at,
                row_count,
                field_count,
                app_version,
                error_message
            )

            SELECT
                @batch_id,
                @status,
                @actor,
                @created_at,
                NULL,
                @row_count,
                @field_count,
                @app_version,
                NULL

            WHERE NOT EXISTS (
                SELECT 1
                FROM `{self.batch_table_id}`
                WHERE batch_id = @batch_id
            )
        """

        job_config = (
            bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter(
                        "batch_id",
                        "STRING",
                        batch.batch_id,
                    ),
                    bigquery.ScalarQueryParameter(
                        "status",
                        "STRING",
                        batch.status,
                    ),
                    bigquery.ScalarQueryParameter(
                        "actor",
                        "STRING",
                        batch.actor,
                    ),
                    bigquery.ScalarQueryParameter(
                        "created_at",
                        "TIMESTAMP",
                        batch.created_at,
                    ),
                    bigquery.ScalarQueryParameter(
                        "row_count",
                        "INT64",
                        batch.row_count,
                    ),
                    bigquery.ScalarQueryParameter(
                        "field_count",
                        "INT64",
                        batch.field_count,
                    ),
                    bigquery.ScalarQueryParameter(
                        "app_version",
                        "STRING",
                        batch.app_version,
                    ),
                ]
            )
        )

        job = self._client.query(
            sql,
            job_config=job_config,
            location=self._location,
        )

        job.result()

        return getattr(
            job,
            "num_dml_affected_rows",
            None,
        )

    def clear_staging(
        self,
        batch_id: str,
    ) -> int | None:
        batch_id_value = (
            self._required_text(
                batch_id,
                "batch_id",
            )
        )

        sql = f"""
            DELETE FROM `{self.staging_table_id}`
            WHERE batch_id = @batch_id
        """

        job_config = (
            bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter(
                        "batch_id",
                        "STRING",
                        batch_id_value,
                    )
                ]
            )
        )

        job = self._client.query(
            sql,
            job_config=job_config,
            location=self._location,
        )

        job.result()

        return getattr(
            job,
            "num_dml_affected_rows",
            None,
        )

    def load_staging_rows(
        self,
        rows: Iterable[
            StagingRow
        ],
    ) -> int:
        staging_rows = tuple(
            rows
        )

        self._validate_staging_rows(
            staging_rows
        )

        records = [
            self._staging_record(
                row
            )
            for row in staging_rows
        ]

        job_config = (
            bigquery.LoadJobConfig()
        )

        job_config.schema = list(
            build_staging_schema()
        )

        job_config.write_disposition = (
            bigquery.WriteDisposition
            .WRITE_APPEND
        )

        job = (
            self._client
            .load_table_from_json(
                records,
                self.staging_table_id,
                job_config=job_config,
                location=self._location,
            )
        )

        job.result()

        output_rows = getattr(
            job,
            "output_rows",
            None,
        )

        if output_rows is None:
            return len(
                records
            )

        return int(
            output_rows
        )

    def replace_staging_rows(
        self,
        rows: Iterable[
            StagingRow
        ],
    ) -> int:
        staging_rows = tuple(
            rows
        )

        self._validate_staging_rows(
            staging_rows
        )

        batch_id = (
            staging_rows[0]
            .batch_id
        )

        self.clear_staging(
            batch_id
        )

        return self.load_staging_rows(
            staging_rows
        )

    def count_staging_rows(
        self,
        batch_id: str,
    ) -> int:
        batch_id_value = (
            self._required_text(
                batch_id,
                "batch_id",
            )
        )

        sql = f"""
            SELECT
                COUNT(*) AS row_count
            FROM `{self.staging_table_id}`
            WHERE batch_id = @batch_id
        """

        job_config = (
            bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter(
                        "batch_id",
                        "STRING",
                        batch_id_value,
                    )
                ]
            )
        )

        result = (
            self._client.query(
                sql,
                job_config=job_config,
                location=self._location,
            )
            .result()
        )

        row = next(
            iter(result)
        )

        try:
            value = row[
                "row_count"
            ]

        except (
            KeyError,
            TypeError,
        ):
            value = getattr(
                row,
                "row_count",
            )

        return int(
            value
        )

    def _validate_staging_rows(
        self,
        rows: tuple[
            StagingRow,
            ...
        ],
    ) -> None:
        if not rows:
            raise BigQueryPersistenceError(
                "No existen filas "
                "para staging."
            )

        batch_ids = {
            row.batch_id
            for row in rows
        }

        if len(batch_ids) != 1:
            raise BigQueryPersistenceError(
                "Todas las filas staging "
                "deben pertenecer al "
                "mismo batch."
            )

        row_ids = [
            row.row_id
            for row in rows
        ]

        if (
            len(row_ids)
            != len(set(row_ids))
        ):
            raise BigQueryPersistenceError(
                "Existen row_id duplicados "
                "en staging."
            )

        for row in rows:
            if not str(
                row.batch_id
            ).strip():
                raise (
                    BigQueryPersistenceError(
                        "batch_id no puede "
                        "estar vacio."
                    )
                )

            if not str(
                row.row_id
            ).strip():
                raise (
                    BigQueryPersistenceError(
                        "row_id no puede "
                        "estar vacio."
                    )
                )

            if (
                isinstance(
                    row.expected_version,
                    bool,
                )
                or not isinstance(
                    row.expected_version,
                    int,
                )
                or row.expected_version < 1
            ):
                raise (
                    BigQueryPersistenceError(
                        "expected_version "
                        "debe ser un entero "
                        "mayor o igual a 1."
                    )
                )

            record = (
                row.as_record()
            )

            if (
                tuple(record)
                != STAGING_COLUMNS
            ):
                raise (
                    BigQueryPersistenceError(
                        "La fila staging "
                        "no coincide con "
                        "el contrato."
                    )
                )

    @staticmethod
    def _staging_record(
        row: StagingRow,
    ) -> dict:
        record = (
            row.as_record()
        )

        return {
            key: (
                BigQueryPersistenceRepository
                ._json_value(
                    value
                )
            )
            for (
                key,
                value,
            ) in record.items()
        }

    @staticmethod
    def _json_value(
        value,
    ):
        if value is None:
            return None

        if isinstance(
            value,
            Decimal,
        ):
            return format(
                value,
                "f",
            )

        if isinstance(
            value,
            datetime,
        ):
            return (
                value.isoformat()
            )

        return value

    def _table_id(
        self,
        table_name: str,
    ) -> str:
        name = self._required_text(
            table_name,
            "table_name",
        )

        return (
            f"{self._project}."
            f"{self._dataset}."
            f"{name}"
        )

    @staticmethod
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
            raise BigQueryPersistenceError(
                f"{field_name} no puede "
                "estar vacio."
            )

        return text
