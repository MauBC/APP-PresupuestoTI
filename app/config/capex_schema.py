from app.config.presupuesto_app_config import (
    MONTHS,
)
from app.config.presupuesto_schema import (
    PERSISTENCE_COLUMNS,
    PERSISTENCE_TYPES,
)


CAPEX_EXCEL_SHEET = "PB 2027"
CAPEX_EXPECTED_YEAR = 2027


CAPEX_STRING_COLUMNS = (
    "tipo",
    "vicepresidencia",
    "pais",
    "sociedad",
    "responsable",
    "gerente_aprobador",
    "vp_aprobador",
    "tipo_activo",
    "tipo_capex",
    "clasificacion_inversion",
    "filtro_ti",
    "nombre_inversion",
    "descripcion_inversion",
    "codigo_cebe",
    "gyp",
    "codigo_ceco",
    "desc_cebe",
    "sede_cg",
    "u_productiva_cg",
    "seg_rs",
    "moneda_facturacion",
    "observacion_comentario",
)


CAPEX_INTEGER_COLUMNS = (
    "anio",
    "cantidad",
)


CAPEX_ML_MONTH_COLUMNS = tuple(
    f"{month}_ml"
    for month in MONTHS
)

CAPEX_ML_TOTAL_COLUMN = (
    "anio_ml"
)

CAPEX_USD_MONTH_COLUMNS = tuple(
    f"{month}_usd"
    for month in MONTHS
)

CAPEX_USD_TOTAL_COLUMN = (
    "anio_usd"
)


CAPEX_AMOUNT_COLUMNS = (
    *CAPEX_ML_MONTH_COLUMNS,
    CAPEX_ML_TOTAL_COLUMN,
    *CAPEX_USD_MONTH_COLUMNS,
    CAPEX_USD_TOTAL_COLUMN,
)


CAPEX_BUSINESS_COLUMNS = (
    "tipo",
    "vicepresidencia",
    "pais",
    "sociedad",
    "anio",
    "responsable",
    "gerente_aprobador",
    "vp_aprobador",
    "tipo_activo",
    "tipo_capex",
    "clasificacion_inversion",
    "filtro_ti",
    "nombre_inversion",
    "cantidad",
    "descripcion_inversion",
    "codigo_cebe",
    "gyp",
    "codigo_ceco",
    "desc_cebe",
    "sede_cg",
    "u_productiva_cg",
    "seg_rs",
    "moneda_facturacion",
    *CAPEX_ML_MONTH_COLUMNS,
    CAPEX_ML_TOTAL_COLUMN,
    *CAPEX_USD_MONTH_COLUMNS,
    CAPEX_USD_TOTAL_COLUMN,
    "observacion_comentario",
)


CAPEX_DIMENSION_COLUMNS = tuple(
    column
    for column in CAPEX_BUSINESS_COLUMNS
    if column not in CAPEX_AMOUNT_COLUMNS
)


CAPEX_GROUPABLE_COLUMNS = (
    "vicepresidencia",
    "pais",
    "sociedad",
    "responsable",
    "gerente_aprobador",
    "nombre_inversion",
    "tipo_activo",
    "tipo_capex",
    "clasificacion_inversion",
    "filtro_ti",
    "codigo_cebe",
    "gyp",
    "codigo_ceco",
    "desc_cebe",
    "sede_cg",
    "u_productiva_cg",
    "seg_rs",
    "moneda_facturacion",
)


