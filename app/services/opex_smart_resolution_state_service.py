from app.models.opex_smart_resolution_state import (
    OpexSmartBudgetResolutionState,
    OpexSmartWorkbookResolutionState,
)
from app.services.opex_smart_resolution_plan_service import (
    OpexSmartResolutionPlanService,
)
from app.services.opex_smart_resolution_service import (
    OpexSmartResolutionService,
)


class OpexSmartResolutionStateError(
    ValueError
):
    def __init__(
        self,
        code,
        message,
        *,
        key=None,
    ):
        super().__init__(
            message
        )

        self.code = code
        self.key = key


class OpexSmartResolutionStateService:
    def __init__(
        self,
        *,
        plan_service:
        OpexSmartResolutionPlanService,
        resolution_service:
        OpexSmartResolutionService,
    ):
        self._plan_service = (
            plan_service
        )

        self._resolution_service = (
            resolution_service
        )

    @staticmethod
    def create_budget_state(
        budget,
    ) -> OpexSmartBudgetResolutionState:
        return (
            OpexSmartBudgetResolutionState(
                budget=budget
            )
        )

    def create_workbook_state(
        self,
        workbook,
    ) -> OpexSmartWorkbookResolutionState:
        states = {}

        for budget in workbook.budgets:
            key = budget.sheet_name

            if key in states:
                raise (
                    OpexSmartResolutionStateError(
                        "DUPLICATE_SHEET",
                        (
                            "La plantilla contiene "
                            "mas de una hoja llamada "
                            f"{key}."
                        ),
                        key=key,
                    )
                )

            states[key] = (
                self.create_budget_state(
                    budget
                )
            )

        return (
            OpexSmartWorkbookResolutionState(
                source_path=(
                    workbook.source_path
                ),
                budgets=states,
            )
        )

    @staticmethod
    def get_budget_state(
        workbook_state,
        sheet_name,
    ) -> OpexSmartBudgetResolutionState:
        try:
            return (
                workbook_state
                .budgets[
                    sheet_name
                ]
            )

        except KeyError as exc:
            raise (
                OpexSmartResolutionStateError(
                    "SHEET_NOT_FOUND",
                    (
                        "No existe la hoja "
                        f"{sheet_name} en el estado."
                    ),
                    key=sheet_name,
                )
            ) from exc

    def select_account(
        self,
        state,
        *,
        categoria_gasto,
        nombre_cuenta,
        atributo_2,
    ):
        state.account_selection = (
            self._resolution_service
            .select_account(
                state
                .budget
                .numero_cuenta,
                categoria_gasto=(
                    categoria_gasto
                ),
                nombre_cuenta=(
                    nombre_cuenta
                ),
                atributo_2=(
                    atributo_2
                ),
            )
        )

        return state.account_selection

    @staticmethod
    def clear_account(
        state,
    ):
        state.account_selection = None

    def select_cebe(
        self,
        state,
        centro_beneficio,
        selection,
    ):
        requirements = {
            item.centro_beneficio:
                item
            for item in (
                self._resolution_service
                .cebe_requirements(
                    state.budget
                )
            )
        }

        requirement = (
            requirements.get(
                centro_beneficio
            )
        )

        if requirement is None:
            raise (
                OpexSmartResolutionStateError(
                    "CEBE_SELECTION_NOT_REQUIRED",
                    (
                        "El CEBE "
                        f"{centro_beneficio} "
                        "no requiere seleccion "
                        "manual."
                    ),
                    key=centro_beneficio,
                )
            )

        if (
            selection
            not in requirement.options
        ):
            raise (
                OpexSmartResolutionStateError(
                    "CEBE_SELECTION_INVALID",
                    (
                        "La seleccion del CEBE "
                        f"{centro_beneficio} "
                        "no pertenece a las "
                        "alternativas oficiales."
                    ),
                    key=centro_beneficio,
                )
            )

        state.cebe_selections[
            centro_beneficio
        ] = selection

        return selection

    @staticmethod
    def clear_cebe(
        state,
        centro_beneficio,
    ):
        state.cebe_selections.pop(
            centro_beneficio,
            None,
        )

    @staticmethod
    def set_distribution(
        state,
        resolved_distribution,
    ):
        state.resolved_distribution = (
            resolved_distribution
        )

    @staticmethod
    def clear_distribution(
        state,
    ):
        state.resolved_distribution = None

    def plan(
        self,
        state,
    ):
        return (
            self._plan_service
            .build_plan(
                state.budget,
                account_selection=(
                    state.account_selection
                ),
                cebe_selections=(
                    state.cebe_selections
                ),
                resolved_distribution=(
                    state
                    .resolved_distribution
                ),
            )
        )

    def workbook_plans(
        self,
        workbook_state,
    ):
        return {
            sheet_name: self.plan(
                state
            )
            for (
                sheet_name,
                state,
            )
            in workbook_state
            .budgets
            .items()
        }

    def workbook_ready(
        self,
        workbook_state,
    ) -> bool:
        plans = (
            self.workbook_plans(
                workbook_state
            )
        )

        return (
            bool(plans)
            and all(
                plan.ready
                for plan in plans.values()
            )
        )

    @staticmethod
    def _pending_description(
        plan,
    ):
        pending = []

        if not plan.account_resolved:
            pending.append(
                "cuenta"
            )

        if not plan.cebe_resolved:
            pending.append(
                "CEBE: "
                + ", ".join(
                    plan.unresolved_cebes
                )
            )

        if not plan.distribution_resolved:
            pending.append(
                "distribucion"
            )

        if plan.issues:
            pending.append(
                "issues: "
                + ", ".join(
                    issue.code
                    for issue
                    in plan.issues
                )
            )

        return "; ".join(
            pending
        )

    def build_rows(
        self,
        state,
    ):
        plan = self.plan(
            state
        )

        if not plan.ready:
            raise (
                OpexSmartResolutionStateError(
                    "RESOLUTION_NOT_READY",
                    (
                        "La hoja "
                        f"{state.budget.sheet_name} "
                        "todavia no esta lista: "
                        f"{self._pending_description(plan)}."
                    ),
                    key=(
                        state
                        .budget
                        .sheet_name
                    ),
                )
            )

        return (
            self._resolution_service
            .build_rows(
                budget=state.budget,
                resolved=(
                    state
                    .resolved_distribution
                ),
                account_selection=(
                    state.account_selection
                ),
                cebe_selections=(
                    state.cebe_selections
                ),
            )
        )

    def build_workbook_rows(
        self,
        workbook_state,
    ):
        rows = []

        for state in (
            workbook_state
            .budgets
            .values()
        ):
            rows.extend(
                self.build_rows(
                    state
                )
            )

        return tuple(
            rows
        )
