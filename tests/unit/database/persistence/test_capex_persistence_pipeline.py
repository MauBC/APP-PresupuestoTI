from dataclasses import replace
from datetime import (
    datetime,
    timezone,
)
from decimal import Decimal

import pytest

from app.config.budget_modules import (
    CAPEX_MODULE_CONFIG,
    OPEX_MODULE_CONFIG,
)
from app.config.capex_schema import (
    CAPEX_USD_MONTH_COLUMNS,
    CAPEX_USD_TOTAL_COLUMN,
)
from app.services.presupuesto_persistence_service import (
    PresupuestoPersistenceService,
    PresupuestoPersistenceServiceError,
)
from app.services.presupuesto_workspace import (
    PresupuestoWorkspace,
)
from database.persistence.batch_builder import (
    build_persistence_batch,
)
from database.persistence.bigquery_repository import (
    BigQueryPersistenceRepository,
)
from database.persistence.contract import (
    EDITABLE_COLUMNS,
)
from database.persistence.staging_builder import (
    build_staging_rows,
)
from database.persistence.transaction_sql import (
    build_apply_staged_batch_sql,
)


pytestmark = pytest.mark.unit


FIXED_TIME = datetime(
    2026,
    9,
    9,
    15,
    0,
    tzinfo=timezone.utc,
)


def make_capex_row():
    row = {
        "row_id": "capex-row-001",
        "version": 1,
        "habilitado": True,
        "pais": "PER",
        "responsable": "RESPONSABLE TEST",
        "sociedad": "RANSA PERU",
        "nombre_inversion": "PROYECTO TEST",
        "moneda_facturacion": "PEN",
    }

    for column in (
        CAPEX_USD_MONTH_COLUMNS
    ):
        row[column] = Decimal(
            "0.00"
        )

    row["enero_usd"] = Decimal(
        "100.00"
    )

    row[
        CAPEX_USD_TOTAL_COLUMN
    ] = Decimal(
        "100.00"
    )

    return row


def make_capex_batch():
    workspace = PresupuestoWorkspace(
        CAPEX_MODULE_CONFIG
    )

    workspace.load(
        (
            make_capex_row(),
        )
    )

    workspace.edit_month(
        0,
        "enero_usd",
        Decimal("125.00"),
    )

    batch = build_persistence_batch(
        workspace,
        actor="usuario@empresa.com",
        app_version="test",
        timestamp=FIXED_TIME,
        batch_id_factory=lambda: (
            "capex-batch-001"
        ),
    )

    return (
        workspace,
        batch,
    )


class FakeJob:
    def __init__(
        self,
    ):
        self.num_dml_affected_rows = 1
        self.result_called = False

    def result(
        self,
    ):
        self.result_called = True
        return iter(())


class FakeClient:
    def __init__(
        self,
    ):
        self.calls = []

    def query(
        self,
        sql,
        *,
        job_config=None,
        location=None,
    ):
        job = FakeJob()

        self.calls.append(
            {
                "sql": sql,
                "job_config": job_config,
                "location": location,
                "job": job,
            }
        )

        return job


def parameter_map(
    job_config,
):
    return {
        parameter.name:
            parameter.value
        for parameter
        in job_config.query_parameters
    }


def test_capex_builds_usd_persistence_batch():
    workspace, batch = (
        make_capex_batch()
    )

    assert (
        workspace.module_config.module.value
        == "CAPEX"
    )

    assert batch.row_count == 1

    assert batch.field_count == 2

    row = batch.rows[0]

    assert row.row_id == (
        "capex-row-001"
    )

    assert (
        row.expected_version
        == 1
    )

    changed_columns = {
        change.column
        for change
        in row.field_changes
    }

    assert changed_columns == {
        "enero_usd",
        CAPEX_USD_TOTAL_COLUMN,
    }

    persisted_columns = tuple(
        column
        for column, _
        in row.editable_values
    )

    assert (
        persisted_columns
        == EDITABLE_COLUMNS
    )


def test_capex_builds_shared_usd_staging():
    _, batch = (
        make_capex_batch()
    )

    staging = build_staging_rows(
        batch,
        timestamp=FIXED_TIME,
    )

    assert len(staging) == 1

    row = staging[0]

    assert row.batch_id == (
        "capex-batch-001"
    )

    assert row.row_id == (
        "capex-row-001"
    )

    assert (
        row.expected_version
        == 1
    )

    values = dict(
        row.editable_values
    )

    assert (
        values["enero_usd"]
        == Decimal("125.00")
    )

    assert (
        values[
            CAPEX_USD_TOTAL_COLUMN
        ]
        == Decimal("125.00")
    )


