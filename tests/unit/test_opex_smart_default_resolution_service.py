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
    ):
        self.requirements = tuple(
            requirements
        )
        self.account_calls = []
        self.cebe_calls = []

    def select_account(
        self,
        current,
        **kwargs,
    ):
        current.account_selection = (
            kwargs
        )
        self.account_calls.append(
            kwargs
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
            cebe_requirements=(
                self.requirements
            ),
            distribution_status=(
                distribution_status
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


def test_uses_first_official_cebe_option():
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

    assert (
        manager.cebe_calls
        == [
            (
                "51IC000000",
                "TESORERIA",
            )
        ]
    )

    assert (
        result.cebe_defaults
        == (
            "51IC000000",
        )
    )


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
