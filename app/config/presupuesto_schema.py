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

AMOUNT_GROUPS = (
    "mf",
    "usd",
    "ml",
)

STRING_COLUMNS = (
    "origen",
    "presupuestador",
    "compania",
    "vp",
    "pais",
    "ceco",
    "centro_beneficio",
    "vp2",
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

AMOUNT_COLUMNS = tuple(
    column
    for group in AMOUNT_GROUPS
    for column in (
        *(f"{month}_{group}" for month in MONTHS),
        f"anio_{group}",
    )
)

EXPECTED_COLUMNS = (
    *STRING_COLUMNS,
    *AMOUNT_COLUMNS,
)

EXPECTED_TYPES = {
    **{
        column: "STRING"
        for column in STRING_COLUMNS
    },
    **{
        column: "NUMERIC"
        for column in AMOUNT_COLUMNS
    },
}