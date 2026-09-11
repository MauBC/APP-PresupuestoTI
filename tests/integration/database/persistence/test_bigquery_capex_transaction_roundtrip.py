from dataclasses import replace
from datetime import (
    datetime,
    timezone,
)
from decimal import Decimal
from uuid import uuid4

import pytest
from google.cloud import bigquery

from app.config.budget_modules import (
    CAPEX_MODULE_CONFIG,
)
from app.config.settings import settings
from app.repositories.presupuesto_repository import (
    PresupuestoRepository,
)
from app.services.bigquery_service import (
    BigQueryService,
)
from app.services.presupuesto_history_service import (
    PresupuestoHistoryService,
)
from app.services.presupuesto_persistence_service import (
    PresupuestoPersistenceService,
)
from app.services.presupuesto_reversal_coordinator import (
    PresupuestoReversalCoordinator,
)
from app.services.presupuesto_save_coordinator import (
    PresupuestoSaveCoordinator,
)
from app.services.presupuesto_workspace import (
    PresupuestoWorkspace,
)
from app.services.presupuesto_workspace_loader import (
    PresupuestoWorkspaceLoader,
)
from database.persistence.bigquery_repository import (
    BigQueryPersistenceRepository,
)


pytestmark = pytest.mark.integration


SAVE_ACTOR = (
    "integration-capex-save"
)

REVERSAL_ACTOR = (
    "integration-capex-reversal"
)


def enabled_capex_config():
    capabilities = replace(
        CAPEX_MODULE_CONFIG.capabilities,
        persistence=True,
    )

    return replace(
        CAPEX_MODULE_CONFIG,
        capabilities=capabilities,
    )


def table_id(
    table_name,
):
    return "{}.{}.{}".format(
        settings.GOOGLE_CLOUD_PROJECT,
        settings.BIGQUERY_DATASET,
        table_name,
    )


def run_query(
    client,
    sql,
    parameters=(),
):
    config = bigquery.QueryJobConfig(
        query_parameters=list(
            parameters
        )
    )

    return list(
        client.query(
            sql,
            job_config=config,
            location=(
                settings
                .BIGQUERY_LOCATION
            ),
        )
        .result()
    )


def count_capex_rows(
    client,
    module_config,
):
    sql = f"""
        SELECT
            COUNT(*) AS total_rows
        FROM `{
            table_id(
                module_config.main_table
            )
        }`
    """

    rows = run_query(
        client,
        sql,
    )

    assert len(rows) == 1

    return int(
        rows[0]["total_rows"]
    )


def insert_synthetic_capex_row(
    client,
    *,
    module_config,
    row_id,
):
    main_table = table_id(
        module_config.main_table
    )

    now = datetime.now(
        timezone.utc
    )

    month_columns = tuple(
        module_config.month_columns
    )

    usd_values = {
        column: Decimal("0.00")
        for column
        in month_columns
    }

    usd_values[
        "enero_usd"
    ] = Decimal(
        "100.00"
    )

    usd_values[
        module_config.annual_column
    ] = Decimal(
        "100.00"
    )

    amount_columns = (
        *month_columns,
        module_config.annual_column,
    )

    column_sql = ",\n            ".join(
        f"`{column}`"
        for column
        in amount_columns
    )

    parameter_sql = ",\n            ".join(
        f"@{column}"
        for column
        in amount_columns
    )

    sql = f"""
        INSERT INTO `{main_table}` (
            row_id,
            habilitado,
            version,
            created_at,
            created_by,
            updated_at,
            updated_by,
            moneda_facturacion,
            responsable,
            codigo_ceco,
            cantidad,
            enero_ml,
            anio_ml,
            {column_sql}
        )

        VALUES (
            @row_id,
            TRUE,
            1,
            @now,
            @actor,
            @now,
            @actor,
            @currency,
            @responsable,
            @codigo_ceco,
            @cantidad,
            @enero_ml,
            @anio_ml,
            {parameter_sql}
        )
    """

    parameters = [
        bigquery.ScalarQueryParameter(
            "row_id",
            "STRING",
            row_id,
        ),
        bigquery.ScalarQueryParameter(
            "now",
            "TIMESTAMP",
            now,
        ),
        bigquery.ScalarQueryParameter(
            "actor",
            "STRING",
            SAVE_ACTOR,
        ),
        bigquery.ScalarQueryParameter(
            "currency",
            "STRING",
            "PEN",
        ),
        bigquery.ScalarQueryParameter(
            "responsable",
            "STRING",
            "RESPONSABLE ORIGINAL",
        ),
        bigquery.ScalarQueryParameter(
            "codigo_ceco",
            "STRING",
            "001234",
        ),
        bigquery.ScalarQueryParameter(
            "cantidad",
            "INT64",
            1,
        ),
        bigquery.ScalarQueryParameter(
            "enero_ml",
            "NUMERIC",
            Decimal("365.00"),
        ),
        bigquery.ScalarQueryParameter(
            "anio_ml",
            "NUMERIC",
            Decimal("365.00"),
        ),
    ]

    for (
        column,
        value,
    ) in usd_values.items():
        parameters.append(
            bigquery.ScalarQueryParameter(
                column,
                "NUMERIC",
                value,
            )
        )

    run_query(
        client,
        sql,
        parameters,
    )


