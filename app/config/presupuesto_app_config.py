MONTHS = (
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "setiembre",
    "octubre",
    "noviembre",
    "diciembre",
)

HIDDEN_COLUMNS = (
    "vp",
    "vp2",
)

ROW_ID_COLUMN = "row_id"
HABILITADO_COLUMN = "habilitado"
VERSION_COLUMN = "version"

CREATED_AT_COLUMN = "created_at"
CREATED_BY_COLUMN = "created_by"
UPDATED_AT_COLUMN = "updated_at"
UPDATED_BY_COLUMN = "updated_by"

DIMENSION_COLUMNS = (
    "origen",
    "presupuestador",
    "compania",
    "pais",
    "ceco",
    "centro_beneficio",
    "desc_cebe",
    "macroservicio_cg",
    "tipo_servicio_cg",
    "sede_cg",
    "region_cg",
    "gyp",
    "numero_cuenta",
    "nombre_cuenta",
    "nombre_gasto",
    "proveedor",
    "categoria_gasto",
    "atributo_2",
    "segmentacion",
    "moneda_facturacion",
    "periodo",
)

USD_MONTH_COLUMNS = tuple(
    f"{month}_usd"
    for month in MONTHS
)

USD_TOTAL_COLUMN = "anio_usd"

USD_COLUMNS = (
    *USD_MONTH_COLUMNS,
    USD_TOTAL_COLUMN,
)

APP_COLUMNS = (
    *DIMENSION_COLUMNS,
    HABILITADO_COLUMN,
    *USD_COLUMNS,
)

TECHNICAL_LOAD_COLUMNS = (
    ROW_ID_COLUMN,
    VERSION_COLUMN,
)

LOAD_COLUMNS = (
    *DIMENSION_COLUMNS,
    *TECHNICAL_LOAD_COLUMNS,
    HABILITADO_COLUMN,
    *USD_COLUMNS,
)

GROUPABLE_COLUMNS = DIMENSION_COLUMNS

EDITABLE_USD_COLUMNS = USD_COLUMNS