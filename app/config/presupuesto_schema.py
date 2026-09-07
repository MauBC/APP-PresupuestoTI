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

LEGACY_EXPECTED_COLUMNS = (
    *STRING_COLUMNS,
    *AMOUNT_COLUMNS,
)

LEGACY_EXPECTED_TYPES = {
    **{
        column: "STRING"
        for column in STRING_COLUMNS
    },
    **{
        column: "NUMERIC"
        for column in AMOUNT_COLUMNS
    },
}

PERSISTENCE_COLUMNS = (
    "row_id",
    "habilitado",
    "version",
    "created_at",
    "created_by",
    "updated_at",
    "updated_by",
)

PERSISTENCE_TYPES = {
    "row_id": "STRING",
    "habilitado": "BOOLEAN",
    "version": "INTEGER",
    "created_at": "TIMESTAMP",
    "created_by": "STRING",
    "updated_at": "TIMESTAMP",
    "updated_by": "STRING",
}

EXPECTED_COLUMNS = (
    *LEGACY_EXPECTED_COLUMNS,
    *PERSISTENCE_COLUMNS,
)

EXPECTED_TYPES = {
    **LEGACY_EXPECTED_TYPES,
    **PERSISTENCE_TYPES,
}