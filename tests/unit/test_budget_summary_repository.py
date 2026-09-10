
from decimal import Decimal

import pytest

from app.config.budget_modules import (
    CAPEX_MODULE_CONFIG,
)
from app.config.budget_summary_config import (
    CAPEX_POWERAPPS_SUMMARY,
)
from app.repositories.budget_summary_repository import (
    BudgetSummaryRepository,
)


pytestmark = pytest.mark.unit


class FakeJob:
    def __init__(
        self,
        rows,
    ):
        self._rows = rows

    def result(
        self,
    ):
        return self._rows


class FakeClient:
    def __init__(
        self,
        rows,
    ):
        self.rows = rows
        self.calls = []

    def query(
        self,
        sql,
        **kwargs,
    ):
        self.calls.append(
            (
                sql,
                kwargs,
            )
        )

        return FakeJob(
            self.rows
        )


class FakeBigQueryService:
    def __init__(
        self,
        rows,
    ):
        self.client = (
            FakeClient(
                rows
            )
        )

    def get_table_reference(
        self,
        table_name=None,
    ):
        return (
            "project.dataset."
            f"{table_name}"
        )


def sample_row():
    return {
        "vicepresidencia":
            "TI",
        "pais":
            "PER",
        "sociedad":
            "RANSA PERU",
        "responsable":
            "ANA",
        "gerente_aprobador":
            "GERENTE",
        "vp_aprobador":
            "VP",
        "nombre_inversion":
            "PROYECTO A",
        "registros_origen":
            3,
        "total_usd":
            Decimal("65000"),
        "_source_row_count":
            3,
        "_source_total_usd":
            Decimal("65000"),
    }


def test_summary_query_uses_only_required_contract():
    bigquery = (
        FakeBigQueryService(
            [
                sample_row()
            ]
        )
    )

    repository = (
        BudgetSummaryRepository(
            bigquery,
            module_config=(
                CAPEX_MODULE_CONFIG
            ),
        )
    )

    rows = (
        repository
        .get_summary_rows(
            CAPEX_POWERAPPS_SUMMARY
        )
    )

    assert len(rows) == 1

    sql = (
        bigquery
        .client
        .calls[0][0]
    )

    for column in (
        CAPEX_POWERAPPS_SUMMARY
        .group_by
    ):
        assert (
            f"`{column}`"
            in sql
        )

    assert (
        "`anio_usd`"
        in sql
    )

    assert (
        "`codigo_ceco`"
        not in sql
    )

    assert (
        "`codigo_cebe`"
        not in sql
    )

    assert (
        "COALESCE("
        in sql
    )

    assert (
        "`habilitado`"
        in sql
    )

    assert (
        "GROUP BY"
        in sql
    )


def test_summary_query_normalizes_string_dimensions():
    bigquery = (
        FakeBigQueryService(
            [
                sample_row()
            ]
        )
    )

    repository = (
        BudgetSummaryRepository(
            bigquery,
            module_config=(
                CAPEX_MODULE_CONFIG
            ),
        )
    )

    repository.get_summary_rows(
        CAPEX_POWERAPPS_SUMMARY
    )

    sql = (
        bigquery
        .client
        .calls[0][0]
    )

    assert (
        "TRIM("
        in sql
    )

    assert (
        "NULLIF("
        in sql
    )
