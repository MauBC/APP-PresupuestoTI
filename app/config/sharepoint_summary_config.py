
from app.models.sharepoint_schema import (
    SharePointColumnSpec,
)


CAPEX_SHAREPOINT_COLUMN_SPECS = (
    SharePointColumnSpec(
        name="SummaryKey",
        display_name="Summary Key",
        kind="text",
        indexed=True,
        enforce_unique=True,
        max_length=64,
    ),
    SharePointColumnSpec(
        name="Vicepresidencia",
        display_name="Vicepresidencia",
        kind="text",
    ),
    SharePointColumnSpec(
        name="Pais",
        display_name="Pais",
        kind="text",
    ),
    SharePointColumnSpec(
        name="Responsable",
        display_name="Responsable",
        kind="text",
    ),
    SharePointColumnSpec(
        name="GerenteAprobador",
        display_name="Gerente Aprobador",
        kind="text",
    ),
    SharePointColumnSpec(
        name="TotalUSD",
        display_name="Total USD",
        kind="number",
        decimal_places="two",
    ),
    SharePointColumnSpec(
        name="SourceBatchId",
        display_name="Source Batch Id",
        kind="text",
        max_length=100,
    ),
    SharePointColumnSpec(
        name="SyncRunId",
        display_name="Sync Run Id",
        kind="text",
        max_length=100,
    ),
)


CAPEX_SHAREPOINT_FIELDS = (
    "Title",
    *tuple(
        spec.name
        for spec
        in CAPEX_SHAREPOINT_COLUMN_SPECS
    ),
)


CAPEX_SHAREPOINT_BUSINESS_FIELDS = {
    "SummaryKey":
        "summary_key",
    "Vicepresidencia":
        "vicepresidencia",
    "Pais":
        "pais",
    "Responsable":
        "responsable",
    "GerenteAprobador":
        "gerente_aprobador",
    "TotalUSD":
        "total_usd",
}


CAPEX_SHAREPOINT_COMPARE_FIELDS = (
    "Title",
    "SummaryKey",
    "Vicepresidencia",
    "Pais",
    "Responsable",
    "GerenteAprobador",
    "TotalUSD",
)


CAPEX_SHAREPOINT_METADATA_FIELDS = (
    "SourceBatchId",
    "SyncRunId",
)
