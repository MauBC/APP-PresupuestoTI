from app.config.budget_module_config import (
    BudgetModule,
    BudgetModuleCapabilities,
    BudgetModuleConfig,
)
from app.config.presupuesto_app_config import (
    DIMENSION_COLUMNS,
    GROUPABLE_COLUMNS,
    USD_MONTH_COLUMNS,
    USD_TOTAL_COLUMN,
)
from app.config.settings import settings


OPEX_MODULE_CONFIG = (
    BudgetModuleConfig(
        module=BudgetModule.OPEX,
        label="OPEX",
        main_table=(
            settings.BIGQUERY_TABLE
        ),
        dimension_columns=(
            DIMENSION_COLUMNS
        ),
        groupable_columns=(
            GROUPABLE_COLUMNS
        ),
        month_columns=(
            USD_MONTH_COLUMNS
        ),
        annual_column=(
            USD_TOTAL_COLUMN
        ),
        capabilities=(
            BudgetModuleCapabilities(
                monthly_distribution=True,
                ceco_distribution=True,
                country_distribution=True,
                grouped_editing=True,
            )
        ),
        country_column="pais",
        budgeter_column="presupuestador",
        ceco_column="ceco",
        change_detail_columns=(
            "presupuestador",
            "pais",
            "compania",
            "proveedor",
            "nombre_gasto",
            "ceco",
        ),
        configured=True,
    )
)


CAPEX_MODULE_CONFIG = (
    BudgetModuleConfig(
        module=BudgetModule.CAPEX,
        label="CAPEX",
        main_table=(
            settings.BIGQUERY_CAPEX_TABLE
        ),
        dimension_columns=(),
        groupable_columns=(),
        month_columns=(
            USD_MONTH_COLUMNS
        ),
        annual_column=(
            USD_TOTAL_COLUMN
        ),
        capabilities=(
            BudgetModuleCapabilities(
                monthly_distribution=True,
                ceco_distribution=False,
                country_distribution=False,
                grouped_editing=True,
            )
        ),
        country_column=None,
        budgeter_column=None,
        ceco_column=None,
        change_detail_columns=(),
        configured=False,
    )
)


MODULE_CONFIGS = {
    BudgetModule.OPEX:
        OPEX_MODULE_CONFIG,

    BudgetModule.CAPEX:
        CAPEX_MODULE_CONFIG,
}


def get_budget_module_config(
    module:
        BudgetModule | str,
) -> BudgetModuleConfig:
    try:
        normalized = BudgetModule(
            module
        )

    except ValueError as exc:
        raise ValueError(
            "Modulo presupuestal "
            f"no reconocido: {module}"
        ) from exc

    return MODULE_CONFIGS[
        normalized
    ]
