import pytest

from app.config.budget_modules import (
    CAPEX_MODULE_CONFIG,
    OPEX_MODULE_CONFIG,
)
from app.repositories.presupuesto_repository import (
    PresupuestoRepository,
)
from app.services.opex_smart_inference_data_service import (
    OpexSmartInferenceDataService,
)
from app.services.opex_smart_inference_service import (
    OpexSmartInferenceError,
)


pytestmark = pytest.mark.unit


class FakeQueryJob:
    def __init__(
        self,
        rows,
    ):
        self._rows = tuple(
            rows
        )

    def result(
        self,
    ):
        return self._rows


class FakeClient:
    def __init__(
        self,
        rows=(),
    ):
        self.location = "US"
        self.rows = tuple(rows)
        self.calls = []

    def query(
        self,
        sql,
        *,
        location=None,
        **kwargs,
    ):
        self.calls.append(
            {
                "sql":
                    sql,
                "location":
                    location,
                "kwargs":
                    kwargs,
            }
        )

        return FakeQueryJob(
            self.rows
        )


class FakeBigQuery:
    def __init__(
        self,
        rows=(),
    ):
        self.client = FakeClient(
            rows
        )

    def get_table_reference(
        self,
        table_name=None,
    ):
        return (
            "project.dataset."
            + str(table_name)
        )


def test_repository_snapshot_reads_only_dimensions():
    source = {
        column:
            f"value-{column}"
        for column
        in OPEX_MODULE_CONFIG
        .dimension_columns
    }

    source["habilitado"] = True

    # Debe ignorarse aunque BigQuery
    # hipoteticamente la devolviera.
    source["anio_usd"] = 999

    bigquery = FakeBigQuery(
        (
            source,
        )
    )

    repository = (
        PresupuestoRepository(
            bigquery,
            module_config=(
                OPEX_MODULE_CONFIG
            ),
        )
    )

    rows = (
        repository
        .get_dimension_snapshot()
    )

    assert len(rows) == 1

    assert (
        tuple(
            rows[0]
        )
        ==
        (
            *OPEX_MODULE_CONFIG
            .dimension_columns,
            "habilitado",
        )
    )

    assert (
        "anio_usd"
        not in rows[0]
    )

    sql = (
        bigquery
        .client
        .calls[0]["sql"]
    )

    assert (
        "`anio_usd`"
        not in sql
    )

    assert (
        "COALESCE(`habilitado`, TRUE)"
        in sql
    )


def test_repository_can_include_disabled_rows():
    bigquery = FakeBigQuery(
        ()
    )

    repository = (
        PresupuestoRepository(
            bigquery,
            module_config=(
                OPEX_MODULE_CONFIG
            ),
        )
    )

    repository.get_dimension_snapshot(
        enabled_only=False
    )

    sql = (
        bigquery
        .client
        .calls[0]["sql"]
    )

    assert (
        "WHERE"
        not in sql.upper()
    )


class FakeRepository:
    def __init__(
        self,
        *,
        module_config=(
            OPEX_MODULE_CONFIG
        ),
        rows=(),
    ):
        self.module_config = (
            module_config
        )

        self.rows = tuple(
            rows
        )

        self.calls = 0

    def get_dimension_snapshot(
        self,
        *,
        enabled_only=True,
    ):
        assert enabled_only is True

        self.calls += 1

        return tuple(
            dict(row)
            for row in self.rows
        )


def make_row(
    *,
    ceco,
    pais,
    proveedor,
    nombre_gasto="LICENCIAS",
    categoria_gasto="SOFTWARE",
):
    return {
        "ceco":
            ceco,
        "pais":
            pais,
        "proveedor":
            proveedor,
        "nombre_gasto":
            nombre_gasto,
        "categoria_gasto":
            categoria_gasto,
        "periodo":
            "2026",
        "habilitado":
            True,
    }


def test_snapshot_is_cached_between_inferences():
    repository = (
        FakeRepository(
            rows=(
                make_row(
                    ceco="001234",
                    pais="PER",
                    proveedor="MICROSOFT",
                ),
            )
        )
    )

    service = (
        OpexSmartInferenceDataService(
            repository
        )
    )

    first = service.infer(
        {
            "ceco":
                "001234",
        }
    )

    second = service.infer(
        {
            "nombre_gasto":
                "LICENCIAS",
        }
    )

    assert (
        repository.calls
        == 1
    )

    assert (
        service.snapshot_count
        == 1
    )

    assert (
        first.resolved_values[
            "pais"
        ]
        == "PER"
    )

    assert (
        second.resolved_values[
            "categoria_gasto"
        ]
        == "SOFTWARE"
    )


def test_force_reload_refreshes_snapshot():
    repository = (
        FakeRepository(
            rows=(
                make_row(
                    ceco="001234",
                    pais="PER",
                    proveedor="MICROSOFT",
                ),
            )
        )
    )

    service = (
        OpexSmartInferenceDataService(
            repository
        )
    )

    first = (
        service.load_snapshot()
    )

    repository.rows = (
        make_row(
            ceco="009999",
            pais="CHL",
            proveedor="ORACLE",
        ),
    )

    cached = (
        service.load_snapshot()
    )

    refreshed = (
        service.load_snapshot(
            force=True
        )
    )

    assert first == cached

    assert (
        refreshed
        != cached
    )

    assert (
        repository.calls
        == 2
    )


def test_clear_snapshot_causes_new_read():
    repository = (
        FakeRepository(
            rows=(
                make_row(
                    ceco="001234",
                    pais="PER",
                    proveedor="MICROSOFT",
                ),
            )
        )
    )

    service = (
        OpexSmartInferenceDataService(
            repository
        )
    )

    service.load_snapshot()

    assert (
        service.has_snapshot
        is True
    )

    service.clear_snapshot()

    assert (
        service.has_snapshot
        is False
    )

    service.load_snapshot()

    assert (
        repository.calls
        == 2
    )


def test_capex_repository_is_rejected():
    repository = (
        FakeRepository(
            module_config=(
                CAPEX_MODULE_CONFIG
            )
        )
    )

    with pytest.raises(
        OpexSmartInferenceError,
        match="debe pertenecer a OPEX",
    ):
        OpexSmartInferenceDataService(
            repository
        )
