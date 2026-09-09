from datetime import (
    datetime,
    timezone,
)
from decimal import Decimal
from uuid import uuid4

import pytest

from google.cloud import bigquery

from app.config.presupuesto_app_config import (
    HABILITADO_COLUMN,
    USD_COLUMNS,
)
from app.config.settings import settings
from app.models.budget_history import (
    BudgetHistoryBatch,
)
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
from app.services.presupuesto_reversal_service import (
    PresupuestoReversalService,
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
from database.persistence.contract import (
    EDITABLE_VALUE_TYPES,
    PENDING_STATUS,
)
from database.persistence.models import (
    PersistenceBatch,
    PersistenceFieldChange,
    PersistenceRowChange,
)
from database.persistence.staging_builder import (
    build_staging_rows,
)


pytestmark = pytest.mark.integration


ACTOR = "integration-transaction-test"
REVERSAL_ACTOR = (
    "integration-reversal-test"
)


def table_id(
    table_name,
):
    return "{}.{}.{}".format(
        settings.GOOGLE_CLOUD_PROJECT,
        settings.BIGQUERY_DATASET,
        table_name,
    )


def parameter_config(
    parameters,
):
    return bigquery.QueryJobConfig(
        query_parameters=parameters
    )


def run_query(
    client,
    sql,
    parameters=(),
):
    return list(
        client.query(
            sql,
            job_config=parameter_config(
                list(parameters)
            ),
            location=(
                settings
                .BIGQUERY_LOCATION
            ),
        )
        .result()
    )


def editable_state(
    amount,
):
    values = []

    for column in (
        (
            HABILITADO_COLUMN,
            *USD_COLUMNS,
        )
    ):
        if (
            column
            == HABILITADO_COLUMN
        ):
            value = True

        elif column == "enero_usd":
            value = Decimal(
                amount
            )

        elif column == "anio_usd":
            value = Decimal(
                amount
            )

        else:
            value = Decimal(
                "0.00"
            )

        values.append(
            (
                column,
                value,
            )
        )

    return tuple(
        values
    )


def insert_synthetic_main_row(
    client,
    *,
    row_id,
):
    main_table = table_id(
        settings.BIGQUERY_TABLE
    )

    now = datetime.now(
        timezone.utc
    )

    amount_values = {
        column: Decimal(
            "0.00"
        )
        for column in USD_COLUMNS
    }

    amount_values[
        "enero_usd"
    ] = Decimal(
        "100.00"
    )

    amount_values[
        "anio_usd"
    ] = Decimal(
        "100.00"
    )

    usd_columns_sql = ",\n            ".join(
        USD_COLUMNS
    )

    usd_parameters_sql = ",\n            ".join(
        "@{}".format(
            column
        )
        for column in USD_COLUMNS
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
            {usd_columns_sql}
        )

        VALUES (
            @row_id,
            TRUE,
            1,
            @now,
            @actor,
            @now,
            @actor,
            {usd_parameters_sql}
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
            ACTOR,
        ),
    ]

    for (
        column,
        value,
    ) in amount_values.items():
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


def build_batch(
    *,
    batch_id,
    row_id,
    expected_version,
    before_amount,
    after_amount,
):
    before_value = Decimal(
        before_amount
    )

    after_value = Decimal(
        after_amount
    )

    field_changes = (
        PersistenceFieldChange(
            column="enero_usd",
            before=before_value,
            after=after_value,
            value_type=(
                EDITABLE_VALUE_TYPES[
                    "enero_usd"
                ]
            ),
        ),
        PersistenceFieldChange(
            column="anio_usd",
            before=before_value,
            after=after_value,
            value_type=(
                EDITABLE_VALUE_TYPES[
                    "anio_usd"
                ]
            ),
        ),
    )

    row = PersistenceRowChange(
        row_id=row_id,
        expected_version=(
            expected_version
        ),
        field_changes=(
            field_changes
        ),
        editable_values=(
            editable_state(
                after_amount
            )
        ),
    )

    return PersistenceBatch(
        batch_id=batch_id,
        status=PENDING_STATUS,
        actor=ACTOR,
        created_at=datetime.now(
            timezone.utc
        ),
        app_version=(
            settings.APP_VERSION
        ),
        rows=(
            row,
        ),
    )


