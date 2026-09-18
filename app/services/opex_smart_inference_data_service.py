from app.config.budget_module_config import (
    BudgetModule,
)
from app.services.opex_smart_inference_service import (
    OpexSmartInferenceError,
    OpexSmartInferenceService,
)


class OpexSmartInferenceDataService:
    def __init__(
        self,
        repository,
    ):
        config = (
            repository
            .module_config
        )

        if (
            config.module
            != BudgetModule.OPEX
        ):
            raise (
                OpexSmartInferenceError(
                    "El origen de inferencia "
                    "debe pertenecer a OPEX."
                )
            )

        self._repository = (
            repository
        )

        self._engine = (
            OpexSmartInferenceService(
                config
            )
        )

        self._snapshot = None

    @property
    def has_snapshot(
        self,
    ) -> bool:
        return (
            self._snapshot
            is not None
        )

    @property
    def snapshot_count(
        self,
    ) -> int:
        if self._snapshot is None:
            return 0

        return len(
            self._snapshot
        )

    def clear_snapshot(
        self,
    ):
        self._snapshot = None

    def load_snapshot(
        self,
        *,
        force: bool = False,
    ):
        if (
            self._snapshot
            is not None
            and
            not force
        ):
            return self._snapshot

        rows = (
            self._repository
            .get_dimension_snapshot(
                enabled_only=True,
            )
        )

        self._snapshot = tuple(
            dict(row)
            for row in rows
        )

        return self._snapshot

    def infer(
        self,
        known_values,
    ):
        snapshot = (
            self.load_snapshot()
        )

        return self._engine.infer(
            known_values,
            snapshot,
        )
