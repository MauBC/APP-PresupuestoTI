from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.models.opex_smart_template import (
    OpexTemplateBudget,
    OpexTemplateDistribution,
)
from app.services.opex_smart_default_resolution_service import (
    OpexSmartDefaultResolutionError,
    OpexSmartDefaultResolutionService,
)
from app.services.opex_template_distribution_service import (
    OpexTemplateDistributionService,
)


pytestmark = pytest.mark.unit


DEFAULT_ACCOUNT_GROUP = (
    SimpleNamespace(
        categoria_gasto=(
            OpexSmartDefaultResolutionService
            .DEFAULT_CATEGORY
        ),
        nombre_cuenta=(
            OpexSmartDefaultResolutionService
            .DEFAULT_ACCOUNT_NAME
        ),
        atributos_2=(
            OpexSmartDefaultResolutionService
            .DEFAULT_ATTRIBUTE_2,
        ),
    )
)


def budget(
    *,
    percentages=True,
    amounts=True,
):
    return OpexTemplateBudget(
        sheet_name="Sheet1",
        nombre_gasto="GASTO",
        proveedor="PROVEEDOR",
        moneda_facturacion="USD",
        numero_cuenta="635610007",
        tipo="MENSUAL",
        monto=Decimal("100"),
        distributions=(
            OpexTemplateDistribution(
                excel_row=8,
                ceco="CECO1",
                percentage=(
                    Decimal("0.50")
                    if percentages
                    else None
                ),
                amount=(
                    Decimal("1")
                    if amounts
                    else None
                ),
            ),
            OpexTemplateDistribution(
                excel_row=9,
                ceco="CECO2",
                percentage=(
                    Decimal("0.50")
                    if percentages
                    else None
                ),
                amount=(
                    Decimal("3")
                    if amounts
                    else None
                ),
            ),
        ),
    )


def state(
    value=None,
):
    return SimpleNamespace(
        budget=(
            value
            if value is not None
            else budget()
        ),
        account_selection=None,
        cebe_selections={},
        resolved_distribution=None,
    )


class FakeStateService:
    def __init__(
        self,
        requirements=(),
        account_groups=None,
    ):
        self.requirements = tuple(
            requirements
        )

        self.account_groups = tuple(
            (
                DEFAULT_ACCOUNT_GROUP,
            )
            if account_groups is None
            else account_groups
        )

        self.account_calls = []
        self.cebe_calls = []

    def select_account(
        self,
        current,
        **kwargs,
    ):
        current.account_selection = (
            SimpleNamespace(
                **kwargs
            )
        )

        self.account_calls.append(
            kwargs
        )

        return (
            current.account_selection
        )

    def select_cebe(
        self,
        current,
        key,
        selection,
    ):
        current.cebe_selections[
            key
        ] = selection

        self.cebe_calls.append(
            (
                key,
                selection,
            )
        )

    @staticmethod
    def set_distribution(
        current,
        resolved,
    ):
        current.resolved_distribution = (
            resolved
        )

    def plan(
        self,
        current,
    ):
        distribution_status = (
            OpexTemplateDistributionService
            .inspect(
                current.budget
            )
        )

        cebe_ready = all(
            requirement
            .centro_beneficio
            in current.cebe_selections
            for requirement
            in self.requirements
        )

        ready = (
            current.account_selection
            is not None
            and cebe_ready
            and current.resolved_distribution
            is not None
        )

        return SimpleNamespace(
            account_groups=(
                self.account_groups
            ),
            account_resolved=(
                current.account_selection
                is not None
            ),
            cebe_requirements=(
                self.requirements
            ),
            cebe_resolved=(
                cebe_ready
            ),
            distribution_status=(
                distribution_status
            ),
            distribution_resolved=(
                current.resolved_distribution
                is not None
            ),
            issues=(),
            ready=ready,
        )

    def workbook_ready(
        self,
        workbook_state,
    ):
        return all(
            self.plan(
                current
            ).ready
            for current
            in workbook_state
            .budgets
            .values()
        )


def service(
    manager=None,
):
    manager = (
        manager
        or FakeStateService()
    )

    return (
        OpexSmartDefaultResolutionService(
            state_service=manager
        )
    )


def test_prefers_amount_weights_when_both_modes_exist():
    current = state()

    result = (
        service()
        .apply_budget_defaults(
            current
        )
    )

    assert (
        result.distribution_mode
        == "IMPORTE"
    )

    assert (
        current
        .resolved_distribution
        .amount_map()
        == {
            "CECO1":
                Decimal("25.00"),
            "CECO2":
                Decimal("75.00"),
        }
    )


def test_falls_back_to_percentage():
    current = state(
        budget(
            percentages=True,
            amounts=False,
        )
    )

    result = (
        service()
        .apply_budget_defaults(
            current
        )
    )

    assert (
        result.distribution_mode
        == "PORCENTAJE"
    )

    assert (
        current
        .resolved_distribution
        .total
        == Decimal("100.00")
    )


