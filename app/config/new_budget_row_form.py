from dataclasses import (
    dataclass,
)
from typing import Any

from app.config.budget_module_config import (
    BudgetModule,
)


@dataclass(
    frozen=True,
    slots=True,
)
class NewBudgetRowSection:
    title: str
    columns: tuple[
        str,
        ...
    ]


@dataclass(
    frozen=True,
    slots=True,
)
class NewBudgetRowFormDefinition:
    sections: tuple[
        NewBudgetRowSection,
        ...
    ]

    defaults: tuple[
        tuple[
            str,
            Any,
        ],
        ...
    ] = ()

    @property
    def columns(
        self,
    ) -> tuple[
        str,
        ...
    ]:
        return tuple(
            column
            for section in self.sections
            for column in section.columns
        )

    @property
    def default_map(
        self,
    ) -> dict[
        str,
        Any,
    ]:
        return dict(
            self.defaults
        )


CAPEX_NEW_ROW_FORM = (
    NewBudgetRowFormDefinition(
        sections=(
            NewBudgetRowSection(
                title="Datos generales",
                columns=(
                    "tipo",
                    "anio",
                    "cantidad",
                    "nombre_inversion",
                    "descripcion_inversion",
                    "pais",
                    "sociedad",
                    "moneda_facturacion",
                ),
            ),
            NewBudgetRowSection(
                title="Aprobaci\u00f3n",
                columns=(
                    "vicepresidencia",
                    "responsable",
                    "presupuestador",
                    "gerente_aprobador",
                    "vp_aprobador",
                ),
            ),
            NewBudgetRowSection(
                title="Clasificaci\u00f3n",
                columns=(
                    "tipo_activo",
                    "tipo_capex",
                    "clasificacion_inversion",
                    "filtro_ti",
                ),
            ),
            NewBudgetRowSection(
                title="Imputaci\u00f3n",
                columns=(
                    "codigo_cebe",
                    "gyp",
                    "codigo_ceco",
                    "desc_cebe",
                    "sede_cg",
                    "u_productiva_cg",
                    "seg_rs",
                ),
            ),
            NewBudgetRowSection(
                title="Observaci\u00f3n",
                columns=(
                    "observacion_comentario",
                ),
            ),
        ),
        defaults=(
            (
                "anio",
                2027,
            ),
            (
                "cantidad",
                1,
            ),
        ),
    )
)


def _generic_definition(
    module_config,
):
    return NewBudgetRowFormDefinition(
        sections=(
            NewBudgetRowSection(
                title="Datos de la nueva fila",
                columns=tuple(
                    module_config
                    .dimension_columns
                ),
            ),
        ),
    )


def _validate_definition(
    definition,
    module_config,
):
    expected = tuple(
        module_config
        .dimension_columns
    )

    actual = (
        definition.columns
    )

    if len(actual) != len(
        set(actual)
    ):
        raise ValueError(
            "La configuracion del formulario "
            "contiene columnas duplicadas."
        )

    if set(actual) != set(
        expected
    ):
        missing = sorted(
            set(expected)
            - set(actual)
        )

        extra = sorted(
            set(actual)
            - set(expected)
        )

        details = []

        if missing:
            details.append(
                "faltantes="
                + ", ".join(
                    missing
                )
            )

        if extra:
            details.append(
                "extras="
                + ", ".join(
                    extra
                )
            )

        raise ValueError(
            "La configuracion del formulario "
            "no coincide con las dimensiones "
            f"de {module_config.label}: "
            + " | ".join(
                details
            )
        )

    invalid_defaults = (
        set(
            definition.default_map
        )
        - set(expected)
    )

    if invalid_defaults:
        raise ValueError(
            "Defaults no validos para "
            f"{module_config.label}: "
            + ", ".join(
                sorted(
                    invalid_defaults
                )
            )
        )


def get_new_budget_row_form(
    module_config,
) -> NewBudgetRowFormDefinition:
    if (
        module_config.module
        == BudgetModule.CAPEX
    ):
        definition = (
            CAPEX_NEW_ROW_FORM
        )

    else:
        #
        # OPEX sigue usando el mismo motor.
        # Su layout especifico se agregara
        # en el siguiente bloque dedicado.
        #
        definition = (
            _generic_definition(
                module_config
            )
        )

    _validate_definition(
        definition,
        module_config,
    )

    return definition