def read_capex_row(
    client,
    *,
    module_config,
    row_id,
):
    main_table = table_id(
        module_config.main_table
    )

    sql = f"""
        SELECT
            row_id,
            version,
            habilitado,
            moneda_facturacion,
            responsable,
            codigo_ceco,
            cantidad,
            enero_ml,
            anio_ml,
            enero_usd,
            anio_usd,
            updated_by
        FROM `{main_table}`
        WHERE row_id = @row_id
    """

    rows = run_query(
        client,
        sql,
        [
            bigquery.ScalarQueryParameter(
                "row_id",
                "STRING",
                row_id,
            )
        ],
    )

    assert len(rows) == 1

    return rows[0]


def cleanup_test_data(
    client,
    *,
    module_config,
    row_id,
    batch_ids,
):
    clean_batch_ids = list(
        dict.fromkeys(
            str(value).strip()
            for value
            in batch_ids
            if str(value).strip()
        )
    )

    parameters = [
        bigquery.ArrayQueryParameter(
            "batch_ids",
            "STRING",
            clean_batch_ids,
        ),
        bigquery.ScalarQueryParameter(
            "row_id",
            "STRING",
            row_id,
        ),
    ]

    staging_table = table_id(
        settings.BIGQUERY_STAGING_TABLE
    )

    audit_table = table_id(
        settings.BIGQUERY_AUDIT_TABLE
    )

    batch_table = table_id(
        settings.BIGQUERY_BATCH_TABLE
    )

    main_table = table_id(
        module_config.main_table
    )

    sql = f"""
        DELETE FROM `{staging_table}`
        WHERE batch_id IN UNNEST(
            @batch_ids
        );

        DELETE FROM `{audit_table}`
        WHERE batch_id IN UNNEST(
            @batch_ids
        );

        DELETE FROM `{batch_table}`
        WHERE batch_id IN UNNEST(
            @batch_ids
        );

        DELETE FROM `{main_table}`
        WHERE row_id = @row_id;
    """

    run_query(
        client,
        sql,
        parameters,
    )


def build_stack(
    client,
    *,
    module_config,
    workspace,
):
    bigquery_service = (
        BigQueryService(
            client
        )
    )

    read_repository = (
        PresupuestoRepository(
            bigquery_service,
            module_config=(
                module_config
            ),
        )
    )

    persistence_repository = (
        BigQueryPersistenceRepository(
            client,
            module_config=(
                module_config
            ),
        )
    )

    persistence_service = (
        PresupuestoPersistenceService(
            workspace,
            persistence_repository,
        )
    )

    workspace_loader = (
        PresupuestoWorkspaceLoader(
            read_repository,
            workspace,
        )
    )

    history_service = (
        PresupuestoHistoryService(
            persistence_repository
        )
    )

    return (
        read_repository,
        persistence_repository,
        persistence_service,
        workspace_loader,
        history_service,
    )


