from collections import Counter
from decimal import Decimal
from pathlib import Path

from app.models.opex_smart_finalization import (
    OpexSmartInsertionContext,
)
from app.models.opex_smart_import import (
    OpexSmartImportCebeDecision,
    OpexSmartImportDecision,
    OpexSmartImportPreparation,
)
from app.services.opex_fx_loader import (
    OpexFxLoader,
)
from app.services.opex_fx_service import (
    OpexFxService,
)
from app.services.opex_master_data_loader import (
    OpexMasterDataLoader,
)
from app.services.opex_master_enrichment_service import (
    OpexMasterEnrichmentService,
)
from app.services.opex_smart_default_resolution_service import (
    OpexSmartDefaultResolutionService,
)
from app.services.opex_smart_enrichment_service import (
    OpexSmartEnrichmentService,
)
from app.services.opex_smart_finalization_service import (
    OpexSmartFinalizationService,
)
from app.services.opex_smart_resolution_plan_service import (
    OpexSmartResolutionPlanService,
)
from app.services.opex_smart_resolution_service import (
    OpexSmartResolutionService,
)
from app.services.opex_smart_resolution_state_service import (
    OpexSmartResolutionStateService,
)
from app.services.opex_smart_template_loader import (
    OpexSmartTemplateLoader,
)


class OpexSmartImportPreparationError(
    ValueError
):
    pass


