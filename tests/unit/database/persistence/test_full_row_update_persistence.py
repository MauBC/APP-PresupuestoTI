from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.config.budget_modules import (
    CAPEX_MODULE_CONFIG,
    OPEX_MODULE_CONFIG,
)
from app.services.presupuesto_workspace import PresupuestoWorkspace
from database.persistence.audit_builder import build_audit_changes
from database.persistence.batch_builder import build_persistence_batch
from database.persistence.in_memory_repository import InMemoryPersistenceRepository
from database.persistence.staging_builder import build_staging_rows

pytestmark = pytest.mark.unit
FIXED_TIME = datetime(2026, 9, 11, 20, 0, tzinfo=timezone.utc)


def make_persisted_row(config, *, row_id):
    row = {}
    for column, value_type in config.insert_column_types:
        if value_type == "STRING":
            row[column] = "X"
        elif value_type == "INTEGER":
            row[column] = 2027 if column == "anio" else 1
        elif value_type == "NUMERIC":
            row[column] = Decimal("0")
        else:
            raise AssertionError(value_type)
    row["row_id"] = row_id
    row["version"] = 1
    row["habilitado"] = True
    return row


def persist_one_edit(config, *, row_id, column, value):
    source = make_persisted_row(config, row_id=row_id)
    workspace = PresupuestoWorkspace(config)
    workspace.load([source])
    workspace.edit_value(0, column, value)

    batch = build_persistence_batch(
        workspace,
        actor="unit@test.local",
        timestamp=FIXED_TIME,
        batch_id_factory=lambda: f"batch-{row_id}",
    )
    staging = build_staging_rows(batch, timestamp=FIXED_TIME)
    ids = iter(f"audit-{i}" for i in range(batch.field_count))
    audit = build_audit_changes(
        batch,
        timestamp=FIXED_TIME,
        audit_id_factory=lambda: next(ids),
    )

    repo = InMemoryPersistenceRepository([source])
    repo.create_batch(batch)
    repo.stage_rows(staging)
    result = repo.apply_staged_batch(batch.batch_id, audit)
    return batch, staging, result, repo.get_row(row_id)


def test_opex_dimension_update_roundtrip():
    batch, staging, result, row = persist_one_edit(
        OPEX_MODULE_CONFIG,
        row_id="opex-row",
        column="ceco",
        value="001234",
    )
    assert result.is_applied
    assert row["ceco"] == "001234"
    assert row["version"] == 2
    assert dict(batch.rows[0].insert_values)["ceco"] == "001234"
    assert staging[0].insert_payload is not None


def test_capex_string_update_roundtrip():
    batch, staging, result, row = persist_one_edit(
        CAPEX_MODULE_CONFIG,
        row_id="capex-row",
        column="nombre_inversion",
        value="Proyecto editado",
    )
    assert result.is_applied
    assert row["nombre_inversion"] == "Proyecto editado"
    assert row["version"] == 2
    assert (
        dict(batch.rows[0].insert_values)["nombre_inversion"]
        == "Proyecto editado"
    )
    assert staging[0].insert_payload is not None
