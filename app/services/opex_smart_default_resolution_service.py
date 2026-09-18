from dataclasses import dataclass

from app.services.opex_template_distribution_service import (
    OpexTemplateDistributionService,
)


class OpexSmartDefaultResolutionError(
    ValueError
):
    def __init__(self, message, *, sheet_name=None, issues=()):
        super().__init__(message)
        self.sheet_name = sheet_name
        self.issues = tuple(issues)


@dataclass(
    frozen=True,
    slots=True,
)
class OpexSmartDefaultDecision:
    sheet_name: str
    account_name: str | None
    atributo_2: str | None
    distribution_mode: str
    cebe_defaults: tuple[str, ...]


class OpexSmartDefaultResolutionService:
    ISSUE_PREVIEW_LIMIT = 5

    @classmethod
    def _blocking_error(cls, sheet_name, issues):
        issues = tuple(issues)
        lines = [f'La hoja "{sheet_name}" tiene {len(issues)} incidencias bloqueantes.']
        for issue in issues[:cls.ISSUE_PREVIEW_LIMIT]:
            context = []
            if issue.excel_row is not None:
                context.append(f"Fila Excel {issue.excel_row}")
            if issue.ceco is not None:
                context.append(f"CECO {issue.ceco}")
            elif issue.key is not None:
                context.append(f"Referencia {issue.key}")
            prefix = " | ".join(context)
            if prefix:
                prefix += " | "
            lines.append(f"{prefix}{issue.code}: {issue.message}")
        remaining = len(issues) - cls.ISSUE_PREVIEW_LIMIT
        if remaining > 0:
            lines.append(f"Hay {remaining} incidencias adicionales en esta hoja.")
        lines.append("Corrige los datos indicados y vuelve a analizar la plantilla.")
        return OpexSmartDefaultResolutionError(
            "\n".join(lines), sheet_name=sheet_name, issues=issues,
        )

    DEFAULT_CATEGORY = (
        "Equipo inform\u00e1tico"
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

    @staticmethod
    def _account_combinations(
        plan,
    ):
        result = []

        for group in getattr(
            plan,
            "account_groups",
            (),
        ):
            for atributo in (
                group.atributos_2
            ):
                result.append(
                    (
                        str(
                            group.categoria_gasto
                        ),
                        str(
                            group.nombre_cuenta
                        ),
                        str(
                            atributo
                        ),
                    )
                )

        return tuple(
            result
        )

    def _apply_safe_account_default(
        self,
        state,
        plan,
    ):
        combinations = (
            self._account_combinations(
                plan
            )
        )

        if not combinations:
            return None

        recommended = (
            self.DEFAULT_CATEGORY,
            self.DEFAULT_ACCOUNT_NAME,
            self.DEFAULT_ATTRIBUTE_2,
        )

        if recommended in combinations:
            selected = recommended

        elif len(combinations) == 1:
            selected = combinations[0]

        else:
            # Varias definiciones oficiales.
            # No se inventa una seleccion:
            # debe decidir el usuario.
            return None

        (
            categoria,
            nombre,
            atributo,
        ) = selected

        return (
            self._state_service
            .select_account(
                state,
                categoria_gasto=categoria,
                nombre_cuenta=nombre,
                atributo_2=atributo,
            )
        )

    def apply_budget_defaults(
        self,
        state,
    ) -> OpexSmartDefaultDecision:
        budget = state.budget

        initial_plan = (
            self._state_service
            .plan(
                state
            )
        )

        self._apply_safe_account_default(
            state,
            initial_plan,
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

            # Conservar decisiones previas; una ambiguedad real requiere
            # seleccion explicita y debe llegar pendiente al editor.
            if requirement.centro_beneficio in state.cebe_selections:
                continue
            if len(requirement.options) != 1:
                continue
            selection = requirement.options[0]

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

        # Los errores reales siguen bloqueando.
        # ACCOUNT_AMBIGUOUS no llega aqui como
        # issue: el plan lo representa como una
        # decision pendiente.
        if final_plan.issues:
            raise self._blocking_error(
                budget.sheet_name,
                final_plan.issues,
            )

        if not getattr(
            final_plan,
            "distribution_resolved",
            True,
        ):
            raise (
                OpexSmartDefaultResolutionError(
                    "La hoja "
                    f"{budget.sheet_name} conserva "
                    "la distribucion pendiente."
                )
            )

        account = (
            state.account_selection
        )

        return (
            OpexSmartDefaultDecision(
                sheet_name=(
                    budget.sheet_name
                ),
                account_name=(
                    None
                    if account is None
                    else str(
                        account.nombre_cuenta
                    )
                ),
                atributo_2=(
                    None
                    if account is None
                    else str(
                        account.atributo_2
                    )
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

        # No exigimos workbook_ready aqui.
        #
        # Una cuenta con varias alternativas
        # oficiales puede quedar pendiente para
        # que el usuario la resuelva en la UI.
        return tuple(
            decisions
        )