def test_capex_repository_targets_capex_table_and_batch_module():
    client = FakeClient()

    repository = (
        BigQueryPersistenceRepository(
            client,
            project="project-test",
            dataset="dataset-test",
            location="US",
            module_config=(
                CAPEX_MODULE_CONFIG
            ),
        )
    )

    assert (
        repository.main_table_id
        ==
        "project-test."
        "dataset-test."
        f"{CAPEX_MODULE_CONFIG.main_table}"
    )

    _, batch = (
        make_capex_batch()
    )

    repository.insert_pending_batch(
        batch
    )

    assert len(
        client.calls
    ) == 1

    call = client.calls[0]

    parameters = parameter_map(
        call["job_config"]
    )

    assert (
        parameters["budget_module"]
        == "CAPEX"
    )

    assert (
        parameters["batch_id"]
        == "capex-batch-001"
    )

    assert (
        call["location"]
        == "US"
    )

    assert (
        call["job"]
        .result_called
    )


def test_transaction_sql_can_target_capex_main_table():
    repository = (
        BigQueryPersistenceRepository(
            FakeClient(),
            project="project-test",
            dataset="dataset-test",
            location="US",
            module_config=(
                CAPEX_MODULE_CONFIG
            ),
        )
    )

    sql = build_apply_staged_batch_sql(
        main_table_id=(
            repository.main_table_id
        ),
        batch_table_id=(
            repository.batch_table_id
        ),
        audit_table_id=(
            repository.audit_table_id
        ),
        staging_table_id=(
            repository.staging_table_id
        ),
    )

    assert (
        "MERGE "
        f"`{repository.main_table_id}`"
        in sql
    )

    assert (
        "BEGIN TRANSACTION;"
        in sql
    )

    assert (
        "COMMIT TRANSACTION;"
        in sql
    )

    for column in (
        EDITABLE_COLUMNS
    ):
        assert (
            f"`{column}`"
            in sql
        )


class GuardRepository:
    def __init__(
        self,
        module_config,
    ):
        self.module_config = (
            module_config
        )

        self.calls = []

    def insert_pending_batch(
        self,
        batch,
    ):
        self.calls.append(
            (
                "insert",
                batch,
            )
        )

        raise AssertionError(
            "No se esperaba escritura."
        )


def make_capex_workspace(
    module_config=CAPEX_MODULE_CONFIG,
):
    workspace = PresupuestoWorkspace(
        module_config
    )

    workspace.load(
        (
            make_capex_row(),
        )
    )

    workspace.edit_month(
        0,
        "enero_usd",
        Decimal("125.00"),
    )

    return workspace


def test_capex_service_blocks_persistence_while_disabled():
    disabled_capabilities = replace(
        CAPEX_MODULE_CONFIG.capabilities,
        persistence=False,
    )

    disabled_capex = replace(
        CAPEX_MODULE_CONFIG,
        capabilities=(
            disabled_capabilities
        ),
    )

    workspace = (
        make_capex_workspace(
            disabled_capex
        )
    )

    repository = GuardRepository(
        disabled_capex
    )

    service = (
        PresupuestoPersistenceService(
            workspace,
            repository,
            app_version="test",
        )
    )

    with pytest.raises(
        PresupuestoPersistenceServiceError,
        match="no permite",
    ):
        service.save_changes(
            actor="usuario@empresa.com",
            timestamp=FIXED_TIME,
            batch_id_factory=lambda: (
                "blocked-capex-batch"
            ),
        )

    assert repository.calls == []


def test_persistence_service_rejects_module_mismatch():
    enabled_capabilities = replace(
        CAPEX_MODULE_CONFIG.capabilities,
        persistence=True,
    )

    enabled_capex = replace(
        CAPEX_MODULE_CONFIG,
        capabilities=(
            enabled_capabilities
        ),
    )

    workspace = (
        make_capex_workspace(
            enabled_capex
        )
    )

    repository = GuardRepository(
        OPEX_MODULE_CONFIG
    )

    service = (
        PresupuestoPersistenceService(
            workspace,
            repository,
            app_version="test",
        )
    )

    with pytest.raises(
        PresupuestoPersistenceServiceError,
        match="no coincide",
    ):
        service.save_changes(
            actor="usuario@empresa.com",
            timestamp=FIXED_TIME,
            batch_id_factory=lambda: (
                "mismatch-batch"
            ),
        )

    assert repository.calls == []


def test_capex_persistence_service_reports_module_label():
    enabled_capabilities = replace(
        CAPEX_MODULE_CONFIG.capabilities,
        persistence=True,
    )

    enabled_capex = replace(
        CAPEX_MODULE_CONFIG,
        capabilities=(
            enabled_capabilities
        ),
    )

    workspace = (
        make_capex_workspace(
            enabled_capex
        )
    )

    service = (
        PresupuestoPersistenceService(
            workspace,
            GuardRepository(
                enabled_capex
            ),
            app_version="test",
        )
    )

    assert (
        service.module_label
        == "CAPEX"
    )
