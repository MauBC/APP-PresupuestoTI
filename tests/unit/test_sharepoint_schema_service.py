
import pytest

from app.models.sharepoint_schema import (
    SharePointColumnSpec,
)
from app.services.sharepoint_schema_service import (
    SharePointSchemaError,
    SharePointSchemaService,
)


pytestmark = pytest.mark.unit


class FakeClient:
    def __init__(
        self,
        columns,
    ):
        self.columns = list(
            columns
        )

        self.created = []

    def get_columns(
        self,
        list_name,
    ):
        return tuple(
            self.columns
        )

    def create_column(
        self,
        list_name,
        definition,
    ):
        self.created.append(
            (
                list_name,
                definition,
            )
        )

        column = dict(
            definition
        )

        self.columns.append(
            column
        )

        return column


def specs():
    return (
        SharePointColumnSpec(
            name="SummaryKey",
            display_name="Summary Key",
            kind="text",
            indexed=True,
            enforce_unique=True,
            max_length=64,
        ),
        SharePointColumnSpec(
            name="TotalUSD",
            display_name="Total USD",
            kind="number",
            decimal_places="two",
        ),
    )


def test_plan_finds_missing_columns():
    service = (
        SharePointSchemaService(
            FakeClient(
                (
                    {
                        "name":
                            "Title",
                        "text":
                            {},
                    },
                )
            )
        )
    )

    plan = service.plan(
        list_name="Resumen_Capex",
        specs=specs(),
    )

    assert (
        len(
            plan.missing
        )
        == 2
    )

    assert plan.is_compatible
    assert not plan.is_complete


def test_ensure_creates_only_missing():
    client = FakeClient(
        (
            {
                "name":
                    "SummaryKey",
                "text":
                    {},
            },
        )
    )

    service = (
        SharePointSchemaService(
            client
        )
    )

    result = service.ensure(
        list_name="Resumen_Capex",
        specs=specs(),
    )

    assert result.is_complete

    assert (
        len(
            client.created
        )
        == 1
    )

    assert (
        client.created[0][1][
            "name"
        ]
        == "TotalUSD"
    )


def test_incompatible_existing_column_blocks():
    client = FakeClient(
        (
            {
                "name":
                    "TotalUSD",
                "text":
                    {},
            },
        )
    )

    service = (
        SharePointSchemaService(
            client
        )
    )

    with pytest.raises(
        SharePointSchemaError,
        match="incompatibles",
    ):
        service.ensure(
            list_name="Resumen_Capex",
            specs=specs(),
        )

    assert client.created == []


def test_unique_column_must_be_indexed():
    with pytest.raises(
        ValueError,
        match="indexada",
    ):
        SharePointColumnSpec(
            name="Key",
            display_name="Key",
            kind="text",
            enforce_unique=True,
            indexed=False,
        )


def test_number_payload_uses_two_decimals():
    spec = (
        SharePointColumnSpec(
            name="TotalUSD",
            display_name="Total USD",
            kind="number",
            decimal_places="two",
        )
    )

    payload = spec.graph_payload()

    assert (
        payload["number"][
            "decimalPlaces"
        ]
        == "two"
    )