def test_uses_recommended_account():
    current = state()

    manager = FakeStateService()

    value = (
        OpexSmartDefaultResolutionService(
            state_service=manager
        )
    )

    value.apply_budget_defaults(
        current
    )

    assert (
        manager.account_calls
        == [
            {
                "categoria_gasto":
                    "Equipo informático",
                "nombre_cuenta":
                    (
                        "MANT. Y REPAR. "
                        "SOFTWARE ADM"
                    ),
                "atributo_2":
                    "GASTOS TI",
            }
        ]
    )


def test_ambiguous_cebe_remains_pending_for_explicit_selection():
    requirement = (
        SimpleNamespace(
            centro_beneficio=(
                "51IC000000"
            ),
            options=(
                "TESORERIA",
                "FACTURACION",
            ),
        )
    )

    manager = FakeStateService(
        (
            requirement,
        )
    )

    current = state()

    result = (
        OpexSmartDefaultResolutionService(
            state_service=manager
        )
        .apply_budget_defaults(
            current
        )
    )

    assert manager.cebe_calls == []
    assert current.cebe_selections == {}
    assert result.cebe_defaults == ()
    assert not manager.plan(current).ready

    current.cebe_selections["51IC000000"] = "FACTURACION"
    OpexSmartDefaultResolutionService(state_service=manager).apply_budget_defaults(current)
    assert current.cebe_selections["51IC000000"] == "FACTURACION"
    assert manager.cebe_calls == []


def test_rejects_unresolvable_distribution():
    current = state(
        budget(
            percentages=False,
            amounts=False,
        )
    )

    with pytest.raises(
        OpexSmartDefaultResolutionError,
        match="distribucion valida",
    ):
        (
            service()
            .apply_budget_defaults(
                current
            )
        )


def test_applies_defaults_to_full_workbook():
    first = state()
    second = state()

    workbook_state = (
        SimpleNamespace(
            budgets={
                "Sheet1":
                    first,
                "Sheet2":
                    second,
            }
        )
    )

    result = (
        service()
        .apply_workbook_defaults(
            workbook_state
        )
    )

    assert len(result) == 2

    assert all(
        current
        .resolved_distribution
        is not None
        for current in (
            first,
            second,
        )
    )



def test_multiple_official_accounts_remain_pending_for_user():
    current = state()

    groups = (
        SimpleNamespace(
            categoria_gasto=(
                "Licencias / Suscripciones"
            ),
            nombre_cuenta=(
                "Consultoria TI"
            ),
            atributos_2=(
                "GASTOS TI",
                "OTROS GASTOS",
            ),
        ),
        SimpleNamespace(
            categoria_gasto=(
                "Licencias / Suscripciones"
            ),
            nombre_cuenta=(
                "Mantenimiento de Licencias "
                "Infraestructura TI"
            ),
            atributos_2=(
                "GASTOS TI",
            ),
        ),
    )

    manager = FakeStateService(
        account_groups=groups
    )

    result = (
        OpexSmartDefaultResolutionService(
            state_service=manager
        )
        .apply_budget_defaults(
            current
        )
    )

    assert (
        current.account_selection
        is None
    )

    assert result.account_name is None

    assert (
        current.resolved_distribution
        is not None
    )


def test_single_official_account_is_selected_safely():
    current = state()

    groups = (
        SimpleNamespace(
            categoria_gasto=(
                "Licencias / Suscripciones"
            ),
            nombre_cuenta=(
                "Consultoria TI"
            ),
            atributos_2=(
                "GASTOS TI",
            ),
        ),
    )

    manager = FakeStateService(
        account_groups=groups
    )

    result = (
        OpexSmartDefaultResolutionService(
            state_service=manager
        )
        .apply_budget_defaults(
            current
        )
    )

    assert (
        current
        .account_selection
        .nombre_cuenta
        == "Consultoria TI"
    )

    assert (
        result.account_name
        == "Consultoria TI"
    )


def test_workbook_defaults_allow_pending_account_decision():
    current = state()

    groups = (
        SimpleNamespace(
            categoria_gasto="CAT",
            nombre_cuenta="CUENTA",
            atributos_2=(
                "A",
                "B",
            ),
        ),
    )

    manager = FakeStateService(
        account_groups=groups
    )

    workbook_state = (
        SimpleNamespace(
            budgets={
                "Sheet1":
                    current,
            }
        )
    )

    decisions = (
        OpexSmartDefaultResolutionService(
            state_service=manager
        )
        .apply_workbook_defaults(
            workbook_state
        )
    )

    assert len(decisions) == 1

    assert (
        current.account_selection
        is None
    )

    assert not (
        manager.workbook_ready(
            workbook_state
        )
    )
