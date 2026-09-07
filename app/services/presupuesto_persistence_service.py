from datetime import datetime

from app.config.settings import settings
from database.persistence.batch_builder import (
    PersistenceBuildError,
    build_persistence_batch,
    generate_batch_id,
)
from database.persistence.models import (
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

            staging = build_staging_rows(
                batch,
                timestamp=batch.created_at,
            )

        except (
            PersistenceBuildError,
            StagingBuildError,
        ) as exc:
            raise (
                PresupuestoPersistenceServiceError(
                    str(exc)
                )
            ) from exc

        try:
            self._repository.insert_pending_batch(
                batch
            )

        except Exception as exc:
            raise (
                PresupuestoPersistenceServiceError(
                    "No se pudo registrar "
                    "el batch de cambios. "
                    "No se modifico el Workspace."
                )
            ) from exc

        try:
            self._repository.replace_staging_rows(
                staging
            )

        except Exception as exc:
            self._mark_preparation_failed(
                batch.batch_id,
                exc,
            )

            raise (
                PresupuestoPersistenceServiceError(
                    "No se pudo preparar "
                    "el staging del batch. "
                    "El Workspace conserva "
                    "todos sus cambios."
                )
            ) from exc

        try:
            result = (
                self._repository
                .apply_staged_batch(
                    batch.batch_id,
                    batch.actor,
                )
            )

        except Exception as exc:
            raise (
                PresupuestoPersistenceServiceError(
                    "No se pudo confirmar "
                    "el resultado final de "
                    "la persistencia. "
                    "El Workspace conserva "
                    "todos sus cambios."
                )
            ) from exc

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
