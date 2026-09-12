from datetime import datetime
from typing import Callable, Mapping

from app.config.budget_modules import (
    OPEX_MODULE_CONFIG,
)
from app.models.opex_smart_finalization import (
    OpexSmartInsertionContext,
)
from app.models.opex_smart_periodization import (
    OpexSmartPeriodizedRow,
)
from app.services.new_budget_row_service import (
    NewBudgetRowService,
)
from app.services.opex_new_row_amount_service import (
    OpexNewRowAmountService,
)
from app.services.opex_smart_periodization_service import (
    OpexSmartPeriodizationService,
)


class OpexSmartFinalizationError(
    ValueError
):
    pass


class OpexSmartFinalizationService:
    def __init__(
        self,
        *,
        state_service,
        amount_provider:
            Callable[
                [OpexSmartPeriodizedRow],
                Mapping,
            ],
        row_service=None,
        amount_service=None,
        periodization_service=None,
    ):
        if not callable(
            amount_provider
        ):
            raise OpexSmartFinalizationError(
                "amount_provider debe ser "
                "invocable."
            )

        self._state_service = (
            state_service
        )

        self._amount_provider = (
            amount_provider
        )

        self._row_service = (
            row_service
            or NewBudgetRowService(
                OPEX_MODULE_CONFIG
            )
        )

        self._amount_service = (
            amount_service
            or OpexNewRowAmountService()
        )

        self._periodization_service = (
            periodization_service
            or OpexSmartPeriodizationService()
        )

    @staticmethod
    def _required_text(
        value,
        *,
        label,
    ) -> str:
        text = str(
            value
            if value is not None
            else ""
        ).strip()

        if not text:
            raise OpexSmartFinalizationError(
                f"{label} no puede estar vacio."
            )

        return text

    @classmethod
    def _context_values(
        cls,
        context:
            OpexSmartInsertionContext,
    ):
        if not isinstance(
            context,
            OpexSmartInsertionContext,
        ):
            raise TypeError(
                "context debe ser "
                "OpexSmartInsertionContext."
            )

        origen = cls._required_text(
            context.origen,
            label="origen",
        )

        presupuestador = (
            cls._required_text(
                context.presupuestador,
                label="presupuestador",
            )
        )

        periodo = cls._required_text(
            context.periodo,
            label="periodo",
        )

        if periodo != "2027 PB":
            raise OpexSmartFinalizationError(
                "La insercion inteligente OPEX "
                "debe pertenecer al periodo "
                "2027 PB."
            )

        return (
            origen,
            presupuestador,
            periodo,
        )

    @staticmethod
    def _dimensions(
        periodized:
            OpexSmartPeriodizedRow,
        *,
        origen,
        presupuestador,
        periodo,
    ):
        source = (
            periodized.source_row
        )

        enrichment = (
            source.enrichment
        )

        if enrichment is None:
            raise OpexSmartFinalizationError(
                "La fila OPEX no contiene "
                "enriquecimiento de maestros."
            )

        return {
            "origen":
                origen,
            "periodo":
                periodo,
            "presupuestador":
                presupuestador,
            "pais":
                enrichment.pais,
            "compania":
                enrichment.compania,
            "moneda_facturacion":
                source.moneda_facturacion,
            "ceco":
                source.ceco,
            "centro_beneficio":
                enrichment
                .centro_beneficio,
            "numero_cuenta":
                enrichment.numero_cuenta,
            "nombre_cuenta":
                enrichment.nombre_cuenta,
            "gyp":
                enrichment.gyp,
            "desc_cebe":
                enrichment.desc_cebe,
            "macroservicio_cg":
                enrichment
                .macroservicio_cg,
            "tipo_servicio_cg":
                enrichment
                .tipo_servicio_cg,
            "sede_cg":
                enrichment.sede_cg,
            "region_cg":
                enrichment.region_cg,
            "nombre_gasto":
                source.nombre_gasto,
            "proveedor":
                source.proveedor,
            "categoria_gasto":
                enrichment
                .categoria_gasto,
            "atributo_2":
                enrichment.atributo_2,
            "segmentacion":
                enrichment.segmentacion,
        }

    def build_drafts(
        self,
        workbook_state,
        *,
        context:
            OpexSmartInsertionContext,
        actor: str,
        timestamp:
            datetime | None = None,
    ):
        (
            origen,
            presupuestador,
            periodo,
        ) = self._context_values(
            context
        )

        if not (
            self._state_service
            .workbook_ready(
                workbook_state
            )
        ):
            raise OpexSmartFinalizationError(
                "La plantilla OPEX todavia "
                "no esta completamente resuelta."
            )

        enriched_rows = (
            self._state_service
            .build_workbook_rows(
                workbook_state
            )
        )

        if not enriched_rows:
            raise OpexSmartFinalizationError(
                "La plantilla OPEX no produjo "
                "filas para insertar."
            )

        periodized_rows = (
            self._periodization_service
            .periodize_rows(
                enriched_rows
            )
        )

        drafts = []

        for periodized in (
            periodized_rows
        ):
            dimensions = (
                self._dimensions(
                    periodized,
                    origen=origen,
                    presupuestador=(
                        presupuestador
                    ),
                    periodo=periodo,
                )
            )

            draft = (
                self._row_service
                .create_draft(
                    dimensions,
                    actor=actor,
                    timestamp=timestamp,
                )
            )

            monthly_values = (
                self._amount_provider(
                    periodized
                )
            )

            draft = (
                self._amount_service
                .apply(
                    draft,
                    monthly_values=(
                        monthly_values
                    ),
                )
            )

            drafts.append(
                draft
            )

        return tuple(
            drafts
        )

    def build_rows(
        self,
        workbook_state,
        *,
        context:
            OpexSmartInsertionContext,
        actor: str,
        timestamp:
            datetime | None = None,
    ):
        drafts = self.build_drafts(
            workbook_state,
            context=context,
            actor=actor,
            timestamp=timestamp,
        )

        return tuple(
            dict(
                draft.row
            )
            for draft
            in drafts
        )

    def add_to_workspace(
        self,
        workspace,
        workbook_state,
        *,
        context:
            OpexSmartInsertionContext,
        actor: str,
        timestamp:
            datetime | None = None,
        description:
            str = (
                "Insercion inteligente "
                "OPEX 2027"
            ),
    ):
        rows = self.build_rows(
            workbook_state,
            context=context,
            actor=actor,
            timestamp=timestamp,
        )

        description_value = str(
            description
            if description is not None
            else ""
        ).strip()

        if not description_value:
            raise OpexSmartFinalizationError(
                "description no puede "
                "estar vacio."
            )

        return (
            workspace
            .add_new_rows(
                rows,
                description=(
                    description_value
                ),
            )
        )
