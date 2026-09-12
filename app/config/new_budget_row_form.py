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

    required_columns: tuple[
        str,
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


OPEX_NEW_ROW_FORM = (
    NewBudgetRowFormDefinition(
        sections=(
            NewBudgetRowSection(
                title="Datos generales",
                columns=(
                    "origen",
                    "periodo",
                    "presupuestador",
                    "pais",
                    "compania",
                    "moneda_facturacion",
                ),
            ),
            NewBudgetRowSection(
                title="Imputacion contable",
                columns=(
                    "ceco",
                    "centro_beneficio",
                    "numero_cuenta",
                    "nombre_cuenta",
                    "gyp",
                ),
            ),
            NewBudgetRowSection(
                title="Centro de gestion",
                columns=(
                    "desc_cebe",
                    "macroservicio_cg",
                    "tipo_servicio_cg",
                    "sede_cg",
                    "region_cg",
                ),
            ),
            NewBudgetRowSection(
                title="Gasto y clasificacion",
                columns=(
                    "nombre_gasto",
                    "proveedor",
                    "categoria_gasto",
                    "atributo_2",
                    "segmentacion",
                ),
            ),
        ),
        required_columns=(
            "presupuestador",
            "pais",
            "compania",
            "ceco",
            "nombre_gasto",
            "moneda_facturacion",
            "periodo",
        ),
    )
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
        required_columns=(
            "nombre_inversion",
            "vicepresidencia",
            "pais",
            "responsable",
            "gerente_aprobador",
            "anio",
            "cantidad",
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

    required = tuple(
        definition.required_columns
    )

    if len(required) != len(
        set(required)
    ):
        raise ValueError(
            "La configuracion del formulario "
            "contiene campos obligatorios "
            "duplicados."
        )

    invalid_required = (
        set(required)
        - set(expected)
    )

    if invalid_required:
        raise ValueError(
            "Campos obligatorios no validos "
            f"para {module_config.label}: "
            + ", ".join(
                sorted(
                    invalid_required
                )
            )
        )


def get_missing_required_new_row_columns(
    definition,
    values,
) -> tuple[str, ...]:
    supplied = dict(
        values or {}
    )

    missing = []

    for column in (
        definition.required_columns
    ):
        value = supplied.get(
            column
        )

        if value is None:
            missing.append(
                column
            )
            continue

        if (
            isinstance(
                value,
                str,
            )
            and not value.strip()
        ):
            missing.append(
                column
            )

    return tuple(
        missing
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

    elif (
        module_config.module
        == BudgetModule.OPEX
    ):
        definition = (
            OPEX_NEW_ROW_FORM
        )

    else:
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
