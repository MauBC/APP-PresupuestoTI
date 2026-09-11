from copy import deepcopy
from datetime import (
    datetime,
    timezone,
)
from decimal import (
    Decimal,
    InvalidOperation,
)

from app.config.budget_modules import (
    get_budget_module_config,
)
from app.config.presupuesto_app_config import (
    HABILITADO_COLUMN,
    ROW_ID_COLUMN,
    VERSION_COLUMN,
)
from app.models.budget_history import (
    BudgetAuditChange,
    BudgetHistoryDetail,
)
from app.models.budget_reversal import (
    BudgetReversalProposal,
)
from database.persistence.batch_builder import (
    generate_batch_id,
)
from database.persistence.contract import (
    EDITABLE_COLUMNS,
    EDITABLE_VALUE_TYPES,
    PENDING_STATUS,
)
from database.persistence.models import (
    PersistenceBatch,
    PersistenceFieldChange,
    PersistenceRowChange,
)


class PresupuestoReversalError(
    ValueError
):
    pass


class PresupuestoReversalConflictError(
    PresupuestoReversalError
):
    pass


def _required_text(
    value,
    field_name: str,
) -> str:
    text = str(
        value
        if value is not None
        else ""
    ).strip()

    if not text:
        raise PresupuestoReversalError(
            f"{field_name} no puede "
            "estar vacio."
        )

    return text


def _normalize_timestamp(
    value: datetime,
) -> datetime:
    if not isinstance(
        value,
        datetime,
    ):
        raise PresupuestoReversalError(
            "created_at debe ser datetime."
        )

    if (
        value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise PresupuestoReversalError(
            "created_at debe incluir "
            "zona horaria."
        )

    return value.astimezone(
        timezone.utc
    )


def _required_version(
    value,
) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(
            value,
            int,
        )
        or value < 1
    ):
        raise PresupuestoReversalError(
            "version debe ser "
            "un entero >= 1."
        )

    return value


def _numeric_value(
    value,
    *,
    field_name: str,
):
    if value is None:
        return None

    if isinstance(
        value,
        bool,
    ):
        raise PresupuestoReversalError(
            f"{field_name} no es NUMERIC."
        )

    try:
        result = (
            value
            if isinstance(
                value,
                Decimal,
            )
            else Decimal(
                str(value).strip()
            )
        )

    except (
        InvalidOperation,
        ValueError,
    ) as exc:
        raise PresupuestoReversalError(
            f"{field_name} no es "
            "un NUMERIC valido."
        ) from exc

    if not result.is_finite():
        raise PresupuestoReversalError(
            f"{field_name} debe ser "
            "un NUMERIC finito."
        )

    return result


def _boolean_value(
    value,
    *,
    field_name: str,
):
    if isinstance(
        value,
        bool,
    ):
        return value

    if value is None:
        raise PresupuestoReversalError(
            f"{field_name} no puede "
            "ser NULL."
        )

    text = str(
        value
    ).strip().lower()

    if text == "true":
        return True

    if text == "false":
        return False

    raise PresupuestoReversalError(
        f"{field_name} no es "
        "un BOOLEAN valido."
    )


def _typed_value(
    value,
    value_type: str,
    *,
    field_name: str,
):
    normalized_type = (
        str(
            value_type
        )
        .strip()
        .upper()
    )

    if normalized_type == "NUMERIC":
        return _numeric_value(
            value,
            field_name=field_name,
        )

    if normalized_type == "BOOLEAN":
        return _boolean_value(
            value,
            field_name=field_name,
        )

    raise PresupuestoReversalError(
        "Tipo de valor de auditoria "
        "no soportado: "
        f"{value_type}"
    )


def _group_changes(
    detail: BudgetHistoryDetail,
) -> dict[
    str,
    tuple[
        BudgetAuditChange,
        ...,
    ],
]:
    grouped = {}

    for change in detail.changes:
        grouped.setdefault(
            change.row_id,
            [],
        ).append(
            change
        )

    return {
        row_id: tuple(changes)
        for row_id, changes
        in grouped.items()
    }


def _index_current_rows(
    current_rows,
) -> dict[
    str,
    dict,
]:
    result = {}

    for source in current_rows:
        row = dict(
            source
        )

        row_id = _required_text(
            row.get(
                ROW_ID_COLUMN
            ),
            ROW_ID_COLUMN,
        )

        if row_id in result:
            raise PresupuestoReversalError(
                "Existen row_id duplicados "
                "entre las filas actuales: "
                f"{row_id}"
            )

        result[
            row_id
        ] = row

    return result


