from app.config.opex_smart_precision import (
    OPEX_SMART_MONEY_QUANTUM,
)

from functools import partial

from collections import Counter
from decimal import Decimal
from pathlib import Path

from app.models.opex_smart_finalization import (
    OpexSmartInsertionContext,
)
from app.models.opex_smart_import import (
    OpexSmartImportAccountChoice,
    OpexSmartImportCebeChoice,
    OpexSmartImportCebeDecision,
    OpexSmartImportCebeOption,
    OpexSmartImportDecision,
    OpexSmartImportPreparation,
    OpexSmartImportSheetOverride,
    OpexSmartImportSheetReview,
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
from app.services.opex_template_distribution_service import (
    OpexTemplateDistributionService,
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

    @staticmethod
    def _cebe_option(
        centro_beneficio,
        record,
    ) -> OpexSmartImportCebeOption:
        return (
            OpexSmartImportCebeOption(
                centro_beneficio=str(
                    centro_beneficio
                ),
                desc_cebe=str(
                    record.desc_cebe
                    or ""
                ),
                macroservicio_cg=str(
                    record.macroservicio_cg
                    or ""
                ),
                tipo_servicio_cg=str(
                    record.tipo_servicio_cg
                    or ""
                ),
                region_cg=str(
                    record.region_cg
                    or ""
                ),
                sede_cg=str(
                    record.sede_cg
                    or ""
                ),
                segmentacion=str(
                    record.segmentacion
                    or ""
                ),
            )
        )

    @classmethod
    def _build_review_options(
        cls,
        *,
        workbook_state,
        state_service,
    ) -> tuple[
        OpexSmartImportSheetReview,
        ...,
    ]:
        result = []

        for (
            sheet_name,
            state,
        ) in (
            workbook_state
            .budgets
            .items()
        ):
            plan = (
                state_service
                .plan(
                    state
                )
            )

            account_options = []

            for group in (
                plan.account_groups
            ):
                for atributo in (
                    group.atributos_2
                ):
                    account_options.append(
                        OpexSmartImportAccountChoice(
                            categoria_gasto=str(
                                group.categoria_gasto
                            ),
                            nombre_cuenta=str(
                                group.nombre_cuenta
                            ),
                            atributo_2=str(
                                atributo
                            ),
                        )
                    )

            modes = []

            if (
                plan
                .distribution_status
                .amount_valid
            ):
                modes.append(
                    "IMPORTE"
                )

            if (
                plan
                .distribution_status
                .percentage_valid
            ):
                modes.append(
                    "PORCENTAJE"
                )

            cebe_choices = []

            for requirement in (
                plan.cebe_requirements
            ):
                cebe_choices.append(
                    OpexSmartImportCebeChoice(
                        centro_beneficio=str(
                            requirement
                            .centro_beneficio
                        ),
                        options=tuple(
                            cls._cebe_option(
                                requirement
                                .centro_beneficio,
                                record,
                            )
                            for record
                            in requirement.options
                        ),
                    )
                )

            result.append(
                OpexSmartImportSheetReview(
                    sheet_name=str(
                        sheet_name
                    ),
                    account_options=tuple(
                        account_options
                    ),
                    distribution_modes=tuple(
                        modes
                    ),
                    cebe_choices=tuple(
                        cebe_choices
                    ),
                )
            )

        return tuple(
            result
        )

    @staticmethod
    def _override_map(
        overrides,
    ):
        result = {}

        for override in (
            overrides
            or ()
        ):
            if not isinstance(
                override,
                OpexSmartImportSheetOverride,
            ):
                raise (
                    OpexSmartImportPreparationError(
                        "Override OPEX invalido."
                    )
                )

            key = str(
                override.sheet_name
            ).strip()

            if not key:
                raise (
                    OpexSmartImportPreparationError(
                        "El override no tiene "
                        "nombre de hoja."
                    )
                )

            if key in result:
                raise (
                    OpexSmartImportPreparationError(
                        "Existe mas de un override "
                        f"para {key}."
                    )
                )

            result[key] = override

        return result

    @classmethod
    def _apply_overrides(
        cls,
        *,
        workbook_state,
        state_service,
        overrides,
    ):
        override_map = (
            cls._override_map(
                overrides
            )
        )

        unknown = (
            set(
                override_map
            )
            -
            set(
                workbook_state
                .budgets
            )
        )

        if unknown:
            raise (
                OpexSmartImportPreparationError(
                    "Existen overrides para hojas "
                    "desconocidas: "
                    + ", ".join(
                        sorted(
                            unknown
                        )
                    )
                )
            )

        for (
            sheet_name,
            override,
        ) in override_map.items():
            state = (
                workbook_state
                .budgets[
                    sheet_name
                ]
            )

            if override.account is not None:
                (
                    state_service
                    .select_account(
                        state,
                        categoria_gasto=(
                            override
                            .account
                            .categoria_gasto
                        ),
                        nombre_cuenta=(
                            override
                            .account
                            .nombre_cuenta
                        ),
                        atributo_2=(
                            override
                            .account
                            .atributo_2
                        ),
                    )
                )

            if override.cebe_selections:
                plan = (
                    state_service
                    .plan(
                        state
                    )
                )

                requirements = {
                    str(
                        item
                        .centro_beneficio
                    ):
                        item
                    for item
                    in plan.cebe_requirements
                }

                used = set()

                for selection in (
                    override
                    .cebe_selections
                ):
                    key = str(
                        selection
                        .centro_beneficio
                    )

                    if key in used:
                        raise (
                            OpexSmartImportPreparationError(
                                "CEBE repetido en "
                                "override: "
                                f"{key}."
                            )
                        )

                    used.add(
                        key
                    )

                    requirement = (
                        requirements.get(
                            key
                        )
                    )

                    if requirement is None:
                        raise (
                            OpexSmartImportPreparationError(
                                "El CEBE "
                                f"{key} no requiere "
                                "una decision para "
                                f"{sheet_name}."
                            )
                        )

                    matches = [
                        record
                        for record
                        in requirement.options
                        if (
                            cls._cebe_option(
                                key,
                                record,
                            )
                            == selection
                        )
                    ]

                    if len(matches) != 1:
                        raise (
                            OpexSmartImportPreparationError(
                                "La seleccion para "
                                f"CEBE {key} no coincide "
                                "con una opcion oficial."
                            )
                        )

                    (
                        state_service
                        .select_cebe(
                            state,
                            key,
                            matches[0],
                        )
                    )

            if (
                override
                .distribution_mode
                is not None
            ):
                mode = str(
                    override
                    .distribution_mode
                ).strip().upper()

                plan = (
                    state_service
                    .plan(
                        state
                    )
                )

                status = (
                    plan
                    .distribution_status
                )

                if mode == "IMPORTE":
                    if not status.amount_valid:
                        raise (
                            OpexSmartImportPreparationError(
                                "IMPORTE no es una "
                                "distribucion valida "
                                f"para {sheet_name}."
                            )
                        )

                    resolved = (
                        OpexTemplateDistributionService
                        .resolve_amounts(
                            state.budget,
                            (
                                OpexTemplateDistributionService
                                .amount_inputs(
                                    state.budget
                                )
                            ),
                        )
                    )

                elif mode == "PORCENTAJE":
                    if not (
                        status
                        .percentage_valid
                    ):
                        raise (
                            OpexSmartImportPreparationError(
                                "PORCENTAJE no es una "
                                "distribucion valida "
                                f"para {sheet_name}."
                            )
                        )

                    resolved = (
                        OpexTemplateDistributionService
                        .resolve_percentages(
                            state.budget,
                            (
                                OpexTemplateDistributionService
                                .percentage_inputs(
                                    state.budget
                                )
                            ),
                        )
                    )

                else:
                    raise (
                        OpexSmartImportPreparationError(
                            "Modo de distribucion "
                            f"invalido: {mode}."
                        )
                    )

                (
                    state_service
                    .set_distribution(
                        state,
                        resolved,
                    )
                )

        if not (
            state_service
            .workbook_ready(
                workbook_state
            )
        ):
            raise (
                OpexSmartImportPreparationError(
                    "El libro no quedo listo "
                    "despues de aplicar las "
                    "decisiones del usuario."
                )
            )

    @classmethod
    def _build_pending_result(
        cls,
        *,
        source,
        workbook,
        workbook_state,
        review_options,
    ) -> OpexSmartImportPreparation:
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
            auto_cebe_count += len(
                state.cebe_selections
            )

            account = (
                state.account_selection
            )

            distribution = (
                state.resolved_distribution
            )

            # Solo guardamos una decision previa
            # si ya existe una cuenta realmente
            # seleccionada en el estado.
            if (
                account is None
                or distribution is None
            ):
                continue

            cebe_decisions = tuple(
                OpexSmartImportCebeDecision(
                    centro_beneficio=str(
                        centro_beneficio
                    ),
                    tipo_servicio_cg=str(
                        record.tipo_servicio_cg
                    ),
                )
                for (
                    centro_beneficio,
                    record,
                )
                in state
                .cebe_selections
                .items()
            )

            decisions.append(
                OpexSmartImportDecision(
                    sheet_name=str(
                        sheet_name
                    ),
                    account_name=str(
                        account.nombre_cuenta
                    ),
                    atributo_2=str(
                        account.atributo_2
                    ),
                    distribution_mode=str(
                        distribution.mode
                    ),
                    cebe_decisions=(
                        cebe_decisions
                    ),
                )
            )

        return (
            OpexSmartImportPreparation(
                rows=(),
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
                total_usd=Decimal(
                    "0.00"
                ),
                country_counts=(),
                invoice_currency_counts=(),
                review_options=tuple(
                    review_options
                ),
                decisions=tuple(
                    decisions
                ),
            )
        )

    @classmethod
    def _build_result(
        cls,
        *,
        source,
        workbook,
        workbook_state,
        rows,
        review_options=(),
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
                review_options=tuple(
                    review_options
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
        overrides=None,
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

        review_options = (
            self._build_review_options(
                workbook_state=(
                    workbook_state
                ),
                state_service=(
                    state_service
                ),
            )
        )

        if overrides:
            self._apply_overrides(
                workbook_state=(
                    workbook_state
                ),
                state_service=(
                    state_service
                ),
                overrides=overrides,
            )

        if not (
            state_service
            .workbook_ready(
                workbook_state
            )
        ):
            return (
                self._build_pending_result(
                    source=source,
                    workbook=workbook,
                    workbook_state=(
                        workbook_state
                    ),
                    review_options=(
                        review_options
                    ),
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
                    partial(
                        fx.monthly_values,
                        quantum=(
                            OPEX_SMART_MONEY_QUANTUM
                        ),
                    )
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
            review_options=(
                review_options
            ),
        )
