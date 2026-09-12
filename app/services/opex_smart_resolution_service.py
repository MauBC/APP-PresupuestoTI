from app.models.opex_master_data import (
    OpexAccountMasterRecord,
    OpexCebeMasterRecord,
)
from app.models.opex_master_enrichment import (
    OpexMasterEnrichment,
)
from app.models.opex_smart_enrichment import (
    OpexSmartEnrichedRow,
)
from app.models.opex_smart_resolution import (
    OpexAccountChoiceGroup,
    OpexCebeSelectionRequirement,
)
from app.services.opex_master_enrichment_service import (
    OpexMasterEnrichmentError,
    OpexMasterEnrichmentService,
)
from app.services.opex_template_distribution_service import (
    OpexTemplateResolvedDistribution,
)


class OpexSmartResolutionError(
    ValueError
):
    def __init__(
        self,
        code,
        message,
        *,
        key=None,
    ):
        super().__init__(
            message
        )

        self.code = code
        self.key = key


class OpexSmartResolutionService:
    def __init__(
        self,
        master_service:
        OpexMasterEnrichmentService,
    ):
        self._master_service = (
            master_service
        )

    @staticmethod
    def _unique_records(
        records,
    ):
        result = []

        for record in records:
            if record not in result:
                result.append(
                    record
                )

        return tuple(
            result
        )

    @staticmethod
    def _required_text(
        value,
        *,
        code,
        field,
        key,
    ):
        if value is None:
            text = ""
        else:
            text = str(
                value
            ).strip()

        if not text:
            raise OpexSmartResolutionError(
                code,
                (
                    f"{field} esta vacio "
                    f"para {key}."
                ),
                key=key,
            )

        return text

    @staticmethod
    def _raise_master_error(
        exc,
    ):
        raise OpexSmartResolutionError(
            exc.code,
            str(exc),
            key=exc.key,
        ) from exc

    def _account_records(
        self,
        numero_cuenta,
    ):
        try:
            options = (
                self._master_service
                .account_options(
                    numero_cuenta
                )
            )
        except (
            OpexMasterEnrichmentError
        ) as exc:
            self._raise_master_error(
                exc
            )

        options = self._unique_records(
            options
        )

        if options:
            return options

        try:
            record = (
                self._master_service
                .resolve_account(
                    numero_cuenta
                )
            )
        except (
            OpexMasterEnrichmentError
        ) as exc:
            self._raise_master_error(
                exc
            )

        return (
            record,
        )

    def _cebe_records(
        self,
        centro_beneficio,
    ):
        try:
            options = (
                self._master_service
                .cebe_options(
                    centro_beneficio
                )
            )
        except (
            OpexMasterEnrichmentError
        ) as exc:
            self._raise_master_error(
                exc
            )

        options = self._unique_records(
            options
        )

        if options:
            return options

        try:
            record = (
                self._master_service
                .resolve_cebe(
                    centro_beneficio
                )
            )
        except (
            OpexMasterEnrichmentError
        ) as exc:
            self._raise_master_error(
                exc
            )

        return (
            record,
        )

    def account_choice_groups(
        self,
        numero_cuenta,
    ) -> tuple[
        OpexAccountChoiceGroup,
        ...,
    ]:
        records = self._account_records(
            numero_cuenta
        )

        grouped = {}

        for record in records:
            key = (
                str(
                    record.categoria_gasto
                    or ""
                ).strip(),
                str(
                    record.nombre_cuenta
                    or ""
                ).strip(),
            )

            atributo = str(
                record.atributo_2
                or ""
            ).strip()

            grouped.setdefault(
                key,
                set(),
            ).add(
                atributo
            )

        return tuple(
            OpexAccountChoiceGroup(
                categoria_gasto=(
                    categoria
                ),
                nombre_cuenta=nombre,
                atributos_2=tuple(
                    sorted(
                        atributos
                    )
                ),
            )
            for (
                categoria,
                nombre,
            ), atributos
            in sorted(
                grouped.items()
            )
        )

    def select_account(
        self,
        numero_cuenta,
        *,
        categoria_gasto,
        nombre_cuenta,
        atributo_2,
    ) -> OpexAccountMasterRecord:
        expected = (
            str(
                categoria_gasto
            ).strip(),
            str(
                nombre_cuenta
            ).strip(),
            str(
                atributo_2
            ).strip(),
        )

        matches = []

        for record in (
            self._account_records(
                numero_cuenta
            )
        ):
            candidate = (
                str(
                    record.categoria_gasto
                    or ""
                ).strip(),
                str(
                    record.nombre_cuenta
                    or ""
                ).strip(),
                str(
                    record.atributo_2
                    or ""
                ).strip(),
            )

            if candidate == expected:
                matches.append(
                    record
                )

        matches = self._unique_records(
            matches
        )

        if len(matches) != 1:
            raise OpexSmartResolutionError(
                "ACCOUNT_SELECTION_INVALID",
                (
                    "La seleccion de cuenta "
                    f"{numero_cuenta} no coincide "
                    "con una definicion oficial."
                ),
                key=str(
                    numero_cuenta
                ),
            )

        return matches[0]

    def cebe_requirements(
        self,
        budget,
    ) -> tuple[
        OpexCebeSelectionRequirement,
        ...,
    ]:
        grouped = {}

        for distribution in (
            budget.distributions
        ):
            try:
                ceco = (
                    self._master_service
                    .normalize_ceco(
                        distribution.ceco
                    )
                )

                centro_beneficio = (
                    self._master_service
                    .derive_cebe_from_ceco(
                        ceco
                    )
                )

                (
                    self._master_service
                    .resolve_cebe(
                        centro_beneficio
                    )
                )

            except (
                OpexMasterEnrichmentError
            ) as exc:
                if (
                    exc.code
                    != "CEBE_AMBIGUOUS"
                ):
                    continue

                current = (
                    grouped.setdefault(
                        centro_beneficio,
                        {
                            "cecos": [],
                            "rows": [],
                        },
                    )
                )

                current[
                    "cecos"
                ].append(
                    ceco
                )

                current[
                    "rows"
                ].append(
                    distribution.excel_row
                )

        requirements = []

        for centro_beneficio, data in (
            grouped.items()
        ):
            requirements.append(
                OpexCebeSelectionRequirement(
                    centro_beneficio=(
                        centro_beneficio
                    ),
                    cecos=tuple(
                        data["cecos"]
                    ),
                    excel_rows=tuple(
                        data["rows"]
                    ),
                    options=(
                        self._cebe_records(
                            centro_beneficio
                        )
                    ),
                )
            )

        return tuple(
            requirements
        )

    def _validate_account_selection(
        self,
        numero_cuenta,
        selection,
    ):
        official = (
            self._account_records(
                numero_cuenta
            )
        )

        if selection not in official:
            raise OpexSmartResolutionError(
                "ACCOUNT_SELECTION_INVALID",
                (
                    "La cuenta seleccionada "
                    "no pertenece a las "
                    "definiciones oficiales de "
                    f"{numero_cuenta}."
                ),
                key=str(
                    numero_cuenta
                ),
            )

    def _resolve_cebe_record(
        self,
        centro_beneficio,
        selections,
    ):
        try:
            return (
                self._master_service
                .resolve_cebe(
                    centro_beneficio
                )
            )

        except (
            OpexMasterEnrichmentError
        ) as exc:
            if (
                exc.code
                != "CEBE_AMBIGUOUS"
            ):
                self._raise_master_error(
                    exc
                )

        selection = selections.get(
            centro_beneficio
        )

        if selection is None:
            raise OpexSmartResolutionError(
                "CEBE_SELECTION_REQUIRED",
                (
                    "El CEBE "
                    f"{centro_beneficio} "
                    "requiere una seleccion "
                    "explicita."
                ),
                key=centro_beneficio,
            )

        official = (
            self._cebe_records(
                centro_beneficio
            )
        )

        if selection not in official:
            raise OpexSmartResolutionError(
                "CEBE_SELECTION_INVALID",
                (
                    "La seleccion del CEBE "
                    f"{centro_beneficio} "
                    "no pertenece a sus "
                    "definiciones oficiales."
                ),
                key=centro_beneficio,
            )

        return selection

    def _build_master_enrichment(
        self,
        *,
        account,
        ceco,
        centro_beneficio,
        gyp,
        prefix,
        recoverable,
        cebe,
    ):
        numero_cuenta = (
            self._required_text(
                account.numero_cuenta,
                code=(
                    "ACCOUNT_DATA_MISSING"
                ),
                field="Numero de cuenta",
                key=(
                    account.numero_cuenta
                ),
            )
        )

        return OpexMasterEnrichment(
            numero_cuenta=numero_cuenta,
            nombre_cuenta=(
                self._required_text(
                    account.nombre_cuenta,
                    code=(
                        "ACCOUNT_DATA_MISSING"
                    ),
                    field="Nombre Cuenta",
                    key=numero_cuenta,
                )
            ),
            categoria_gasto=(
                self._required_text(
                    account.categoria_gasto,
                    code=(
                        "ACCOUNT_DATA_MISSING"
                    ),
                    field=(
                        "Categoria de Gasto"
                    ),
                    key=numero_cuenta,
                )
            ),
            atributo_2=(
                self._required_text(
                    account.atributo_2,
                    code=(
                        "ACCOUNT_DATA_MISSING"
                    ),
                    field="Atributo 2",
                    key=numero_cuenta,
                )
            ),
            ceco_prefix=prefix,
            sociedad=(
                self._required_text(
                    recoverable.sociedad,
                    code=(
                        "RECOVERABLE_DATA_MISSING"
                    ),
                    field="Sociedad",
                    key=prefix,
                )
            ),
            compania=(
                self._required_text(
                    recoverable.compania,
                    code=(
                        "RECOVERABLE_DATA_MISSING"
                    ),
                    field=(
                        "Descripcion Sociedad"
                    ),
                    key=prefix,
                )
            ),
            pais=(
                self._required_text(
                    recoverable.pais,
                    code=(
                        "RECOVERABLE_DATA_MISSING"
                    ),
                    field="Pais",
                    key=prefix,
                )
            ),
            ceco=ceco,
            centro_beneficio=(
                centro_beneficio
            ),
            gyp=gyp,
            desc_cebe=(
                self._required_text(
                    cebe.desc_cebe,
                    code=(
                        "CEBE_DATA_MISSING"
                    ),
                    field="Desc_CeBe",
                    key=centro_beneficio,
                )
            ),
            macroservicio_cg=(
                self._required_text(
                    cebe.macroservicio_cg,
                    code=(
                        "CEBE_DATA_MISSING"
                    ),
                    field="Macroservicio CG",
                    key=centro_beneficio,
                )
            ),
            tipo_servicio_cg=(
                self._required_text(
                    cebe.tipo_servicio_cg,
                    code=(
                        "CEBE_DATA_MISSING"
                    ),
                    field="Tipo Servicio CG",
                    key=centro_beneficio,
                )
            ),
            region_cg=(
                self._required_text(
                    cebe.region_cg,
                    code=(
                        "CEBE_DATA_MISSING"
                    ),
                    field="Region CG",
                    key=centro_beneficio,
                )
            ),
            sede_cg=(
                self._required_text(
                    cebe.sede_cg,
                    code=(
                        "CEBE_DATA_MISSING"
                    ),
                    field="Sede CG",
                    key=centro_beneficio,
                )
            ),
            segmentacion=(
                self._required_text(
                    cebe.segmentacion,
                    code=(
                        "CEBE_DATA_MISSING"
                    ),
                    field="Seg Rs",
                    key=centro_beneficio,
                )
            ),
        )

    def build_rows(
        self,
        *,
        budget,
        resolved:
        OpexTemplateResolvedDistribution,
        account_selection:
        OpexAccountMasterRecord,
        cebe_selections=None,
    ) -> tuple[
        OpexSmartEnrichedRow,
        ...,
    ]:
        self._validate_account_selection(
            budget.numero_cuenta,
            account_selection,
        )

        cebe_selections = (
            cebe_selections
            or {}
        )

        if (
            len(
                resolved.amounts
            )
            != len(
                budget.distributions
            )
        ):
            raise OpexSmartResolutionError(
                "DISTRIBUTION_MISMATCH",
                (
                    "La distribucion resuelta "
                    "no tiene la misma cantidad "
                    "de filas que la plantilla."
                ),
            )

        rows = []

        for (
            distribution,
            resolved_item,
        ) in zip(
            budget.distributions,
            resolved.amounts,
        ):
            (
                resolved_ceco,
                amount,
            ) = resolved_item

            try:
                ceco = (
                    self._master_service
                    .normalize_ceco(
                        distribution.ceco
                    )
                )

                normalized_resolved = (
                    self._master_service
                    .normalize_ceco(
                        resolved_ceco
                    )
                )

                if (
                    ceco
                    != normalized_resolved
                ):
                    raise (
                        OpexSmartResolutionError(
                            "DISTRIBUTION_MISMATCH",
                            (
                                "El orden de CECO "
                                "de la distribucion "
                                "resuelta no coincide "
                                "con la plantilla. "
                                f"Esperado={ceco}; "
                                "recibido="
                                f"{normalized_resolved}."
                            ),
                            key=ceco,
                        )
                    )

                gyp = (
                    self._master_service
                    .derive_gyp_from_ceco(
                        ceco
                    )
                )

                centro_beneficio = (
                    self._master_service
                    .derive_cebe_from_ceco(
                        ceco
                    )
                )

                (
                    prefix,
                    recoverable,
                ) = (
                    self._master_service
                    .resolve_recoverable(
                        ceco
                    )
                )

            except (
                OpexMasterEnrichmentError
            ) as exc:
                self._raise_master_error(
                    exc
                )

            cebe = (
                self._resolve_cebe_record(
                    centro_beneficio,
                    cebe_selections,
                )
            )

            enrichment = (
                self._build_master_enrichment(
                    account=(
                        account_selection
                    ),
                    ceco=ceco,
                    centro_beneficio=(
                        centro_beneficio
                    ),
                    gyp=gyp,
                    prefix=prefix,
                    recoverable=recoverable,
                    cebe=cebe,
                )
            )

            rows.append(
                OpexSmartEnrichedRow(
                    sheet_name=(
                        budget.sheet_name
                    ),
                    excel_row=(
                        distribution.excel_row
                    ),
                    nombre_gasto=(
                        budget.nombre_gasto
                    ),
                    proveedor=(
                        budget.proveedor
                    ),
                    moneda_facturacion=(
                        budget
                        .moneda_facturacion
                    ),
                    numero_cuenta=(
                        budget.numero_cuenta
                    ),
                    tipo=budget.tipo,
                    monto_presupuesto=(
                        budget.monto
                    ),
                    ceco=ceco,
                    monto_ceco=amount,
                    enrichment=enrichment,
                )
            )

        return tuple(
            rows
        )
