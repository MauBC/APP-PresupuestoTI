from collections.abc import Callable
from datetime import datetime, timezone
from uuid import uuid4

import pandas as pd

from database.bootstrap.schema import (
    STORAGE_BUSINESS_COLUMNS,
)


TECHNICAL_COLUMNS = (
    "row_id",
    "habilitado",
    "version",
    "created_at",
    "created_by",
    "updated_at",
    "updated_by",
)


FINAL_STORAGE_COLUMNS = (
    *STORAGE_BUSINESS_COLUMNS,
    *TECHNICAL_COLUMNS,
)


class PersistenceEnrichmentError(
    ValueError
):
    pass


def utc_now() -> datetime:
    return datetime.now(
        timezone.utc
    )


def generate_row_id() -> str:
    return str(
        uuid4()
    )


def enrich_for_persistence(
    dataframe: pd.DataFrame,
    *,
    actor: str,
    timestamp: datetime | None = None,
    row_id_factory: Callable[
        [],
        str,
    ] = generate_row_id,
) -> pd.DataFrame:
    source = dataframe.copy(
        deep=True
    )

    missing = tuple(
        column
        for column
        in STORAGE_BUSINESS_COLUMNS
        if column not in source.columns
    )

    if missing:
        raise PersistenceEnrichmentError(
            "Faltan columnas de negocio: "
            + ", ".join(missing)
        )

    actor_value = str(
        actor
    ).strip()

    if not actor_value:
        raise PersistenceEnrichmentError(
            "El usuario de bootstrap "
            "no puede estar vacio."
        )

    effective_timestamp = (
        timestamp
        if timestamp is not None
        else utc_now()
    )

    if (
        effective_timestamp.tzinfo
        is None
    ):
        raise PersistenceEnrichmentError(
            "El timestamp debe incluir "
            "zona horaria."
        )

    enriched = source[
        list(
            STORAGE_BUSINESS_COLUMNS
        )
    ].copy()

    row_ids = [
        row_id_factory()
        for _ in range(
            len(enriched)
        )
    ]

    if any(
        not str(row_id).strip()
        for row_id in row_ids
    ):
        raise PersistenceEnrichmentError(
            "Se genero un row_id vacio."
        )

    if (
        len(set(row_ids))
        != len(row_ids)
    ):
        raise PersistenceEnrichmentError(
            "Se generaron row_id duplicados."
        )

    enriched[
        "row_id"
    ] = row_ids

    enriched[
        "habilitado"
    ] = True

    enriched[
        "version"
    ] = 1

    enriched[
        "created_at"
    ] = effective_timestamp

    enriched[
        "created_by"
    ] = actor_value

    enriched[
        "updated_at"
    ] = effective_timestamp

    enriched[
        "updated_by"
    ] = actor_value

    return enriched[
        list(
            FINAL_STORAGE_COLUMNS
        )
    ]