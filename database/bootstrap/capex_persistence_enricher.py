from collections.abc import Callable
from datetime import datetime

import pandas as pd

from app.config.capex_schema import (
    CAPEX_BUSINESS_COLUMNS,
    CAPEX_EXPECTED_COLUMNS,
)
from database.bootstrap.persistence_enricher import (
    generate_row_id,
    utc_now,
)


class CapexPersistenceEnrichmentError(
    ValueError
):
    pass


def enrich_capex_for_persistence(
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

    expected_business = tuple(
        CAPEX_BUSINESS_COLUMNS
    )

    actual_columns = tuple(
        source.columns
    )

    missing = tuple(
        column
        for column in expected_business
        if column not in source.columns
    )

    if missing:
        raise CapexPersistenceEnrichmentError(
            "Faltan columnas CAPEX de negocio: "
            + ", ".join(
                missing
            )
        )

    extra = tuple(
        column
        for column in actual_columns
        if column not in expected_business
    )

    if extra:
        raise CapexPersistenceEnrichmentError(
            "Existen columnas CAPEX no esperadas: "
            + ", ".join(
                extra
            )
        )

    actor_value = str(
        actor
    ).strip()

    if not actor_value:
        raise CapexPersistenceEnrichmentError(
            "El usuario de bootstrap "
            "CAPEX no puede estar vacio."
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
        raise CapexPersistenceEnrichmentError(
            "El timestamp CAPEX debe "
            "incluir zona horaria."
        )

    enriched = source[
        list(
            expected_business
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
        raise CapexPersistenceEnrichmentError(
            "Se genero un row_id "
            "CAPEX vacio."
        )

    if (
        len(
            set(
                row_ids
            )
        )
        != len(
            row_ids
        )
    ):
        raise CapexPersistenceEnrichmentError(
            "Se generaron row_id "
            "CAPEX duplicados."
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
            CAPEX_EXPECTED_COLUMNS
        )
    ]