class OpexSmartImportPreparationService:
    def __init__(
        self,
        masters_directory=None,
    ):
        if masters_directory is None:
            masters_directory = (
                Path(__file__)
                .resolve()
                .parents[2]
                / "maestros"
            )

        self._masters_directory = (
            Path(
                masters_directory
            )
            .expanduser()
            .resolve()
        )

    @staticmethod
    def validate_request(
        *,
        source_path,
        origin,
        budgeter,
        actor,
    ):
        source_text = str(
            source_path
            if source_path is not None
            else ""
        ).strip()

        if not source_text:
            raise (
                OpexSmartImportPreparationError(
                    "Selecciona primero un archivo."
                )
            )

        source = (
            Path(
                source_text
            )
            .expanduser()
            .resolve()
        )

        if not source.exists():
            raise (
                OpexSmartImportPreparationError(
                    "El archivo seleccionado "
                    "no existe."
                )
            )

        if source.suffix.lower() not in {
            ".xlsx",
            ".xlsm",
        }:
            raise (
                OpexSmartImportPreparationError(
                    "La plantilla debe ser "
                    "XLSX o XLSM."
                )
            )

        normalized_origin = str(
            origin
            if origin is not None
            else ""
        ).strip()

        if not normalized_origin:
            raise (
                OpexSmartImportPreparationError(
                    "Origen es obligatorio."
                )
            )

        normalized_budgeter = str(
            budgeter
            if budgeter is not None
            else ""
        ).strip()

        if not normalized_budgeter:
            raise (
                OpexSmartImportPreparationError(
                    "Presupuestador es "
                    "obligatorio."
                )
            )

        normalized_actor = str(
            actor
            if actor is not None
            else ""
        ).strip()

        if not normalized_actor:
            raise (
                OpexSmartImportPreparationError(
                    "No se pudo identificar "
                    "al usuario actual."
                )
            )

        return (
            source,
            normalized_origin,
            normalized_budgeter,
            normalized_actor,
        )

    @staticmethod
    def _build_state_service(
        snapshot,
    ):
        master = (
            OpexMasterEnrichmentService(
                snapshot
            )
        )

        analysis = (
            OpexSmartEnrichmentService(
                master
            )
        )

        resolution = (
            OpexSmartResolutionService(
                master
            )
        )

        plan_service = (
            OpexSmartResolutionPlanService(
                analysis_service=analysis,
                resolution_service=resolution,
            )
        )

        return (
            OpexSmartResolutionStateService(
                plan_service=plan_service,
                resolution_service=resolution,
            )
        )

    @staticmethod
    def _decimal(
        value,
    ) -> Decimal:
        if value is None:
            return Decimal("0.00")

        if isinstance(
            value,
            Decimal,
        ):
            return value

        return Decimal(
            str(value)
        )

    @classmethod
    def _build_result(
        cls,
        *,
        source,
        workbook,
        workbook_state,
        rows,
    ) -> OpexSmartImportPreparation:
        normalized_rows = tuple(
            rows
        )

        total_usd = sum(
            (
                cls._decimal(
                    row.get(
                        "anio_usd"
                    )
                )
                for row
                in normalized_rows
            ),
            Decimal("0.00"),
        )

        countries = Counter(
            str(
                row.get(
                    "pais"
                )
                or ""
            ).strip()
            for row
            in normalized_rows
        )

        currencies = Counter(
            str(
                row.get(
                    "moneda_facturacion"
                )
                or ""
            ).strip()
            for row
            in normalized_rows
        )

        decisions = []

        auto_cebe_count = 0

        for (
            sheet_name,
            state,
        ) in (
            workbook_state
            .budgets
            .items()
        ):
            account = (
                state.account_selection
            )

            distribution = (
                state.resolved_distribution
            )

            cebe_decisions = []

            for (
                centro_beneficio,
                record,
            ) in (
                state
                .cebe_selections
                .items()
            ):
                cebe_decisions.append(
                    OpexSmartImportCebeDecision(
                        centro_beneficio=(
                            str(
                                centro_beneficio
                            )
                        ),
                        tipo_servicio_cg=(
                            str(
                                record
                                .tipo_servicio_cg
                            )
                        ),
                    )
                )

            auto_cebe_count += len(
                cebe_decisions
            )

            decisions.append(
                OpexSmartImportDecision(
                    sheet_name=(
                        str(
                            sheet_name
                        )
                    ),
                    account_name=(
                        str(
                            account
                            .nombre_cuenta
                        )
                    ),
                    atributo_2=(
                        str(
                            account
                            .atributo_2
                        )
                    ),
                    distribution_mode=(
                        str(
                            distribution.mode
                        )
                    ),
                    cebe_decisions=tuple(
                        cebe_decisions
                    ),
                )
            )

        return (
            OpexSmartImportPreparation(
                rows=normalized_rows,
                source_name=(
                    Path(
                        source
                    ).name
                ),
                budget_count=len(
                    workbook.budgets
                ),
                auto_cebe_count=(
                    auto_cebe_count
                ),
                total_usd=total_usd,
                country_counts=tuple(
                    sorted(
                        (
                            key,
                            value,
                        )
                        for (
                            key,
                            value,
                        )
                        in countries.items()
                        if key
                    )
                ),
                invoice_currency_counts=tuple(
                    sorted(
                        (
                            key,
                            value,
                        )
                        for (
                            key,
                            value,
                        )
                        in currencies.items()
                        if key
                    )
                ),
                decisions=tuple(
                    decisions
                ),
            )
        )

    def prepare(
        self,
        *,
        source_path,
        origin,
        budgeter,
        actor,
    ) -> OpexSmartImportPreparation:
        (
            source,
            origin,
            budgeter,
            actor,
        ) = self.validate_request(
            source_path=source_path,
            origin=origin,
            budgeter=budgeter,
            actor=actor,
        )

        workbook = (
            OpexSmartTemplateLoader()
            .load(
                source
            )
        )

        snapshot = (
            OpexMasterDataLoader(
                self._masters_directory
            )
            .load()
        )

        state_service = (
            self._build_state_service(
                snapshot
            )
        )

        workbook_state = (
            state_service
            .create_workbook_state(
                workbook
            )
        )

        (
            OpexSmartDefaultResolutionService(
                state_service=state_service
            )
            .apply_workbook_defaults(
                workbook_state
            )
        )

        fx_table = (
            OpexFxLoader()
            .load(
                self._masters_directory
                / "TC.xlsx"
            )
        )

        fx = (
            OpexFxService(
                fx_table
            )
        )

        rows = (
            OpexSmartFinalizationService(
                state_service=(
                    state_service
                ),
                amount_provider=(
                    fx.monthly_values
                ),
            )
            .build_rows(
                workbook_state,
                context=(
                    OpexSmartInsertionContext(
                        origen=origin,
                        presupuestador=budgeter,
                        periodo="2027 PB",
                    )
                ),
                actor=actor,
            )
        )

        if not rows:
            raise (
                OpexSmartImportPreparationError(
                    "La plantilla no produjo "
                    "ninguna fila OPEX."
                )
            )

        return self._build_result(
            source=source,
            workbook=workbook,
            workbook_state=(
                workbook_state
            ),
            rows=rows,
        )
