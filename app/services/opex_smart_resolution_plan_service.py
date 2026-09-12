from decimal import Decimal

from app.models.opex_smart_resolution_plan import (
    OpexSmartBudgetResolutionPlan,
    OpexSmartResolutionPlanIssue,
)
from app.services.opex_smart_resolution_service import (
    OpexSmartResolutionError,
    OpexSmartResolutionService,
)
from app.services.opex_template_distribution_service import (
    OpexTemplateDistributionService,
)


class OpexSmartResolutionPlanService:
    def __init__(
        self,
        *,
        analysis_service,
        resolution_service: OpexSmartResolutionService,
        distribution_service=None,
    ):
        self._analysis_service = analysis_service
        self._resolution_service = resolution_service
        self._distribution_service = (
            distribution_service
            or OpexTemplateDistributionService()
        )

    @staticmethod
    def _issue(
        code,
        message,
        *,
        key=None,
    ):
        return OpexSmartResolutionPlanIssue(
            code=code,
            message=message,
            key=key,
        )

    @staticmethod
    def _append_issue(
        issues,
        issue,
    ):
        identity = (
            issue.code,
            issue.message,
            issue.key,
        )

        existing = {
            (
                current.code,
                current.message,
                current.key,
            )
            for current in issues
        }

        if identity not in existing:
            issues.append(
                issue
            )

    def _automatic_account(
        self,
        numero_cuenta,
        groups,
    ):
        combinations = []

        for group in groups:
            for atributo in group.atributos_2:
                combinations.append(
                    (
                        group.categoria_gasto,
                        group.nombre_cuenta,
                        atributo,
                    )
                )

        if len(combinations) != 1:
            return None

        (
            categoria,
            nombre,
            atributo,
        ) = combinations[0]

        return (
            self._resolution_service
            .select_account(
                numero_cuenta,
                categoria_gasto=categoria,
                nombre_cuenta=nombre,
                atributo_2=atributo,
            )
        )

    def _validate_account(
        self,
        budget,
        groups,
        selection,
    ):
        if selection is None:
            return self._automatic_account(
                budget.numero_cuenta,
                groups,
            )

        selected = (
            self._resolution_service
            .select_account(
                budget.numero_cuenta,
                categoria_gasto=(
                    selection.categoria_gasto
                ),
                nombre_cuenta=(
                    selection.nombre_cuenta
                ),
                atributo_2=(
                    selection.atributo_2
                ),
            )
        )

        if selected != selection:
            raise OpexSmartResolutionError(
                "ACCOUNT_SELECTION_INVALID",
                (
                    "La seleccion de cuenta no "
                    "coincide exactamente con una "
                    "definicion oficial."
                ),
                key=budget.numero_cuenta,
            )

        return selected

    @staticmethod
    def _validate_distribution(
        budget,
        resolved,
    ):
        if resolved is None:
            return False, None

        expected = tuple(
            str(
                item.ceco
            ).strip().upper()
            for item in budget.distributions
        )

        received = tuple(
            str(
                ceco
            ).strip().upper()
            for ceco, _amount
            in resolved.amounts
        )

        if expected != received:
            return (
                False,
                OpexSmartResolutionPlanIssue(
                    code="DISTRIBUTION_MISMATCH",
                    message=(
                        "Los CECO de la distribucion "
                        "resuelta no coinciden con "
                        "la plantilla."
                    ),
                ),
            )

        total = sum(
            (
                Decimal(amount)
                for _ceco, amount
                in resolved.amounts
            ),
            Decimal("0"),
        )

        target = Decimal(
            budget.monto
        )

        if total != target:
            return (
                False,
                OpexSmartResolutionPlanIssue(
                    code=(
                        "DISTRIBUTION_TOTAL_MISMATCH"
                    ),
                    message=(
                        "La distribucion resuelta "
                        f"suma {total} y el monto "
                        f"objetivo es {target}."
                    ),
                ),
            )

        return True, None

    def build_plan(
        self,
        budget,
        *,
        account_selection=None,
        cebe_selections=None,
        resolved_distribution=None,
    ) -> OpexSmartBudgetResolutionPlan:
        cebe_selections = (
            cebe_selections
            or {}
        )

        analysis = (
            self._analysis_service
            .analyze_budget(
                budget
            )
        )

        issues = []

        # Los ACCOUNT_AMBIGUOUS se representan
        # como una seleccion pendiente.
        for issue in analysis.budget_issues:
            if issue.code == "ACCOUNT_AMBIGUOUS":
                continue

            self._append_issue(
                issues,
                self._issue(
                    issue.code,
                    issue.message,
                ),
            )

        # Los CEBE_AMBIGUOUS se representan
        # como requisitos de seleccion.
        for issue in analysis.issues:
            if issue.code == "CEBE_AMBIGUOUS":
                continue

            self._append_issue(
                issues,
                self._issue(
                    issue.code,
                    issue.message,
                    key=issue.ceco,
                ),
            )

        # -------------------------------------------------
        # Cuenta
        # -------------------------------------------------

        account_groups = ()

        try:
            account_groups = (
                self._resolution_service
                .account_choice_groups(
                    budget.numero_cuenta
                )
            )

        except OpexSmartResolutionError as exc:
            self._append_issue(
                issues,
                self._issue(
                    exc.code,
                    str(exc),
                    key=exc.key,
                ),
            )

        selected_account = None

        if account_groups:
            try:
                selected_account = (
                    self._validate_account(
                        budget,
                        account_groups,
                        account_selection,
                    )
                )

            except OpexSmartResolutionError as exc:
                self._append_issue(
                    issues,
                    self._issue(
                        exc.code,
                        str(exc),
                        key=exc.key,
                    ),
                )

        account_resolved = (
            selected_account is not None
        )

        # -------------------------------------------------
        # CEBE
        # -------------------------------------------------

        requirements = (
            self._resolution_service
            .cebe_requirements(
                budget
            )
        )

        unresolved_cebes = []

        for requirement in requirements:
            key = (
                requirement.centro_beneficio
            )

            selection = (
                cebe_selections.get(
                    key
                )
            )

            if selection is None:
                unresolved_cebes.append(
                    key
                )
                continue

            if selection not in requirement.options:
                self._append_issue(
                    issues,
                    self._issue(
                        "CEBE_SELECTION_INVALID",
                        (
                            "La seleccion del CEBE "
                            f"{key} no pertenece a "
                            "sus alternativas oficiales."
                        ),
                        key=key,
                    ),
                )

                unresolved_cebes.append(
                    key
                )

        cebe_resolved = (
            not unresolved_cebes
        )

        # -------------------------------------------------
        # Distribucion
        # -------------------------------------------------

        (
            distribution_resolved,
            distribution_issue,
        ) = self._validate_distribution(
            budget,
            resolved_distribution,
        )

        if distribution_issue is not None:
            self._append_issue(
                issues,
                distribution_issue,
            )

        ready = (
            account_resolved
            and cebe_resolved
            and distribution_resolved
            and not issues
        )

        return OpexSmartBudgetResolutionPlan(
            sheet_name=(
                budget.sheet_name
            ),
            account_groups=(
                account_groups
            ),
            account_selection=(
                selected_account
            ),
            account_resolved=(
                account_resolved
            ),
            cebe_requirements=(
                requirements
            ),
            unresolved_cebes=tuple(
                unresolved_cebes
            ),
            cebe_resolved=(
                cebe_resolved
            ),
            distribution_status=(
                analysis.distribution_status
            ),
            resolved_distribution=(
                resolved_distribution
            ),
            distribution_resolved=(
                distribution_resolved
            ),
            issues=tuple(
                issues
            ),
            ready=ready,
        )
