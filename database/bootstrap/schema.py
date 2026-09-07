from app.config.presupuesto_schema import (
    AMOUNT_COLUMNS,
    LEGACY_EXPECTED_COLUMNS,
    STRING_COLUMNS,
)


IGNORED_SOURCE_COLUMNS = (
    "vp",
    "vp1",
    "vp2",
)


STORAGE_STRING_COLUMNS = tuple(
    column
    for column in STRING_COLUMNS
    if column not in IGNORED_SOURCE_COLUMNS
)


STORAGE_AMOUNT_COLUMNS = (
    AMOUNT_COLUMNS
)


STORAGE_BUSINESS_COLUMNS = tuple(
    column
    for column in LEGACY_EXPECTED_COLUMNS
    if column not in IGNORED_SOURCE_COLUMNS
)