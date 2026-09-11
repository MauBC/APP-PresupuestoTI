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
    OPEX_MODULE_CONFIG,
)
from app.config.settings import settings
from app.repositories.presupuesto_repository import (
    PresupuestoRepository,
)
from app.services.bigquery_service import (
    BigQueryService,
)
from app.services.new_budget_row_service import (
    NewBudgetRowService,
)
from app.services.presupuesto_persistence_service import (
    PresupuestoPersistenceService,
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

ACTOR = "integration-m8c-insert"


def table_id(name):
    return (
        f"{settings.GOOGLE_CLOUD_PROJECT}."
        f"{settings.BIGQUERY_DATASET}."
        f"{name}"
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
        ).result()
    )


def count_rows(
    client,
    module_config,
):
    result = run_query(
        client,
        f"""
        SELECT COUNT(*) AS total
        FROM `{
            table_id(
                module_config.main_table
            )
        }`
        """,
    )

    return int(
        result[0]["total"]
    )


def insert_existing_opex(
    client,
    *,
    row_id,
    amount,
    version=1,
):
    now = datetime.now(
        timezone.utc
    )

    columns = (
        OPEX_MODULE_CONFIG
        .amount_columns
    )

    values = {
        column: Decimal("0.00")
        for column in columns
    }

    values["enero_usd"] = (
        Decimal(amount)
    )

    values["anio_usd"] = (
        Decimal(amount)
    )

    column_sql = ", ".join(
        f"`{column}`"
        for column in columns
    )

    parameter_sql = ", ".join(
        f"@{column}"
        for column in columns
    )

    sql = f"""
        INSERT INTO `{
            table_id(
                OPEX_MODULE_CONFIG
                .main_table
            )
        }` (
            row_id,
            habilitado,
            version,
            created_at,
            created_by,
            updated_at,
            updated_by,
            {column_sql}
        )
        VALUES (
            @row_id,
            TRUE,
            @version,
            @now,
            @actor,
            @now,
            @actor,
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
            "version",
            "INT64",
            version,
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

    for column, value in (
        values.items()
    ):
        parameters.append(
            bigquery
            .ScalarQueryParameter(
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


def cleanup(
    client,
    *,
    module_config,
    row_ids,
    batch_ids,
):
    clean_rows = list(
        dict.fromkeys(
            str(value).strip()
            for value in row_ids
            if str(value).strip()
        )
    )

    clean_batches = list(
        dict.fromkeys(
            str(value).strip()
            for value in batch_ids
            if str(value).strip()
        )
    )

    sql = f"""
        DELETE FROM `{
            table_id(
                settings
                .BIGQUERY_STAGING_TABLE
            )
        }`
        WHERE batch_id
            IN UNNEST(@batch_ids);

        DELETE FROM `{
            table_id(
                settings
                .BIGQUERY_AUDIT_TABLE
            )
        }`
        WHERE batch_id
            IN UNNEST(@batch_ids);

        DELETE FROM `{
            table_id(
                settings
                .BIGQUERY_BATCH_TABLE
            )
        }`
        WHERE batch_id
            IN UNNEST(@batch_ids);

        DELETE FROM `{
            table_id(
                module_config.main_table
            )
        }`
        WHERE row_id
            IN UNNEST(@row_ids);
    """

    run_query(
        client,
        sql,
        (
            bigquery.ArrayQueryParameter(
                "batch_ids",
                "STRING",
                clean_batches,
            ),
            bigquery.ArrayQueryParameter(
                "row_ids",
                "STRING",
                clean_rows,
            ),
        ),
    )


def make_stack(
    service,
    config,
    workspace,
):
    read_repository = (
        PresupuestoRepository(
            service,
            module_config=config,
        )
    )

    persistence_repository = (
        BigQueryPersistenceRepository(
            service.client,
            module_config=config,
        )
    )

    persistence_service = (
        PresupuestoPersistenceService(
            workspace,
            persistence_repository,
        )
    )

    loader = (
        PresupuestoWorkspaceLoader(
            read_repository,
            workspace,
        )
    )

    coordinator = (
        PresupuestoSaveCoordinator(
            persistence_service,
            loader,
        )
    )

    return (
        read_repository,
        persistence_repository,
        coordinator,
    )


def read_one(
    client,
    table_name,
    row_id,
    columns,
):
    select_sql = ", ".join(
        f"`{column}`"
        for column in columns
    )

    rows = run_query(
        client,
        f"""
        SELECT
            {select_sql}
        FROM `{table_id(table_name)}`
        WHERE row_id = @row_id
        """,
        (
            bigquery
            .ScalarQueryParameter(
                "row_id",
                "STRING",
                row_id,
            ),
        ),
    )

    assert len(rows) == 1

    return rows[0]


def test_real_opex_mixed_update_insert():
    service = BigQueryService()

    token = uuid4().hex

    existing_id = (
        "m8c-existing-"
        + token
    )

    new_id = (
        "m8c-new-"
        + token
    )

    batch_id = (
        "m8c-batch-"
        + token
    )

    initial = count_rows(
        service.client,
        OPEX_MODULE_CONFIG,
    )

    try:
        insert_existing_opex(
            service.client,
            row_id=existing_id,
            amount="100.00",
        )

        workspace = PresupuestoWorkspace(
            OPEX_MODULE_CONFIG
        )

        (
            read_repository,
            persistence_repository,
            coordinator,
        ) = make_stack(
            service,
            OPEX_MODULE_CONFIG,
            workspace,
        )

        workspace.load(
            read_repository
            .get_rows_by_ids(
                (
                    existing_id,
                )
            )
        )

        workspace.edit_month(
            0,
            "enero_usd",
            Decimal("125.00"),
        )

        draft = (
            NewBudgetRowService(
                OPEX_MODULE_CONFIG,
                row_id_factory=(
                    lambda: new_id
                ),
            )
            .create_draft(
                {
                    "pais": "PER",
                    "presupuestador":
                        "M8C TEST",
                    "nombre_gasto":
                        "M8C INSERT TEST",
                    "moneda_facturacion":
                        "USD",
                },
                actor=ACTOR,
                timestamp=(
                    datetime.now(
                        timezone.utc
                    )
                ),
            )
        )

        session_id = (
            workspace.add_new_row(
                draft.row
            )
        )

        workspace.edit_month(
            session_id,
            "enero_usd",
            Decimal("300.00"),
        )

        outcome = (
            coordinator
            .save_and_reload(
                actor=ACTOR,
                batch_id_factory=(
                    lambda: batch_id
                ),
            )
        )

        assert outcome.is_applied
        assert outcome.was_reloaded
        assert not workspace.has_changes

        existing = read_one(
            service.client,
            OPEX_MODULE_CONFIG
            .main_table,
            existing_id,
            (
                "row_id",
                "version",
                "enero_usd",
                "anio_usd",
            ),
        )

        assert (
            existing["version"]
            == 2
        )

        assert (
            existing["enero_usd"]
            == Decimal("125.00")
        )

        inserted = read_one(
            service.client,
            OPEX_MODULE_CONFIG
            .main_table,
            new_id,
            (
                "row_id",
                "pais",
                "presupuestador",
                "nombre_gasto",
                "moneda_facturacion",
                "version",
                "enero_usd",
                "anio_usd",
                "enero_mf",
                "anio_mf",
                "enero_ml",
                "anio_ml",
                "created_by",
                "updated_by",
            ),
        )

        assert (
            inserted["version"]
            == 1
        )

        assert (
            inserted["pais"]
            == "PER"
        )

        assert (
            inserted[
                "presupuestador"
            ]
            == "M8C TEST"
        )

        assert (
            inserted["nombre_gasto"]
            == "M8C INSERT TEST"
        )

        assert (
            inserted[
                "moneda_facturacion"
            ]
            == "USD"
        )

        assert (
            inserted["enero_usd"]
            == Decimal("300.00")
        )

        assert (
            inserted["anio_usd"]
            == Decimal("300.00")
        )

        assert (
            inserted["enero_mf"]
            == Decimal("0")
        )

        assert (
            inserted["enero_ml"]
            == Decimal("0")
        )

        assert (
            inserted["created_by"]
            == ACTOR
        )

        audit = (
            persistence_repository
            .get_batch_audit(
                batch_id
            )
        )

        insert_audit = tuple(
            item
            for item in audit
            if item["row_id"]
            == new_id
        )

        assert insert_audit

        assert all(
            item["version_before"]
            == 0
            for item
            in insert_audit
        )

        assert all(
            item["version_after"]
            == 1
            for item
            in insert_audit
        )

        assert (
            persistence_repository
            .count_staging_rows(
                batch_id
            )
            == 0
        )

    finally:
        cleanup(
            service.client,
            module_config=(
                OPEX_MODULE_CONFIG
            ),
            row_ids=(
                existing_id,
                new_id,
            ),
            batch_ids=(
                batch_id,
            ),
        )

    assert (
        count_rows(
            service.client,
            OPEX_MODULE_CONFIG,
        )
        == initial
    )


def test_real_insert_collision_aborts_batch():
    service = BigQueryService()

    token = uuid4().hex

    existing_id = (
        "m8c-update-"
        + token
    )

    collision_id = (
        "m8c-collision-"
        + token
    )

    batch_id = (
        "m8c-conflict-"
        + token
    )

    initial = count_rows(
        service.client,
        OPEX_MODULE_CONFIG,
    )

    try:
        insert_existing_opex(
            service.client,
            row_id=existing_id,
            amount="100.00",
            version=1,
        )

        insert_existing_opex(
            service.client,
            row_id=collision_id,
            amount="777.00",
            version=4,
        )

        workspace = PresupuestoWorkspace(
            OPEX_MODULE_CONFIG
        )

        (
            read_repository,
            persistence_repository,
            coordinator,
        ) = make_stack(
            service,
            OPEX_MODULE_CONFIG,
            workspace,
        )

        workspace.load(
            read_repository
            .get_rows_by_ids(
                (
                    existing_id,
                )
            )
        )

        workspace.edit_month(
            0,
            "enero_usd",
            Decimal("125.00"),
        )

        draft = (
            NewBudgetRowService(
                OPEX_MODULE_CONFIG,
                row_id_factory=(
                    lambda:
                        collision_id
                ),
            )
            .create_draft(
                {
                    "pais": "PER",
                    "nombre_gasto":
                        "COLLISION",
                },
                actor=ACTOR,
                timestamp=(
                    datetime.now(
                        timezone.utc
                    )
                ),
            )
        )

        new_session = (
            workspace.add_new_row(
                draft.row
            )
        )

        workspace.edit_month(
            new_session,
            "enero_usd",
            Decimal("300.00"),
        )

        outcome = (
            coordinator
            .save_and_reload(
                actor=ACTOR,
                batch_id_factory=(
                    lambda: batch_id
                ),
            )
        )

        assert (
            outcome.status
            == "CONFLICT"
        )

        assert (
            workspace.has_changes
        )

        assert len(
            outcome
            .persistence_result
            .conflicts
        ) == 1

        conflict = (
            outcome
            .persistence_result
            .conflicts[0]
        )

        assert (
            conflict.row_id
            == collision_id
        )

        assert (
            conflict.expected_version
            == 0
        )

        assert (
            conflict.current_version
            == 4
        )

        stored = read_one(
            service.client,
            OPEX_MODULE_CONFIG
            .main_table,
            existing_id,
            (
                "version",
                "enero_usd",
            ),
        )

        assert (
            stored["version"]
            == 1
        )

        assert (
            stored["enero_usd"]
            == Decimal("100.00")
        )

        assert (
            persistence_repository
            .get_batch_audit(
                batch_id
            )
            == ()
        )

        assert (
            persistence_repository
            .count_staging_rows(
                batch_id
            )
            == 0
        )

    finally:
        cleanup(
            service.client,
            module_config=(
                OPEX_MODULE_CONFIG
            ),
            row_ids=(
                existing_id,
                collision_id,
            ),
            batch_ids=(
                batch_id,
            ),
        )

    assert (
        count_rows(
            service.client,
            OPEX_MODULE_CONFIG,
        )
        == initial
    )


def test_real_capex_insert():
    service = BigQueryService()

    token = uuid4().hex

    row_id = (
        "m8c-capex-"
        + token
    )

    batch_id = (
        "m8c-capex-batch-"
        + token
    )

    initial = count_rows(
        service.client,
        CAPEX_MODULE_CONFIG,
    )

    assert initial == 173

    try:
        workspace = PresupuestoWorkspace(
            CAPEX_MODULE_CONFIG
        )

        workspace.load(
            ()
        )

        (
            _,
            persistence_repository,
            coordinator,
        ) = make_stack(
            service,
            CAPEX_MODULE_CONFIG,
            workspace,
        )

        draft = (
            NewBudgetRowService(
                CAPEX_MODULE_CONFIG,
                row_id_factory=(
                    lambda: row_id
                ),
            )
            .create_draft(
                {
                    "tipo": "CAPEX",
                    "vicepresidencia": "TI",
                    "pais": "PER",
                    "sociedad": "M8C TEST",
                    "anio": 2027,
                    "responsable":
                        "M8C TEST",
                    "tipo_activo":
                        "SOFTWARE",
                    "tipo_capex":
                        "TEST",
                    "nombre_inversion":
                        "M8C CAPEX INSERT",
                    "cantidad": 1,
                    "moneda_facturacion":
                        "PEN",
                },
                actor=ACTOR,
                timestamp=(
                    datetime.now(
                        timezone.utc
                    )
                ),
            )
        )

        session_id = (
            workspace.add_new_row(
                draft.row
            )
        )

        workspace.edit_month(
            session_id,
            "enero_usd",
            Decimal("123.45"),
        )

        outcome = (
            coordinator
            .save_and_reload(
                actor=ACTOR,
                batch_id_factory=(
                    lambda: batch_id
                ),
            )
        )

        assert outcome.is_applied
        assert outcome.was_reloaded
        assert not workspace.has_changes

        stored = read_one(
            service.client,
            CAPEX_MODULE_CONFIG
            .main_table,
            row_id,
            (
                "row_id",
                "pais",
                "sociedad",
                "responsable",
                "anio",
                "cantidad",
                "moneda_facturacion",
                "version",
                "enero_ml",
                "anio_ml",
                "enero_usd",
                "anio_usd",
                "created_by",
                "updated_by",
            ),
        )

        assert (
            stored["version"]
            == 1
        )

        assert (
            stored["anio"]
            == 2027
        )

        assert (
            stored["cantidad"]
            == 1
        )

        assert (
            stored["pais"]
            == "PER"
        )

        assert (
            stored["sociedad"]
            == "M8C TEST"
        )

        assert (
            stored[
                "responsable"
            ]
            == "M8C TEST"
        )

        assert (
            stored[
                "moneda_facturacion"
            ]
            == "PEN"
        )

        assert (
            stored["enero_ml"]
            == Decimal("0")
        )

        assert (
            stored["anio_ml"]
            == Decimal("0")
        )

        assert (
            stored["enero_usd"]
            == Decimal("123.45")
        )

        assert (
            stored["anio_usd"]
            == Decimal("123.45")
        )

        audit = (
            persistence_repository
            .get_batch_audit(
                batch_id
            )
        )

        assert audit

        assert all(
            item["version_before"]
            == 0
            for item
            in audit
        )

        assert all(
            item["version_after"]
            == 1
            for item
            in audit
        )

        by_column = {
            item["column_name"]:
                item
            for item in audit
        }

        assert (
            by_column["anio"]
            ["value_type"]
            == "INTEGER"
        )

        assert (
            by_column["cantidad"]
            ["value_type"]
            == "INTEGER"
        )

        assert (
            by_column["pais"]
            ["value_type"]
            == "STRING"
        )

        assert (
            persistence_repository
            .count_staging_rows(
                batch_id
            )
            == 0
        )

    finally:
        cleanup(
            service.client,
            module_config=(
                CAPEX_MODULE_CONFIG
            ),
            row_ids=(
                row_id,
            ),
            batch_ids=(
                batch_id,
            ),
        )

    assert (
        count_rows(
            service.client,
            CAPEX_MODULE_CONFIG,
        )
        == initial
    )
