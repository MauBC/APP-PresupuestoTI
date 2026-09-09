from datetime import datetime
from time import perf_counter

from app.config.settings import settings
from database.persistence.batch_builder import (
    PersistenceBuildError,
    build_persistence_batch,
    generate_batch_id,
)
from database.persistence.models import (
    PersistenceBatch,
    PersistenceResult,
)
from database.persistence.staging_builder import (
    StagingBuildError,
    build_staging_rows,
)


class PresupuestoPersistenceServiceError(
    RuntimeError
):
    pass


def _print_timing(
    label: str,
    started: float,
):
    elapsed = (
        perf_counter()
        - started
    )

    print(
        f"[OPEX SAVE] "
        f"{label:<22} "
        f"{elapsed:>7.2f} s",
        flush=True,
    )


class PresupuestoPersistenceService:
    def __init__(
        self,
        workspace,
        repository,
        *,
        app_version: str | None = None,
    ):
        self._workspace = workspace
        self._repository = repository

        self._app_version = (
            settings.APP_VERSION
            if app_version is None
            else app_version
        )

    def save_changes(
        self,
        *,
        actor: str,
        timestamp: datetime | None = None,
        batch_id_factory=generate_batch_id,
    ) -> PersistenceResult:
        preparation_started = (
            perf_counter()
        )

        try:
            batch = build_persistence_batch(
                self._workspace,
                actor=actor,
                app_version=(
                    self._app_version
                ),
                timestamp=timestamp,
                batch_id_factory=(
                    batch_id_factory
                ),
            )

        except PersistenceBuildError as exc:
            _print_timing(
                "Preparacion ERROR",
                preparation_started,
            )

            raise (
                PresupuestoPersistenceServiceError(
                    str(exc)
                )
            ) from exc

        _print_timing(
            "Preparacion",
            preparation_started,
        )

        return self.persist_batch(
            batch
        )

    def persist_batch(
        self,
        batch: PersistenceBatch,
    ) -> PersistenceResult:
        if not isinstance(
            batch,
            PersistenceBatch,
        ):
            raise (
                PresupuestoPersistenceServiceError(
                    "batch debe ser "
                    "PersistenceBatch."
                )
            )

        total_started = (
            perf_counter()
        )

        staging_build_started = (
            perf_counter()
        )

        try:
            staging = build_staging_rows(
                batch,
                timestamp=batch.created_at,
            )

        except StagingBuildError as exc:
            _print_timing(
                "Staging build ERROR",
                staging_build_started,
            )

            raise (
                PresupuestoPersistenceServiceError(
                    str(exc)
                )
            ) from exc

        _print_timing(
            "Staging build",
            staging_build_started,
        )

        pending_started = (
            perf_counter()
        )

        try:
            self._repository.insert_pending_batch(
                batch
            )

        except Exception as exc:
            _print_timing(
                "Insert PENDING ERROR",
                pending_started,
            )

            raise (
                PresupuestoPersistenceServiceError(
                    "No se pudo registrar "
                    "el batch de cambios."
                )
            ) from exc

        _print_timing(
            "Insert PENDING",
            pending_started,
        )

        staging_started = (
            perf_counter()
        )

        try:
            self._repository.stage_rows(
                staging
            )

        except Exception as exc:
            _print_timing(
                "Carga staging ERROR",
                staging_started,
            )

            self._mark_preparation_failed(
                batch.batch_id,
                exc,
            )

            raise (
                PresupuestoPersistenceServiceError(
                    "No se pudo preparar "
                    "el staging del batch."
                )
            ) from exc

        _print_timing(
            "Carga staging",
            staging_started,
        )

        transaction_started = (
            perf_counter()
        )

        try:
            result = (
                self._repository
                .apply_staged_batch(
                    batch.batch_id,
                    batch.actor,
                )
            )

        except Exception as exc:
            _print_timing(
                "Transaccion ERROR",
                transaction_started,
            )

            raise (
                PresupuestoPersistenceServiceError(
                    "No se pudo confirmar "
                    "el resultado final de "
                    "la persistencia."
                )
            ) from exc

        _print_timing(
            "Transaccion",
            transaction_started,
        )

        _print_timing(
            "Persistencia total",
            total_started,
        )

        if (
            result.batch_id
            != batch.batch_id
        ):
            raise (
                PresupuestoPersistenceServiceError(
                    "El resultado de persistencia "
                    "pertenece a un batch distinto."
                )
            )

        return result

    def _mark_preparation_failed(
        self,
        batch_id: str,
        original_error: Exception,
    ) -> None:
        error_message = (
            "Staging preparation failed: "
            + str(original_error)
        )

        try:
            self._repository.mark_batch_failed(
                batch_id,
                error_message,
            )

        except Exception as mark_error:
            raise (
                PresupuestoPersistenceServiceError(
                    "Fallo la preparacion del "
                    "staging y tampoco se pudo "
                    "marcar el batch como FAILED. "
                    "Se requiere revision antes "
                    "de reintentar."
                )
            ) from mark_error