def test_real_capex_save_conflict_history_and_reversal():
    module_config = (
        enabled_capex_config()
    )

    service = BigQueryService()

    client = service.client

    initial_count = (
        count_capex_rows(
            client,
            module_config,
        )
    )

    token = uuid4().hex

    row_id = (
        "integration-capex-row-"
        + token
    )

    source_batch_id = (
        "integration-capex-save-"
        + token
    )

    conflict_batch_id = (
        "integration-capex-conflict-"
        + token
    )

    reversal_batch_id = (
        "integration-capex-reversal-"
        + token
    )

    batch_ids = (
        source_batch_id,
        conflict_batch_id,
        reversal_batch_id,
    )

    try:
        #
        # 1. Fila temporal:
        # USD = 100
        # ML = 365
        # version = 1
        #
        insert_synthetic_capex_row(
            client,
            module_config=module_config,
            row_id=row_id,
        )

        assert (
            count_capex_rows(
                client,
                module_config,
            )
            == initial_count + 1
        )

        original = read_capex_row(
            client,
            module_config=module_config,
            row_id=row_id,
        )

        assert (
            original["version"]
            == 1
        )

        assert (
            original["enero_usd"]
            == Decimal("100.00")
        )

        assert (
            original["anio_usd"]
            == Decimal("100.00")
        )

        assert (
            original["enero_ml"]
            == Decimal("365.00")
        )

        assert (
            original["anio_ml"]
            == Decimal("365.00")
        )

        assert (
            original[
                "moneda_facturacion"
            ]
            == "PEN"
        )

        assert (
            original["responsable"]
            == "RESPONSABLE ORIGINAL"
        )

        assert (
            original["codigo_ceco"]
            == "001234"
        )

        assert (
            original["cantidad"]
            == 1
        )

        #
        # 2. Dos sesiones cargan v1.
        #
        workspace = (
            PresupuestoWorkspace(
                module_config
            )
        )

        stale_workspace = (
            PresupuestoWorkspace(
                module_config
            )
        )

        (
            read_repository,
            persistence_repository,
            persistence_service,
            workspace_loader,
            history_service,
        ) = build_stack(
            client,
            module_config=module_config,
            workspace=workspace,
        )

        current_rows = (
            read_repository
            .get_rows_by_ids(
                (
                    row_id,
                )
            )
        )

        assert len(
            current_rows
        ) == 1

        workspace.load(
            current_rows
        )

        stale_workspace.load(
            current_rows
        )

        #
        # 3. Sesion A:
        # 100 -> 125
        # v1 -> v2
        #
        workspace.edit_value(
            0,
            "responsable",
            "RESPONSABLE M8J-C",
        )

        workspace.edit_value(
            0,
            "codigo_ceco",
            "009999",
        )

        workspace.edit_value(
            0,
            "cantidad",
            2,
        )

        workspace.edit_month(
            0,
            "enero_usd",
            Decimal("125.00"),
        )

        coordinator = (
            PresupuestoSaveCoordinator(
                persistence_service,
                workspace_loader,
            )
        )

        save_outcome = (
            coordinator
            .save_and_reload(
                actor=SAVE_ACTOR,
                batch_id_factory=(
                    lambda:
                        source_batch_id
                ),
            )
        )

        assert (
            save_outcome.is_applied
        )

        assert (
            save_outcome.was_reloaded
        )

        assert not (
            workspace.has_changes
        )

        stored = read_capex_row(
            client,
            module_config=module_config,
            row_id=row_id,
        )

        assert (
            stored["version"]
            == 2
        )

        assert (
            stored["enero_usd"]
            == Decimal("125.00")
        )

        assert (
            stored["anio_usd"]
            == Decimal("125.00")
        )

        assert (
            stored["responsable"]
            == "RESPONSABLE M8J-C"
        )

        assert (
            stored["codigo_ceco"]
            == "009999"
        )

        assert (
            stored["cantidad"]
            == 2
        )

        #
        # ML queda completamente standby.
        #
        assert (
            stored["enero_ml"]
            == Decimal("365.00")
        )

        assert (
            stored["anio_ml"]
            == Decimal("365.00")
        )

        assert (
            stored[
                "moneda_facturacion"
            ]
            == "PEN"
        )

        assert (
            stored["updated_by"]
            == SAVE_ACTOR
        )

        #
        # 4. Sesion B sigue en v1.
        # Intenta 100 -> 150.
        # Debe dar CONFLICT.
        #
        stale_workspace.edit_month(
            0,
            "enero_usd",
            Decimal("150.00"),
        )

        (
            _,
            conflict_repository,
            conflict_service,
            _,
            _,
        ) = build_stack(
            client,
            module_config=module_config,
            workspace=(
                stale_workspace
            ),
        )

        conflict_result = (
            conflict_service
            .save_changes(
                actor=(
                    "integration-capex-stale"
                ),
                batch_id_factory=(
                    lambda:
                        conflict_batch_id
                ),
            )
        )

        assert (
            conflict_result.status
            == "CONFLICT"
        )

        assert (
            conflict_result
            .has_conflicts
        )

        assert len(
            conflict_result.conflicts
        ) == 1

        conflict = (
            conflict_result
            .conflicts[0]
        )

        assert (
            conflict.row_id
            == row_id
        )

        assert (
            conflict.expected_version
            == 1
        )

        assert (
            conflict.current_version
            == 2
        )

        #
        # Los cambios locales stale
        # deben conservarse.
        #
        assert (
            stale_workspace.has_changes
        )

        assert (
            stale_workspace
            .get_row(0)[
                "enero_usd"
            ]
            == Decimal("150.00")
        )

        #
        # BigQuery NO fue sobrescrito.
        #
        after_conflict = (
            read_capex_row(
                client,
                module_config=(
                    module_config
                ),
                row_id=row_id,
            )
        )

        assert (
            after_conflict["version"]
            == 2
        )

        assert (
            after_conflict[
                "enero_usd"
            ]
            == Decimal("125.00")
        )

        assert (
            after_conflict[
                "anio_usd"
            ]
            == Decimal("125.00")
        )

        #
        # CONFLICT no genera audit.
        #
        assert (
            conflict_repository
            .get_batch_audit(
                conflict_batch_id
            )
            == ()
        )

        #
        # 5. Historial CAPEX.
        #
        batches = (
            history_service
            .list_batches(
                status="APPLIED",
                limit=200,
                offset=0,
            )
        )

        source_batch = next(
            batch
            for batch in batches
            if (
                batch.batch_id
                == source_batch_id
            )
        )

        assert (
            source_batch
            .budget_module
            == "CAPEX"
        )

        assert (
            source_batch
            .reverted_batch_id
            is None
        )

        detail = (
            history_service
            .get_batch_detail(
                source_batch
            )
        )

        assert (
            detail.batch
            .budget_module
            == "CAPEX"
        )

        assert {
            change.column_name
            for change
            in detail.changes
        } == {
            "responsable",
            "codigo_ceco",
            "cantidad",
            "enero_usd",
            "anio_usd",
        }

        #
        # 6. Reversion:
        # 125 -> 100
        # v2 -> v3
        #
        reversal_coordinator = (
            PresupuestoReversalCoordinator(
                workspace=workspace,
                history_service=(
                    history_service
                ),
                read_repository=(
                    read_repository
                ),
                persistence_service=(
                    persistence_service
                ),
                workspace_loader=(
                    workspace_loader
                ),
            )
        )

        reversal_outcome = (
            reversal_coordinator
            .revert_and_reload(
                source_batch,
                actor=(
                    REVERSAL_ACTOR
                ),
                batch_id_factory=(
                    lambda:
                        reversal_batch_id
                ),
            )
        )

        assert (
            reversal_outcome
            .is_applied
        )

        assert (
            reversal_outcome
            .was_reloaded
        )

        restored = read_capex_row(
            client,
            module_config=module_config,
            row_id=row_id,
        )

        assert (
            restored["version"]
            == 3
        )

        assert (
            restored["enero_usd"]
            == Decimal("100.00")
        )

        assert (
            restored["anio_usd"]
            == Decimal("100.00")
        )

        assert (
            restored["responsable"]
            == "RESPONSABLE ORIGINAL"
        )

        assert (
            restored["codigo_ceco"]
            == "001234"
        )

        assert (
            restored["cantidad"]
            == 1
        )

        #
        # ML sigue intacta incluso
        # despues de la reversion.
        #
        assert (
            restored["enero_ml"]
            == Decimal("365.00")
        )

        assert (
            restored["anio_ml"]
            == Decimal("365.00")
        )

        assert (
            restored[
                "moneda_facturacion"
            ]
            == "PEN"
        )

        assert (
            restored["updated_by"]
            == REVERSAL_ACTOR
        )

        assert not (
            workspace.has_changes
        )

        #
        # 7. Batch compensatorio.
        #
        final_batches = (
            history_service
            .list_batches(
                status="APPLIED",
                limit=200,
                offset=0,
            )
        )

        reversal_batch = next(
            batch
            for batch
            in final_batches
            if (
                batch.batch_id
                == reversal_batch_id
            )
        )

        assert (
            reversal_batch
            .budget_module
            == "CAPEX"
        )

        assert (
            reversal_batch
            .reverted_batch_id
            == source_batch_id
        )

        reversal_detail = (
            history_service
            .get_batch_detail(
                reversal_batch
            )
        )

        assert {
            change.column_name
            for change
            in reversal_detail.changes
        } == {
            "responsable",
            "codigo_ceco",
            "cantidad",
            "enero_usd",
            "anio_usd",
        }

        for change in (
            reversal_detail.changes
        ):
            assert (
                change.version_before
                == 2
            )

            assert (
                change.version_after
                == 3
            )

        #
        # Staging final limpio.
        #
        assert (
            persistence_repository
            .count_staging_rows(
                source_batch_id
            )
            == 0
        )

        assert (
            persistence_repository
            .count_staging_rows(
                reversal_batch_id
            )
            == 0
        )

    finally:
        cleanup_test_data(
            client,
            module_config=module_config,
            row_id=row_id,
            batch_ids=batch_ids,
        )

    #
    # La tabla debe conservar exactamente
    # el mismo baseline que tenia antes
    # de insertar la fila sintetica.
    #
    assert (
        count_capex_rows(
            client,
            module_config,
        )
        == initial_count
    )
