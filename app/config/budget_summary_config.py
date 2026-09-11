
from app.config.budget_module_config import (
    BudgetModule,
)
from app.config.capex_schema import (
    CAPEX_USD_TOTAL_COLUMN,
)
from app.models.budget_summary import (
    BudgetSummaryDefinition,
)


CAPEX_POWERAPPS_SUMMARY = (
    BudgetSummaryDefinition(
        name="capex_powerapps",
        module=(
            BudgetModule
            .CAPEX
            .value
        ),
        group_by=(
            "vicepresidencia",
            "pais",
            "responsable",
            "gerente_aprobador",
            "nombre_inversion",
        ),
        amount_column=(
            CAPEX_USD_TOTAL_COLUMN
        ),
    )
)


SUMMARY_DEFINITIONS = {
    (
        BudgetModule
        .CAPEX
        .value
    ): {
        CAPEX_POWERAPPS_SUMMARY
        .name:
            CAPEX_POWERAPPS_SUMMARY,
    },
}


def get_budget_summary_definition(
    module,
    name: str,
) -> BudgetSummaryDefinition:
    module_value = str(
        getattr(
            module,
            "value",
            module,
        )
    ).strip().upper()

    name_value = str(
        name
    ).strip()

    try:
        module_definitions = (
            SUMMARY_DEFINITIONS[
                module_value
            ]
        )

    except KeyError as exc:
        raise ValueError(
            "No existen resumenes "
            "configurados para el modulo "
            f"{module_value}."
        ) from exc

    try:
        return module_definitions[
            name_value
        ]

    except KeyError as exc:
        raise ValueError(
            "Resumen no configurado: "
            f"{name_value}"
        ) from exc
