from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.models.opex_smart_import import (
    OpexSmartImportAccountChoice,
    OpexSmartImportCebeOption,
    OpexSmartImportSheetOverride,
)
from app.models.opex_smart_template import (
    OpexTemplateBudget,
    OpexTemplateDistribution,
)
from app.services.opex_smart_import_preparation_service import (
    OpexSmartImportPreparationError,
    OpexSmartImportPreparationService,
)
from app.services.opex_template_distribution_service import (
    OpexTemplateDistributionService,
)


pytestmark = pytest.mark.unit


ACCOUNT_GROUP = SimpleNamespace(
    categoria_gasto="Equipo informático",
    nombre_cuenta=(
        "MANT. Y REPAR. SOFTWARE ADM"
    ),
    atributos_2=(
        "GASTOS TI",
        "OTRO",
    ),
)


CEBE_A = SimpleNamespace(
    desc_cebe="TESORERIA",
    macroservicio_cg="SOP. CORPORATIVO",
    tipo_servicio_cg="TESORERIA",
    region_cg="NEUTRO",
    sede_cg="NEUTRO",
    segmentacion=(
        "FINANZAS Y ADMINISTRACION"
    ),
)


CEBE_B = SimpleNamespace(
    desc_cebe="TESORERIA",
    macroservicio_cg="SOP. CORPORATIVO",
    tipo_servicio_cg="FACTURACION",
    region_cg="NEUTRO",
    sede_cg="NEUTRO",
    segmentacion=(
        "FINANZAS Y ADMINISTRACION"
    ),
)


def budget():
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
                ),
                amount=Decimal("1"),
            ),
            OpexTemplateDistribution(
                excel_row=9,
                ceco="CECO2",
                percentage=(
                    Decimal("0.50")
                ),
                amount=Decimal("3"),
            ),
        ),
    )


def requirement():
    return SimpleNamespace(
        centro_beneficio="51IC000000",
        options=(
            CEBE_A,
            CEBE_B,
        ),
    )


def make_state():
    return SimpleNamespace(
        budget=budget(),
        account_selection=(
            SimpleNamespace(
                categoria_gasto=(
                    "Equipo informático"
                ),
                nombre_cuenta=(
                    "MANT. Y REPAR. "
                    "SOFTWARE ADM"
                ),
                atributo_2="GASTOS TI",
            )
        ),
        cebe_selections={
            "51IC000000":
                CEBE_A,
        },
        resolved_distribution=(
            OpexTemplateDistributionService
            .resolve_amounts(
                budget(),
                {
                    "CECO1":
                        Decimal("1"),
                    "CECO2":
                        Decimal("3"),
                },
            )
        ),
    )


