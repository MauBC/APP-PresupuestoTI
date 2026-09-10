
from app.config.budget_module_config import (
    BudgetModule,
    BudgetModuleCapabilities,
    BudgetModuleConfig,
)
from app.config.capex_schema import (
    CAPEX_BUSINESS_COLUMNS,
    CAPEX_BUSINESS_TYPES,
    CAPEX_DIMENSION_COLUMNS,
    CAPEX_GROUPABLE_COLUMNS,
    CAPEX_USD_MONTH_COLUMNS,
    CAPEX_USD_TOTAL_COLUMN,
)
from app.config.presupuesto_app_config import (
    DIMENSION_COLUMNS,
    GROUPABLE_COLUMNS,
    USD_MONTH_COLUMNS,
    USD_TOTAL_COLUMN,
)
from app.config.presupuesto_schema import (
    AMOUNT_COLUMNS,
    LEGACY_EXPECTED_TYPES,
)
from app.config.settings import settings


def _column_types(
    columns,
    types,
):
    return tuple(
        (
            column,
            types[column],
        )
        for column
        in columns
    )


OPEX_INSERT_COLUMNS = (
    *DIMENSION_COLUMNS,
    *AMOUNT_COLUMNS,
)


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
        insert_column_types=(
            _column_types(
                OPEX_INSERT_COLUMNS,
                LEGACY_EXPECTED_TYPES,
            )
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
        dimension_columns=(
            CAPEX_DIMENSION_COLUMNS
        ),
        groupable_columns=(
            CAPEX_GROUPABLE_COLUMNS
        ),
        month_columns=(
            CAPEX_USD_MONTH_COLUMNS
        ),
        annual_column=(
            CAPEX_USD_TOTAL_COLUMN
        ),
        capabilities=(
            BudgetModuleCapabilities(
                monthly_distribution=True,
                ceco_distribution=False,
                country_distribution=False,
                grouped_editing=True,
                persistence=True,
            )
        ),
        country_column="pais",
        budgeter_column="responsable",
        ceco_column="codigo_ceco",
        change_detail_columns=(
            "responsable",
            "pais",
            "sociedad",
            "nombre_inversion",
            "tipo_capex",
            "codigo_cebe",
            "codigo_ceco",
        ),
        insert_column_types=(
            _column_types(
                CAPEX_BUSINESS_COLUMNS,
                CAPEX_BUSINESS_TYPES,
            )
        ),
        configured=True,
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