def _validate_detail(
    detail: BudgetHistoryDetail,
):
    if not isinstance(
        detail,
        BudgetHistoryDetail,
    ):
        raise TypeError(
            "detail debe ser "
            "BudgetHistoryDetail."
        )

    if not detail.batch.is_applied:
        raise PresupuestoReversalError(
            "Solo se pueden revertir "
            "batches APPLIED."
        )

    if not detail.changes:
        raise PresupuestoReversalError(
            "El batch no contiene "
            "auditoria para revertir."
        )

    if not (
        detail.field_count_matches
    ):
        raise PresupuestoReversalError(
            "field_count no coincide "
            "con la auditoria."
        )

    if not (
        detail.row_count_matches
    ):
        raise PresupuestoReversalError(
            "row_count no coincide "
            "con la auditoria."
        )


def _validate_row_versions(
    *,
    row_id: str,
    current_version: int,
    changes,
):
    version_pairs = {
        (
            change.version_before,
            change.version_after,
        )
        for change
        in changes
    }

    if len(
        version_pairs
    ) != 1:
        raise PresupuestoReversalError(
            "La fila tiene versiones "
            "inconsistentes en auditoria: "
            f"{row_id}"
        )

    (
        version_before,
        version_after,
    ) = next(
        iter(
            version_pairs
        )
    )

    if (
        version_after
        != version_before + 1
    ):
        raise PresupuestoReversalError(
            "La auditoria contiene una "
            "transicion de version invalida "
            f"para {row_id}: "
            f"{version_before} -> "
            f"{version_after}"
        )

    if (
        current_version
        != version_after
    ):
        raise PresupuestoReversalConflictError(
            "La fila fue modificada "
            "despues del batch original. "
            f"row_id={row_id}, "
            f"version_batch={version_after}, "
            f"version_actual={current_version}."
        )

    return (
        version_before,
        version_after,
    )


def _validate_audit_column(
    change: BudgetAuditChange,
):
    column = change.column_name

    if column not in (
        EDITABLE_VALUE_TYPES
    ):
        raise PresupuestoReversalError(
            "La auditoria contiene una "
            "columna no persistible: "
            f"{column}"
        )

    expected_type = (
        EDITABLE_VALUE_TYPES[
            column
        ]
    )

    actual_type = (
        str(
            change.value_type
        )
        .strip()
        .upper()
    )

    if actual_type != expected_type:
        raise PresupuestoReversalError(
            "value_type no coincide "
            "con el contrato para "
            f"{column}. "
            f"Esperado={expected_type}, "
            f"actual={actual_type}."
        )


def _validate_annual_consistency(
    *,
    target_state: dict,
    changed_columns: set[str],
    budget_module: str,
):
    module_config = (
        get_budget_module_config(
            budget_module
        )
    )

    amount_columns = set(
        module_config
        .amount_columns
    )

    if not (
        changed_columns
        & amount_columns
    ):
        return

    annual_column = (
        module_config
        .annual_column
    )

    annual_value = (
        target_state.get(
            annual_column
        )
    )

    if annual_value is None:
        raise PresupuestoReversalError(
            "La reversion dejaria el "
            "total anual en NULL."
        )

    expected_total = Decimal(
        "0.00"
    )

    for column in (
        module_config
        .month_columns
    ):
        value = (
            target_state.get(
                column
            )
        )

        if value is None:
            continue

        expected_total += (
            _numeric_value(
                value,
                field_name=column,
            )
        )

    expected_total = (
        expected_total.quantize(
            Decimal("0.01")
        )
    )

    annual_numeric = (
        _numeric_value(
            annual_value,
            field_name=annual_column,
        )
    )

    if (
        annual_numeric
        != expected_total
    ):
        raise PresupuestoReversalError(
            "La reversion produciria "
            "un total anual inconsistente. "
            f"{annual_column}="
            f"{annual_numeric}, "
            f"suma_meses="
            f"{expected_total}."
        )


