
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
        name="Sociedad",
        display_name="Sociedad",
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
        name="VPAprobador",
        display_name="VP Aprobador",
        kind="text",
    ),
    SharePointColumnSpec(
        name="NombreInversion",
        display_name="Nombre de Inversion",
        kind="text",
    ),
    SharePointColumnSpec(
        name="TotalUSD",
        display_name="Total USD",
        kind="number",
        decimal_places="two",
    ),
    SharePointColumnSpec(
        name="RegistrosOrigen",
        display_name="Registros Origen",
        kind="number",
        decimal_places="none",
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
    SharePointColumnSpec(
        name="UpdatedAt",
        display_name="Updated At",
        kind="dateTime",
    ),
    SharePointColumnSpec(
        name="Modulo",
        display_name="Modulo",
        kind="text",
        max_length=20,
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
    "Sociedad":
        "sociedad",
    "Responsable":
        "responsable",
    "GerenteAprobador":
        "gerente_aprobador",
    "VPAprobador":
        "vp_aprobador",
    "NombreInversion":
        "nombre_inversion",
    "TotalUSD":
        "total_usd",
    "RegistrosOrigen":
        "registros_origen",
}
