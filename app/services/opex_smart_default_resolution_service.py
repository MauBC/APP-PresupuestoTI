from dataclasses import dataclass

from app.services.opex_template_distribution_service import (
    OpexTemplateDistributionService,
)


class OpexSmartDefaultResolutionError(
    ValueError
):
    pass


@dataclass(
    frozen=True,
    slots=True,
)
class OpexSmartDefaultDecision:
    sheet_name: str
    account_name: str
    atributo_2: str
    distribution_mode: str
    cebe_defaults: tuple[str, ...]


class OpexSmartDefaultResolutionService:
    DEFAULT_CATEGORY = (
        "Equipo informático"
    )

    DEFAULT_ACCOUNT_NAME = (
        "MANT. Y REPAR. SOFTWARE ADM"
    )

    DEFAULT_ATTRIBUTE_2 = (
        "GASTOS TI"
    )

    def __init__(
        self,
        *,
        state_service,
    ):
        self._state_service = (
            state_service
        )

    def apply_budget_defaults(
        self,
        state,
    ) -> OpexSmartDefaultDecision:
        budget = state.budget

        self._state_service.select_account(
            state,
            categoria_gasto=(
                self.DEFAULT_CATEGORY
            ),
            nombre_cuenta=(
                self.DEFAULT_ACCOUNT_NAME
            ),
            atributo_2=(
                self.DEFAULT_ATTRIBUTE_2
            ),
        )

        plan = (
            self._state_service
            .plan(
                state
            )
        )

        selected_cebes = []

        for requirement in (
            plan.cebe_requirements
        ):
            if not requirement.options:
                raise (
                    OpexSmartDefaultResolutionError(
                        "El CEBE "
                        f"{requirement.centro_beneficio} "
                        "no tiene opciones oficiales."
                    )
                )

            selection = (
                requirement.options[0]
            )

            self._state_service.select_cebe(
                state,
                requirement
                .centro_beneficio,
                selection,
            )

            selected_cebes.append(
                requirement
                .centro_beneficio
            )

        status = (
            self._state_service
            .plan(
                state
            )
            .distribution_status
        )

        if status.amount_valid:
            inputs = (
                OpexTemplateDistributionService
                .amount_inputs(
                    budget
                )
            )

            resolved = (
                OpexTemplateDistributionService
                .resolve_amounts(
                    budget,
                    inputs,
                )
            )

        elif status.percentage_valid:
            inputs = (
                OpexTemplateDistributionService
                .percentage_inputs(
                    budget
                )
            )

            resolved = (
                OpexTemplateDistributionService
                .resolve_percentages(
                    budget,
                    inputs,
                )
            )

        else:
            raise (
                OpexSmartDefaultResolutionError(
                    "La hoja "
                    f"{budget.sheet_name} no tiene "
                    "una distribucion valida que "
                    "pueda resolverse "
                    "automaticamente."
                )
            )

        self._state_service.set_distribution(
            state,
            resolved,
        )

        final_plan = (
            self._state_service
            .plan(
                state
            )
        )

        if not final_plan.ready:
            codes = ", ".join(
                issue.code
                for issue
                in final_plan.issues
            )

            suffix = (
                f": {codes}"
                if codes
                else ""
            )

            raise (
                OpexSmartDefaultResolutionError(
                    "La hoja "
                    f"{budget.sheet_name} no quedo "
                    "lista despues de aplicar "
                    "los valores recomendados"
                    f"{suffix}."
                )
            )

        return (
            OpexSmartDefaultDecision(
                sheet_name=(
                    budget.sheet_name
                ),
                account_name=(
                    self.DEFAULT_ACCOUNT_NAME
                ),
                atributo_2=(
                    self.DEFAULT_ATTRIBUTE_2
                ),
                distribution_mode=(
                    resolved.mode
                ),
                cebe_defaults=tuple(
                    selected_cebes
                ),
            )
        )

    def apply_workbook_defaults(
        self,
        workbook_state,
    ) -> tuple[
        OpexSmartDefaultDecision,
        ...,
    ]:
        decisions = []

        for state in (
            workbook_state
            .budgets
            .values()
        ):
            decisions.append(
                self.apply_budget_defaults(
                    state
                )
            )

        if not (
            self._state_service
            .workbook_ready(
                workbook_state
            )
        ):
            raise (
                OpexSmartDefaultResolutionError(
                    "El libro no quedo listo "
                    "despues de aplicar las "
                    "resoluciones recomendadas."
                )
            )

        return tuple(
            decisions
        )