CAPEX_RAW_TO_INTERNAL = {
    "Tipo":
        "tipo",
    "Vicepresidencia":
        "vicepresidencia",
    "Pa\u00eds":
        "pais",
    "Sociedad":
        "sociedad",
    "A\u00f1o":
        "anio",
    "Responsable":
        "responsable",
    "Gerente Aprobador":
        "gerente_aprobador",
    "VP Aprobador":
        "vp_aprobador",
    "Tipo de Activo":
        "tipo_activo",
    "Tipo de CAPEX":
        "tipo_capex",
    "Clasificaci\u00f3n Inversi\u00f3n":
        "clasificacion_inversion",
    "Filtro TI":
        "filtro_ti",
    "Nombre de Inversi\u00f3n":
        "nombre_inversion",
    "Cantidad":
        "cantidad",
    "Breve Descripci\u00f3n de la Inversi\u00f3n":
        "descripcion_inversion",
    "Codigo CEBE":
        "codigo_cebe",
    "GYP":
        "gyp",
    "Codigo CECO":
        "codigo_ceco",
    "Desc_CeBe":
        "desc_cebe",
    "Sede CG":
        "sede_cg",
    "U.Productiva CG":
        "u_productiva_cg",
    "Seg Rs":
        "seg_rs",
    "Moneda de facturaci\u00f3n":
        "moneda_facturacion",

    "01 ML":
        "enero_ml",
    "02 ML":
        "febrero_ml",
    "03 ML":
        "marzo_ml",
    "04 ML":
        "abril_ml",
    "05 ML":
        "mayo_ml",
    "06 ML":
        "junio_ml",
    "07 ML":
        "julio_ml",
    "08 ML":
        "agosto_ml",
    "09 ML":
        "setiembre_ml",
    "10 ML":
        "octubre_ml",
    "11 ML":
        "noviembre_ml",
    "12 ML":
        "diciembre_ml",
    "TOTAL ML":
        "anio_ml",

    "01 USD":
        "enero_usd",
    "02 USD":
        "febrero_usd",
    "3 USD":
        "marzo_usd",
    "4 USD":
        "abril_usd",
    "5 USD":
        "mayo_usd",
    "6 USD":
        "junio_usd",
    "7 USD":
        "julio_usd",
    "8 USD":
        "agosto_usd",
    "9 USD":
        "setiembre_usd",
    "10 USD":
        "octubre_usd",
    "11 USD":
        "noviembre_usd",
    "12 USD":
        "diciembre_usd",
    "TOTAL USD":
        "anio_usd",

    "Observaci\u00f3n/Comentario":
        "observacion_comentario",
}


CAPEX_HEADER_ALIASES = {
    "03 USD": "3 USD",
    "04 USD": "4 USD",
    "05 USD": "5 USD",
    "06 USD": "6 USD",
    "07 USD": "7 USD",
    "08 USD": "8 USD",
    "09 USD": "9 USD",
}


CAPEX_INTERNAL_TO_RAW = {
    internal: raw
    for raw, internal
    in CAPEX_RAW_TO_INTERNAL.items()
}


CAPEX_BUSINESS_TYPES = {
    **{
        column: "STRING"
        for column in CAPEX_STRING_COLUMNS
    },
    **{
        column: "INTEGER"
        for column in CAPEX_INTEGER_COLUMNS
    },
    **{
        column: "NUMERIC"
        for column in CAPEX_AMOUNT_COLUMNS
    },
}


CAPEX_EXPECTED_COLUMNS = (
    *CAPEX_BUSINESS_COLUMNS,
    *PERSISTENCE_COLUMNS,
)


CAPEX_EXPECTED_TYPES = {
    **CAPEX_BUSINESS_TYPES,
    **PERSISTENCE_TYPES,
}


CAPEX_FREE_TEXT_COLUMNS = (
    "nombre_inversion",
    "descripcion_inversion",
    "observacion_comentario",
)


CAPEX_CODE_COLUMNS = (
    "codigo_cebe",
    "codigo_ceco",
)


CAPEX_NULLABLE_TEXT_COLUMNS = (
    "clasificacion_inversion",
    "codigo_cebe",
    "gyp",
    "codigo_ceco",
    "desc_cebe",
    "sede_cg",
    "u_productiva_cg",
    "seg_rs",
    "observacion_comentario",
)