class FakeStateService:
    def plan(
        self,
        state,
    ):
        return SimpleNamespace(
            account_groups=(
                ACCOUNT_GROUP,
            ),
            cebe_requirements=(
                requirement(),
            ),
            distribution_status=(
                OpexTemplateDistributionService
                .inspect(
                    state.budget
                )
            ),
        )

    @staticmethod
    def select_account(
        state,
        *,
        categoria_gasto,
        nombre_cuenta,
        atributo_2,
    ):
        state.account_selection = (
            SimpleNamespace(
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

    @staticmethod
    def select_cebe(
        state,
        key,
        selection,
    ):
        state.cebe_selections[
            key
        ] = selection

    @staticmethod
    def set_distribution(
        state,
        resolved,
    ):
        state.resolved_distribution = (
            resolved
        )

    @staticmethod
    def workbook_ready(
        workbook_state,
    ):
        return all(
            state.account_selection
            is not None
            and
            state.resolved_distribution
            is not None
            for state
            in workbook_state
            .budgets
            .values()
        )


def workbook_state():
    return SimpleNamespace(
        budgets={
            "Sheet1":
                make_state(),
        }
    )


def test_review_exposes_all_official_choices():
    state = workbook_state()

    result = (
        OpexSmartImportPreparationService
        ._build_review_options(
            workbook_state=state,
            state_service=(
                FakeStateService()
            ),
        )
    )

    assert len(result) == 1

    review = result[0]

    assert (
        review.sheet_name
        == "Sheet1"
    )

    assert (
        len(
            review.account_options
        )
        == 2
    )

    assert (
        review.distribution_modes
        == (
            "IMPORTE",
            "PORCENTAJE",
        )
    )

    assert (
        len(
            review.cebe_choices
        )
        == 1
    )

    assert (
        len(
            review
            .cebe_choices[0]
            .options
        )
        == 2
    )


def test_override_can_change_account():
    state = workbook_state()

    override = (
        OpexSmartImportSheetOverride(
            sheet_name="Sheet1",
            account=(
                OpexSmartImportAccountChoice(
                    categoria_gasto=(
                        "Equipo informático"
                    ),
                    nombre_cuenta=(
                        "MANT. Y REPAR. "
                        "SOFTWARE VTAS"
                    ),
                    atributo_2=(
                        "GASTOS TI"
                    ),
                )
            ),
        )
    )

    (
        OpexSmartImportPreparationService
        ._apply_overrides(
            workbook_state=state,
            state_service=(
                FakeStateService()
            ),
            overrides=(
                override,
            ),
        )
    )

    assert (
        state
        .budgets["Sheet1"]
        .account_selection
        .nombre_cuenta
        ==
        "MANT. Y REPAR. SOFTWARE VTAS"
    )


def test_override_can_change_cebe():
    state = workbook_state()

    selected = (
        OpexSmartImportPreparationService
        ._cebe_option(
            "51IC000000",
            CEBE_B,
        )
    )

    override = (
        OpexSmartImportSheetOverride(
            sheet_name="Sheet1",
            cebe_selections=(
                selected,
            ),
        )
    )

    (
        OpexSmartImportPreparationService
        ._apply_overrides(
            workbook_state=state,
            state_service=(
                FakeStateService()
            ),
            overrides=(
                override,
            ),
        )
    )

    assert (
        state
        .budgets["Sheet1"]
        .cebe_selections[
            "51IC000000"
        ]
        is CEBE_B
    )


def test_override_can_change_distribution_mode():
    state = workbook_state()

    override = (
        OpexSmartImportSheetOverride(
            sheet_name="Sheet1",
            distribution_mode=(
                "PORCENTAJE"
            ),
        )
    )

    (
        OpexSmartImportPreparationService
        ._apply_overrides(
            workbook_state=state,
            state_service=(
                FakeStateService()
            ),
            overrides=(
                override,
            ),
        )
    )

    assert (
        state
        .budgets["Sheet1"]
        .resolved_distribution
        .mode
        == "PORCENTAJE"
    )

    assert (
        state
        .budgets["Sheet1"]
        .resolved_distribution
        .total
        == Decimal("100.00")
    )


def test_unknown_sheet_is_rejected():
    with pytest.raises(
        OpexSmartImportPreparationError,
        match="desconocidas",
    ):
        (
            OpexSmartImportPreparationService
            ._apply_overrides(
                workbook_state=(
                    workbook_state()
                ),
                state_service=(
                    FakeStateService()
                ),
                overrides=(
                    OpexSmartImportSheetOverride(
                        sheet_name=(
                            "NO_EXISTE"
                        )
                    ),
                ),
            )
        )


def test_foreign_cebe_selection_is_rejected():
    state = workbook_state()

    foreign = (
        OpexSmartImportCebeOption(
            centro_beneficio=(
                "51IC000000"
            ),
            desc_cebe="INVENTADO",
            macroservicio_cg="X",
            tipo_servicio_cg="X",
            region_cg="X",
            sede_cg="X",
            segmentacion="X",
        )
    )

    with pytest.raises(
        OpexSmartImportPreparationError,
        match="opcion oficial",
    ):
        (
            OpexSmartImportPreparationService
            ._apply_overrides(
                workbook_state=state,
                state_service=(
                    FakeStateService()
                ),
                overrides=(
                    OpexSmartImportSheetOverride(
                        sheet_name="Sheet1",
                        cebe_selections=(
                            foreign,
                        ),
                    ),
                ),
            )
        )