def read_main_row(
    client,
    *,
    row_id,
):
    main_table = table_id(
        settings.BIGQUERY_TABLE
    )

    sql = f"""
        SELECT
            row_id,
            habilitado,
            version,
            enero_usd,
            febrero_usd,
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


def read_batch_status(
    client,
    *,
    batch_id,
):
    batch_table = table_id(
        settings.BIGQUERY_BATCH_TABLE
    )

    sql = f"""
        SELECT
            status,
            row_count,
            field_count,
            completed_at,
            error_message,
            budget_module,
            reverted_batch_id
        FROM `{batch_table}`
        WHERE batch_id = @batch_id
    """

    rows = run_query(
        client,
        sql,
        [
            bigquery.ScalarQueryParameter(
                "batch_id",
                "STRING",
                batch_id,
            )
        ],
    )

    assert len(rows) == 1

    return rows[0]


def read_audit(
    client,
    *,
    batch_id,
):
    audit_table = table_id(
        settings.BIGQUERY_AUDIT_TABLE
    )

    sql = f"""
        SELECT
            row_id,
            column_name,
            value_type,
            before_value,
            after_value,
            version_before,
            version_after,
            actor
        FROM `{audit_table}`
        WHERE batch_id = @batch_id
        ORDER BY column_name
    """

    return run_query(
        client,
        sql,
        [
            bigquery.ScalarQueryParameter(
                "batch_id",
                "STRING",
                batch_id,
            )
        ],
    )


def cleanup(
    client,
    *,
    row_id,
    batch_ids,
):
    clean_batch_ids = tuple(
        dict.fromkeys(
            str(batch_id).strip()
            for batch_id
            in batch_ids
            if str(batch_id).strip()
        )
    )

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
        settings.BIGQUERY_TABLE
    )

    parameters = [
        bigquery.ArrayQueryParameter(
            "batch_ids",
            "STRING",
            list(clean_batch_ids),
        ),
        bigquery.ScalarQueryParameter(
            "row_id",
            "STRING",
            row_id,
        ),
    ]

    sql = f"""
        DELETE FROM `{staging_table}`
        WHERE
            batch_id IN UNNEST(
                @batch_ids
            );

        DELETE FROM `{audit_table}`
        WHERE
            batch_id IN UNNEST(
                @batch_ids
            );

        DELETE FROM `{batch_table}`
        WHERE
            batch_id IN UNNEST(
                @batch_ids
            );

        DELETE FROM `{main_table}`
        WHERE
            row_id = @row_id;
    """

    run_query(
        client,
        sql,
        parameters,
    )


def apply_real_batch(
    repository,
    batch,
):
    staging = build_staging_rows(
        batch
    )

    repository.insert_pending_batch(
        batch
    )

    loaded = repository.stage_rows(
        staging
    )

    assert loaded == batch.row_count

    return (
        repository
        .apply_staged_batch(
            batch.batch_id,
            batch.actor,
        )
    )


def make_history_batch(
    *,
    batch,
    stored_status,
):
    return BudgetHistoryBatch(
        batch_id=batch.batch_id,
        status=(
            stored_status[
                "status"
            ]
        ),
        actor=batch.actor,
        created_at=batch.created_at,
        completed_at=(
            stored_status[
                "completed_at"
            ]
        ),
        row_count=(
            stored_status[
                "row_count"
            ]
        ),
        field_count=(
            stored_status[
                "field_count"
            ]
        ),
        app_version=(
            batch.app_version
        ),
        error_message=(
            stored_status[
                "error_message"
            ]
        ),
        budget_module=(
            stored_status[
                "budget_module"
            ]
        ),
        reverted_batch_id=(
            stored_status[
                "reverted_batch_id"
            ]
        ),
    )


def build_reversal_stack(
    service,
    *,
    workspace,
):
    read_repository = (
        PresupuestoRepository(
            service
        )
    )

    persistence_repository = (
        BigQueryPersistenceRepository(
            service.client
        )
    )

    history_service = (
        PresupuestoHistoryService(
            persistence_repository
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

    coordinator = (
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
            app_version=(
                settings.APP_VERSION
            ),
        )
    )

    return (
        read_repository,
        persistence_repository,
        history_service,
        persistence_service,
        workspace_loader,
        coordinator,
    )


def test_real_transaction_applied_then_conflict():
    service = BigQueryService()

    repository = (
        BigQueryPersistenceRepository(
            service.client
        )
    )

    token = uuid4().hex

    row_id = (
        "integration-txn-row-"
        + token
    )

    applied_batch_id = (
        "integration-txn-applied-"
        + token
    )

    conflict_batch_id = (
        "integration-txn-conflict-"
        + token
    )

    batch_ids = (
        applied_batch_id,
        conflict_batch_id,
    )

    try:
        #
        # Synthetic row only.
        #
        insert_synthetic_main_row(
            service.client,
            row_id=row_id,
        )

        original = read_main_row(
            service.client,
            row_id=row_id,
        )

        assert original[
            "version"
        ] == 1

        assert original[
            "habilitado"
        ] is True

        assert original[
            "enero_usd"
        ] == Decimal(
            "100.00"
        )

        assert original[
            "anio_usd"
        ] == Decimal(
            "100.00"
        )

        #
        # APPLIED batch.
        #
        applied_batch = build_batch(
            batch_id=(
                applied_batch_id
            ),
            row_id=row_id,
            expected_version=1,
            before_amount="100.00",
            after_amount="125.00",
        )

        applied_staging = (
            build_staging_rows(
                applied_batch
            )
        )

        repository.insert_pending_batch(
            applied_batch
        )

        assert (
            repository
            .replace_staging_rows(
                applied_staging
            )
            == 1
        )

        applied_result = (
            repository
            .apply_staged_batch(
                applied_batch_id,
                ACTOR,
            )
        )

        assert (
            applied_result.status
            == "APPLIED"
        )

        assert (
            applied_result.is_applied
        )

        assert (
            applied_result.row_count
            == 1
        )

        assert (
            applied_result.field_count
            == 2
        )

        stored = read_main_row(
            service.client,
            row_id=row_id,
        )

        assert (
            stored["version"]
            == 2
        )

        assert (
            stored["enero_usd"]
            == Decimal(
                "125.00"
            )
        )

        assert (
            stored["anio_usd"]
            == Decimal(
                "125.00"
            )
        )

        assert (
            stored["febrero_usd"]
            == Decimal(
                "0.00"
            )
        )

        assert (
            stored["updated_by"]
            == ACTOR
        )

        applied_status = (
            read_batch_status(
                service.client,
                batch_id=(
                    applied_batch_id
                ),
            )
        )

        assert (
            applied_status["status"]
            == "APPLIED"
        )

        assert (
            applied_status[
                "completed_at"
            ]
            is not None
        )

        assert (
            applied_status[
                "error_message"
            ]
            is None
        )

        assert (
            repository
            .count_staging_rows(
                applied_batch_id
            )
            == 0
        )

        audit = read_audit(
            service.client,
            batch_id=(
                applied_batch_id
            ),
        )

        assert len(audit) == 2

        assert {
            row[
                "column_name"
            ]
            for row in audit
        } == {
            "enero_usd",
            "anio_usd",
        }

        for audit_row in audit:
            assert (
                audit_row[
                    "value_type"
                ]
                == "NUMERIC"
            )

            assert (
                Decimal(
                    audit_row[
                        "before_value"
                    ]
                )
                == Decimal(
                    "100.00"
                )
            )

            assert (
                Decimal(
                    audit_row[
                        "after_value"
                    ]
                )
                == Decimal(
                    "125.00"
                )
            )

            assert (
                audit_row[
                    "version_before"
                ]
                == 1
            )

            assert (
                audit_row[
                    "version_after"
                ]
                == 2
            )

            assert (
                audit_row["actor"]
                == ACTOR
            )

        #
        # CONFLICT batch.
        #
        # This intentionally represents
        # a stale client still expecting
        # version 1.
        #
        conflict_batch = (
            build_batch(
                batch_id=(
                    conflict_batch_id
                ),
                row_id=row_id,
                expected_version=1,
                before_amount="100.00",
                after_amount="150.00",
            )
        )

        conflict_staging = (
            build_staging_rows(
                conflict_batch
            )
        )

        repository.insert_pending_batch(
            conflict_batch
        )

        assert (
            repository
            .replace_staging_rows(
                conflict_staging
            )
            == 1
        )

        conflict_result = (
            repository
            .apply_staged_batch(
                conflict_batch_id,
                ACTOR,
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
        # Main row must remain unchanged.
        #
        after_conflict = (
            read_main_row(
                service.client,
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
            == Decimal(
                "125.00"
            )
        )

        assert (
            after_conflict[
                "anio_usd"
            ]
            == Decimal(
                "125.00"
            )
        )

        conflict_status = (
            read_batch_status(
                service.client,
                batch_id=(
                    conflict_batch_id
                ),
            )
        )

        assert (
            conflict_status["status"]
            == "CONFLICT"
        )

        assert (
            conflict_status[
                "completed_at"
            ]
            is not None
        )

        assert (
            repository
            .count_staging_rows(
                conflict_batch_id
            )
            == 0
        )

        #
        # Conflict must not generate audit.
        #
        conflict_audit = (
            read_audit(
                service.client,
                batch_id=(
                    conflict_batch_id
                ),
            )
        )

        assert (
            conflict_audit
            == []
        )

    finally:
        cleanup(
            service.client,
            row_id=row_id,
            batch_ids=batch_ids,
        )


def test_real_transaction_rolls_back_on_audit_mismatch():
    service = BigQueryService()

    repository = (
        BigQueryPersistenceRepository(
            service.client
        )
    )

    token = uuid4().hex

    row_id = (
        "integration-rollback-row-"
        + token
    )

    batch_id = (
        "integration-rollback-batch-"
        + token
    )

    try:
        #
        # Main row starts at 100 USD,
        # version 1.
        #
        insert_synthetic_main_row(
            service.client,
            row_id=row_id,
        )

        original = read_main_row(
            service.client,
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

        #
        # Intentionally malformed batch:
        #
        # field_count will be 1 because
        # field_changes contains only enero_usd.
        #
        # But final editable state changes BOTH
        # enero_usd and anio_usd from 100 to 125.
        #
        # Therefore transactional audit creates
        # 2 rows while batch.field_count = 1.
        #
        # The ASSERT after audit must fail and
        # rollback the whole transaction before
        # MERGE reaches the main table.
        #
        field_changes = (
            PersistenceFieldChange(
                column="enero_usd",
                before=Decimal(
                    "100.00"
                ),
                after=Decimal(
                    "125.00"
                ),
                value_type=(
                    EDITABLE_VALUE_TYPES[
                        "enero_usd"
                    ]
                ),
            ),
        )

        persistence_row = (
            PersistenceRowChange(
                row_id=row_id,
                expected_version=1,
                field_changes=(
                    field_changes
                ),
                editable_values=(
                    editable_state(
                        "125.00"
                    )
                ),
            )
        )

        batch = PersistenceBatch(
            batch_id=batch_id,
            status=PENDING_STATUS,
            actor=ACTOR,
            created_at=(
                datetime.now(
                    timezone.utc
                )
            ),
            app_version=(
                settings.APP_VERSION
            ),
            rows=(
                persistence_row,
            ),
        )

        assert batch.row_count == 1
        assert batch.field_count == 1

        staging = (
            build_staging_rows(
                batch
            )
        )

        repository.insert_pending_batch(
            batch
        )

        assert (
            repository
            .replace_staging_rows(
                staging
            )
            == 1
        )

        #
        # Transaction must return FAILED.
        #
        result = (
            repository
            .apply_staged_batch(
                batch_id,
                ACTOR,
            )
        )

        assert (
            result.status
            == "FAILED"
        )

        assert not result.is_applied

        assert (
            result.error_message
            is not None
        )

        assert (
            "Audit row count"
            in result.error_message
        )

        #
        # Main table must be untouched.
        #
        after_failure = (
            read_main_row(
                service.client,
                row_id=row_id,
            )
        )

        assert (
            after_failure["version"]
            == 1
        )

        assert (
            after_failure[
                "enero_usd"
            ]
            == Decimal(
                "100.00"
            )
        )

        assert (
            after_failure[
                "anio_usd"
            ]
            == Decimal(
                "100.00"
            )
        )

        #
        # Audit INSERT happened before
        # the ASSERT, but rollback must
        # remove those partial rows.
        #
        audit = read_audit(
            service.client,
            batch_id=batch_id,
        )

        assert audit == []

        #
        # Batch is marked FAILED outside
        # the rolled-back transaction.
        #
        stored_batch = (
            read_batch_status(
                service.client,
                batch_id=batch_id,
            )
        )

        assert (
            stored_batch["status"]
            == "FAILED"
        )

        assert (
            stored_batch[
                "completed_at"
            ]
            is not None
        )

        assert (
            stored_batch[
                "error_message"
            ]
            is not None
        )

        assert (
            "Audit row count"
            in stored_batch[
                "error_message"
            ]
        )

        #
        # Staging is intentionally retained
        # after FAILED so the failed operation
        # can be diagnosed safely.
        #
        assert (
            repository
            .count_staging_rows(
                batch_id
            )
            == 1
        )

    finally:
        cleanup(
            service.client,
            row_id=row_id,
            batch_ids=(
                batch_id,
            ),
        )

def test_real_reversal_applied_end_to_end():
    service = BigQueryService()

    token = uuid4().hex

    row_id = (
        "integration-reversal-row-"
        + token
    )

    source_batch_id = (
        "integration-reversal-source-"
        + token
    )

    reversal_batch_id = (
        "integration-reversal-applied-"
        + token
    )

    batch_ids = (
        source_batch_id,
        reversal_batch_id,
    )

    try:
        #
        # 1. Synthetic row:
        # 100 USD / version 1.
        #
        insert_synthetic_main_row(
            service.client,
            row_id=row_id,
        )

        workspace = (
            PresupuestoWorkspace()
        )

        (
            read_repository,
            persistence_repository,
            _,
            _,
            _,
            coordinator,
        ) = build_reversal_stack(
            service,
            workspace=workspace,
        )

        #
        # 2. Original batch:
        # 100 -> 125
        # v1 -> v2
        #
        source_batch = build_batch(
            batch_id=(
                source_batch_id
            ),
            row_id=row_id,
            expected_version=1,
            before_amount="100.00",
            after_amount="125.00",
        )

        source_result = (
            apply_real_batch(
                persistence_repository,
                source_batch,
            )
        )

        assert source_result.is_applied

        after_source = read_main_row(
            service.client,
            row_id=row_id,
        )

        assert (
            after_source[
                "version"
            ]
            == 2
        )

        assert (
            after_source[
                "enero_usd"
            ]
            == Decimal(
                "125.00"
            )
        )

        assert (
            after_source[
                "anio_usd"
            ]
            == Decimal(
                "125.00"
            )
        )

        source_status = (
            read_batch_status(
                service.client,
                batch_id=(
                    source_batch_id
                ),
            )
        )

        assert (
            source_status[
                "status"
            ]
            == "APPLIED"
        )

        assert (
            source_status[
                "budget_module"
            ]
            == "OPEX"
        )

        assert (
            source_status[
                "reverted_batch_id"
            ]
            is None
        )

        source_history = (
            make_history_batch(
                batch=source_batch,
                stored_status=(
                    source_status
                ),
            )
        )

        #
        # 3. Workspace loads the
        # post-source state: v2 / 125.
        #
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

        assert not workspace.has_changes

        #
        # 4. Full reversal:
        # 125 -> 100
        # v2 -> v3
        #
        outcome = (
            coordinator
            .revert_and_reload(
                source_history,
                actor=(
                    REVERSAL_ACTOR
                ),
                batch_id_factory=lambda: (
                    reversal_batch_id
                ),
            )
        )

        assert outcome.is_applied
        assert outcome.was_reloaded

        assert (
            outcome.proposal
            .source_batch_id
            == source_batch_id
        )

        assert (
            outcome.proposal
            .batch
            .reverted_batch_id
            == source_batch_id
        )

        #
        # 5. Main row restored,
        # but version moves forward.
        #
        restored = read_main_row(
            service.client,
            row_id=row_id,
        )

        assert (
            restored[
                "version"
            ]
            == 3
        )

        assert (
            restored[
                "enero_usd"
            ]
            == Decimal(
                "100.00"
            )
        )

        assert (
            restored[
                "anio_usd"
            ]
            == Decimal(
                "100.00"
            )
        )

        assert (
            restored[
                "updated_by"
            ]
            == REVERSAL_ACTOR
        )

        #
        # 6. Reversal batch metadata.
        #
        reversal_status = (
            read_batch_status(
                service.client,
                batch_id=(
                    reversal_batch_id
                ),
            )
        )

        assert (
            reversal_status[
                "status"
            ]
            == "APPLIED"
        )

        assert (
            reversal_status[
                "row_count"
            ]
            == 1
        )

        assert (
            reversal_status[
                "field_count"
            ]
            == 2
        )

        assert (
            reversal_status[
                "budget_module"
            ]
            == "OPEX"
        )

        assert (
            reversal_status[
                "reverted_batch_id"
            ]
            == source_batch_id
        )

        #
        # 7. New immutable audit:
        # 125 -> 100, v2 -> v3.
        #
        reversal_audit = read_audit(
            service.client,
            batch_id=(
                reversal_batch_id
            ),
        )

        assert len(
            reversal_audit
        ) == 2

        assert {
            item[
                "column_name"
            ]
            for item
            in reversal_audit
        } == {
            "enero_usd",
            "anio_usd",
        }

        for item in (
            reversal_audit
        ):
            assert (
                Decimal(
                    item[
                        "before_value"
                    ]
                )
                == Decimal(
                    "125.00"
                )
            )

            assert (
                Decimal(
                    item[
                        "after_value"
                    ]
                )
                == Decimal(
                    "100.00"
                )
            )

            assert (
                item[
                    "version_before"
                ]
                == 2
            )

            assert (
                item[
                    "version_after"
                ]
                == 3
            )

            assert (
                item["actor"]
                == REVERSAL_ACTOR
            )

        #
        # Original audit remains.
        #
        source_audit = read_audit(
            service.client,
            batch_id=(
                source_batch_id
            ),
        )

        assert len(
            source_audit
        ) == 2

        for item in source_audit:
            assert (
                Decimal(
                    item[
                        "before_value"
                    ]
                )
                == Decimal(
                    "100.00"
                )
            )

            assert (
                Decimal(
                    item[
                        "after_value"
                    ]
                )
                == Decimal(
                    "125.00"
                )
            )

            assert (
                item[
                    "version_before"
                ]
                == 1
            )

            assert (
                item[
                    "version_after"
                ]
                == 2
            )

        #
        # 8. Staging is cleaned.
        #
        assert (
            persistence_repository
            .count_staging_rows(
                reversal_batch_id
            )
            == 0
        )

        #
        # 9. Workspace was refreshed,
        # not left at v2.
        #
        workspace_rows = tuple(
            workspace.iter_rows()
        )

        assert len(
            workspace_rows
        ) == 1

        workspace_row = (
            workspace_rows[0]
        )

        assert (
            workspace_row[
                "version"
            ]
            == 3
        )

        assert (
            workspace_row[
                "enero_usd"
            ]
            == Decimal(
                "100.00"
            )
        )

        assert (
            workspace_row[
                "anio_usd"
            ]
            == Decimal(
                "100.00"
            )
        )

        assert not workspace.has_changes

    finally:
        cleanup(
            service.client,
            row_id=row_id,
            batch_ids=batch_ids,
        )


def test_real_reversal_transaction_blocks_race():
    service = BigQueryService()

    token = uuid4().hex

    row_id = (
        "integration-reversal-race-row-"
        + token
    )

    source_batch_id = (
        "integration-reversal-race-source-"
        + token
    )

    intervening_batch_id = (
        "integration-reversal-race-newer-"
        + token
    )

    reversal_batch_id = (
        "integration-reversal-race-revert-"
        + token
    )

    batch_ids = (
        source_batch_id,
        intervening_batch_id,
        reversal_batch_id,
    )

    try:
        #
        # Initial: 100 / v1.
        #
        insert_synthetic_main_row(
            service.client,
            row_id=row_id,
        )

        workspace = (
            PresupuestoWorkspace()
        )

        (
            read_repository,
            persistence_repository,
            history_service,
            persistence_service,
            _,
            _,
        ) = build_reversal_stack(
            service,
            workspace=workspace,
        )

        #
        # Source:
        # 100 -> 125
        # v1 -> v2.
        #
        source_batch = build_batch(
            batch_id=(
                source_batch_id
            ),
            row_id=row_id,
            expected_version=1,
            before_amount="100.00",
            after_amount="125.00",
        )

        source_result = (
            apply_real_batch(
                persistence_repository,
                source_batch,
            )
        )

        assert source_result.is_applied

        source_status = (
            read_batch_status(
                service.client,
                batch_id=(
                    source_batch_id
                ),
            )
        )

        source_history = (
            make_history_batch(
                batch=source_batch,
                stored_status=(
                    source_status
                ),
            )
        )

        #
        # Build a valid reversal
        # while current version is 2.
        #
        detail = (
            history_service
            .get_batch_detail(
                source_history
            )
        )

        current_rows = (
            read_repository
            .get_rows_by_ids(
                detail.row_ids
            )
        )

        workspace.load(
            current_rows
        )

        proposal = (
            PresupuestoReversalService
            .build_proposal(
                detail,
                current_rows,
                actor=(
                    REVERSAL_ACTOR
                ),
                app_version=(
                    settings.APP_VERSION
                ),
                batch_id_factory=lambda: (
                    reversal_batch_id
                ),
                expected_module=(
                    "OPEX"
                ),
            )
        )

        assert (
            proposal.batch.rows[
                0
            ].expected_version
            == 2
        )

        #
        # Simulate another user saving
        # AFTER proposal creation.
        #
        intervening_batch = (
            build_batch(
                batch_id=(
                    intervening_batch_id
                ),
                row_id=row_id,
                expected_version=2,
                before_amount="125.00",
                after_amount="150.00",
            )
        )

        intervening_result = (
            apply_real_batch(
                persistence_repository,
                intervening_batch,
            )
        )

        assert (
            intervening_result.is_applied
        )

        after_intervening = (
            read_main_row(
                service.client,
                row_id=row_id,
            )
        )

        assert (
            after_intervening[
                "version"
            ]
            == 3
        )

        assert (
            after_intervening[
                "enero_usd"
            ]
            == Decimal(
                "150.00"
            )
        )

        #
        # The prepared reversal still
        # expects v2. Transaction must
        # reject it at BigQuery level.
        #
        reversal_result = (
            persistence_service
            .persist_batch(
                proposal.batch
            )
        )

        assert (
            reversal_result.status
            == "CONFLICT"
        )

        assert (
            reversal_result.has_conflicts
        )

        assert len(
            reversal_result.conflicts
        ) == 1

        conflict = (
            reversal_result
            .conflicts[0]
        )

        assert (
            conflict.row_id
            == row_id
        )

        assert (
            conflict.expected_version
            == 2
        )

        assert (
            conflict.current_version
            == 3
        )

        #
        # v3 / 150 remains untouched.
        #
        final_row = read_main_row(
            service.client,
            row_id=row_id,
        )

        assert (
            final_row[
                "version"
            ]
            == 3
        )

        assert (
            final_row[
                "enero_usd"
            ]
            == Decimal(
                "150.00"
            )
        )

        assert (
            final_row[
                "anio_usd"
            ]
            == Decimal(
                "150.00"
            )
        )

        #
        # Reversal attempt is traceable
        # but did not produce audit.
        #
        reversal_status = (
            read_batch_status(
                service.client,
                batch_id=(
                    reversal_batch_id
                ),
            )
        )

        assert (
            reversal_status[
                "status"
            ]
            == "CONFLICT"
        )

        assert (
            reversal_status[
                "budget_module"
            ]
            == "OPEX"
        )

        assert (
            reversal_status[
                "reverted_batch_id"
            ]
            == source_batch_id
        )

        assert (
            read_audit(
                service.client,
                batch_id=(
                    reversal_batch_id
                ),
            )
            == []
        )

        assert (
            persistence_repository
            .count_staging_rows(
                reversal_batch_id
            )
            == 0
        )

        #
        # Both successful operations
        # preserve their own audits.
        #
        assert len(
            read_audit(
                service.client,
                batch_id=(
                    source_batch_id
                ),
            )
        ) == 2

        assert len(
            read_audit(
                service.client,
                batch_id=(
                    intervening_batch_id
                ),
            )
        ) == 2

    finally:
        cleanup(
            service.client,
            row_id=row_id,
            batch_ids=batch_ids,
        )