class PresupuestoReversalService:
    @staticmethod
    def build_proposal(
        detail: BudgetHistoryDetail,
        current_rows,
        *,
        actor: str,
        app_version: str | None = None,
        timestamp: datetime | None = None,
        batch_id_factory=(
            generate_batch_id
        ),
        expected_module: str | None = None,
    ) -> BudgetReversalProposal:
        _validate_detail(
            detail
        )

        actor_value = _required_text(
            actor,
            "actor",
        )

        budget_module = (
            detail.batch
            .budget_module
            .strip()
            .upper()
        )

        if expected_module is not None:
            expected_module_value = (
                _required_text(
                    expected_module,
                    "expected_module",
                )
                .upper()
            )

            if (
                budget_module
                != expected_module_value
            ):
                raise (
                    PresupuestoReversalError(
                        "El batch pertenece al "
                        f"modulo {budget_module}, "
                        "pero se intento revertir "
                        "desde "
                        f"{expected_module_value}."
                    )
                )

        current_index = (
            _index_current_rows(
                current_rows
            )
        )

        expected_row_ids = set(
            detail.row_ids
        )

        actual_row_ids = set(
            current_index
        )

        missing = (
            expected_row_ids
            - actual_row_ids
        )

        extra = (
            actual_row_ids
            - expected_row_ids
        )

        if missing:
            raise (
                PresupuestoReversalConflictError(
                    "No se encontraron todas "
                    "las filas actuales del batch. "
                    "Faltan: "
                    + ", ".join(
                        sorted(
                            missing
                        )
                    )
                )
            )

        if extra:
            raise PresupuestoReversalError(
                "Se recibieron filas que no "
                "pertenecen al batch: "
                + ", ".join(
                    sorted(
                        extra
                    )
                )
            )

        grouped = _group_changes(
            detail
        )

        persistence_rows = []

        for row_id in (
            detail.row_ids
        ):
            current = (
                current_index[
                    row_id
                ]
            )

            current_version = (
                _required_version(
                    current.get(
                        VERSION_COLUMN
                    )
                )
            )

            changes = (
                grouped[
                    row_id
                ]
            )

            (
                version_before,
                version_after,
            ) = (
                _validate_row_versions(
                    row_id=row_id,
                    current_version=(
                        current_version
                    ),
                    changes=changes,
                )
            )

            target_state = {}

            for column in (
                EDITABLE_COLUMNS
            ):
                if column not in current:
                    raise (
                        PresupuestoReversalError(
                            "La fila actual no "
                            "contiene la columna "
                            "editable requerida: "
                            f"{column}"
                        )
                    )

                target_state[
                    column
                ] = deepcopy(
                    current[
                        column
                    ]
                )

            inverse_changes = []
            changed_columns = set()

            # Una fila insertada no se elimina.
            # Su reversion es una baja logica.
            if version_before == 0:
                enabled_type = (
                    EDITABLE_VALUE_TYPES[
                        HABILITADO_COLUMN
                    ]
                )

                current_enabled = (
                    _typed_value(
                        current.get(
                            HABILITADO_COLUMN
                        ),
                        enabled_type,
                        field_name=(
                            f"{HABILITADO_COLUMN}"
                            ".actual"
                        ),
                    )
                )

                if current_enabled is not True:
                    raise (
                        PresupuestoReversalError(
                            "La fila insertada no "
                            "puede revertirse por "
                            "baja logica porque ya "
                            "esta deshabilitada. "
                            f"row_id={row_id}"
                        )
                    )

                enabled_audits = tuple(
                    change
                    for change in changes
                    if (
                        change.column_name
                        == HABILITADO_COLUMN
                    )
                )

                if len(
                    enabled_audits
                ) > 1:
                    raise (
                        PresupuestoReversalError(
                            "Existe auditoria "
                            "duplicada para "
                            f"{row_id}."
                            f"{HABILITADO_COLUMN}."
                        )
                    )

                if enabled_audits:
                    enabled_change = (
                        enabled_audits[0]
                    )

                    _validate_audit_column(
                        enabled_change
                    )

                    audited_enabled = (
                        _typed_value(
                            enabled_change
                            .after_value,
                            enabled_type,
                            field_name=(
                                f"{HABILITADO_COLUMN}"
                                ".after"
                            ),
                        )
                    )

                    if (
                        audited_enabled
                        is not True
                    ):
                        raise (
                            PresupuestoReversalError(
                                "La alta original "
                                "no dejo la fila "
                                "habilitada. "
                                f"row_id={row_id}"
                            )
                        )

                target_state[
                    HABILITADO_COLUMN
                ] = False

                changed_columns.add(
                    HABILITADO_COLUMN
                )

                inverse_changes.append(
                    PersistenceFieldChange(
                        column=(
                            HABILITADO_COLUMN
                        ),
                        before=True,
                        after=False,
                        value_type=(
                            enabled_type
                        ),
                    )
                )

            else:
                seen_columns = set()

                for change in changes:
                    _validate_audit_column(
                        change
                    )

                    column = (
                        change
                        .column_name
                    )

                    if column in (
                        seen_columns
                    ):
                        raise (
                            PresupuestoReversalError(
                                "Existe auditoria "
                                "duplicada para "
                                f"{row_id}."
                                f"{column}."
                            )
                        )

                    seen_columns.add(
                        column
                    )

                    changed_columns.add(
                        column
                    )

                    value_type = (
                        EDITABLE_VALUE_TYPES[
                            column
                        ]
                    )

                    audited_after = (
                        _typed_value(
                            change.after_value,
                            value_type,
                            field_name=(
                                f"{column}.after"
                            ),
                        )
                    )

                    current_value = (
                        _typed_value(
                            current.get(
                                column
                            ),
                            value_type,
                            field_name=(
                                f"{column}.actual"
                            ),
                        )
                    )

                    if (
                        current_value
                        != audited_after
                    ):
                        raise (
                            PresupuestoReversalConflictError(
                                "El valor actual ya "
                                "no coincide con el "
                                "resultado del batch. "
                                f"row_id={row_id}, "
                                f"column={column}, "
                                f"batch={audited_after}, "
                                f"actual={current_value}."
                            )
                        )

                    target_value = (
                        _typed_value(
                            change.before_value,
                            value_type,
                            field_name=(
                                f"{column}.before"
                            ),
                        )
                    )

                    if (
                        target_value
                        == current_value
                    ):
                        raise (
                            PresupuestoReversalError(
                                "La auditoria no "
                                "representa un cambio "
                                "real para "
                                f"{row_id}.{column}."
                            )
                        )

                    target_state[
                        column
                    ] = deepcopy(
                        target_value
                    )

                    inverse_changes.append(
                        PersistenceFieldChange(
                            column=column,
                            before=deepcopy(
                                current_value
                            ),
                            after=deepcopy(
                                target_value
                            ),
                            value_type=(
                                value_type
                            ),
                        )
                    )

            _validate_annual_consistency(
                target_state=(
                    target_state
                ),
                changed_columns=(
                    changed_columns
                ),
                budget_module=(
                    budget_module
                ),
            )

            editable_values = tuple(
                (
                    column,
                    deepcopy(
                        target_state[
                            column
                        ]
                    ),
                )
                for column
                in EDITABLE_COLUMNS
            )

            persistence_rows.append(
                PersistenceRowChange(
                    row_id=row_id,
                    expected_version=(
                        version_after
                    ),
                    field_changes=tuple(
                        inverse_changes
                    ),
                    editable_values=(
                        editable_values
                    ),
                )
            )

        batch_id = _required_text(
            batch_id_factory(),
            "batch_id",
        )

        if (
            batch_id
            == detail.batch.batch_id
        ):
            raise PresupuestoReversalError(
                "El nuevo batch_id no puede "
                "ser igual al batch original."
            )

        effective_time = (
            datetime.now(
                timezone.utc
            )
            if timestamp is None
            else timestamp
        )

        created_at = (
            _normalize_timestamp(
                effective_time
            )
        )

        app_version_value = None

        if app_version is not None:
            normalized_version = str(
                app_version
            ).strip()

            if normalized_version:
                app_version_value = (
                    normalized_version
                )

        persistence_batch = (
            PersistenceBatch(
                batch_id=batch_id,
                status=PENDING_STATUS,
                actor=actor_value,
                created_at=created_at,
                app_version=(
                    app_version_value
                ),
                rows=tuple(
                    persistence_rows
                ),
                reverted_batch_id=(
                    detail.batch
                    .batch_id
                ),
            )
        )

        if (
            persistence_batch.row_count
            != detail.batch.row_count
        ):
            raise PresupuestoReversalError(
                "La propuesta de reversion "
                "no conserva row_count."
            )

        if any(
            row.field_count < 1
            for row in persistence_batch.rows
        ):
            raise PresupuestoReversalError(
                "La propuesta de reversion "
                "contiene una fila sin cambios."
            )

        return BudgetReversalProposal(
            source_batch_id=(
                detail.batch
                .batch_id
            ),
            budget_module=(
                budget_module
            ),
            batch=(
                persistence_batch
            ),
        )
