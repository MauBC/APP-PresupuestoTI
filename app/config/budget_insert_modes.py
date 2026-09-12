from dataclasses import dataclass
from enum import Enum

from app.config.budget_module_config import (
    BudgetModule,
    BudgetModuleConfig,
)


class BudgetInsertMode(
    str,
    Enum,
):
    MANUAL = "MANUAL"
    INTELLIGENT = "INTELLIGENT"
    TEMPLATE = "TEMPLATE"


@dataclass(
    frozen=True,
    slots=True,
)
class BudgetInsertOption:
    mode: BudgetInsertMode
    title: str
    description: str
    enabled: bool = True


def get_budget_insert_options(
    module_config: BudgetModuleConfig,
) -> tuple[BudgetInsertOption, ...]:
    manual = BudgetInsertOption(
        mode=BudgetInsertMode.MANUAL,
        title="Manual",
        description=(
            "Crear un presupuesto directamente "
            "desde la aplicacion."
        ),
    )

    template = BudgetInsertOption(
        mode=BudgetInsertMode.TEMPLATE,
        title="Por plantilla",
        description=(
            "Importar la plantilla completa "
            "del modulo con sus columnas "
            "de negocio e importes."
        ),
    )

    if (
        module_config.module
        == BudgetModule.OPEX
    ):
        intelligent = BudgetInsertOption(
            mode=(
                BudgetInsertMode
                .INTELLIGENT
            ),
            title="Inteligente",
            description=(
                "Importar el formato OPEX "
                "simplificado por gasto, "
                "CECO y distribucion."
            ),
            enabled=True,
        )

        return (
            manual,
            intelligent,
            template,
        )

    if (
        module_config.module
        == BudgetModule.CAPEX
    ):
        return (
            manual,
            template,
        )

    raise ValueError(
        "Modulo presupuestal no soportado "
        "para insercion."
    )
