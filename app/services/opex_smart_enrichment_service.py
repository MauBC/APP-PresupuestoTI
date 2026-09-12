from app.models.opex_smart_enrichment import (
    OpexSmartBudgetAnalysis,
    OpexSmartEnrichedRow,
    OpexSmartEnrichmentDraft,
    OpexSmartEnrichmentIssue,
    OpexSmartWorkbookAnalysis,
)
from app.services.opex_master_enrichment_service import (
    OpexMasterEnrichmentError,
    OpexMasterEnrichmentService,
)
from app.services.opex_template_distribution_service import (
    OpexTemplateDistributionService,
    OpexTemplateResolvedDistribution,
)


class OpexSmartEnrichmentBuildError(
    ValueError
):
    pass


class OpexSmartEnrichmentService:
    def __init__(
        self,
        master_service:
        OpexMasterEnrichmentService,
        distribution_service=None,
    ):
        self._master_service = (
            master_service
        )

        self._distribution_service = (
            distribution_service
            or OpexTemplateDistributionService()
        )

    def analyze_budget(
        self,
        budget,
    ) -> OpexSmartBudgetAnalysis:
        status = (
            self._distribution_service
            .inspect(
                budget
            )
        )

        drafts = []
        issues = []

        for distribution in (
            budget.distributions
        ):
            try:
                enrichment = (
                    self._master_service
                    .enrich(
                        numero_cuenta=(
                            budget.numero_cuenta
                        ),
                        ceco=(
                            distribution.ceco
                        ),
                    )
                )
            except (
                OpexMasterEnrichmentError
            ) as exc:
                issues.append(
                    OpexSmartEnrichmentIssue(
                        sheet_name=(
                            budget.sheet_name
                        ),
                        excel_row=(
                            distribution
                            .excel_row
                        ),
                        ceco=(
                            distribution.ceco
                        ),
                        code=exc.code,
                        message=str(exc),
                    )
                )

                continue

            drafts.append(
                OpexSmartEnrichmentDraft(
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
                    ceco=(
                        distribution.ceco
                    ),
                    percentage=(
                        distribution.percentage
                    ),
                    input_amount=(
                        distribution.amount
                    ),
                    enrichment=enrichment,
                )
            )

        return OpexSmartBudgetAnalysis(
            sheet_name=(
                budget.sheet_name
            ),
            distribution_status=status,
            drafts=tuple(
                drafts
            ),
            issues=tuple(
                issues
            ),
        )

    def analyze_workbook(
        self,
        workbook,
    ) -> OpexSmartWorkbookAnalysis:
        return OpexSmartWorkbookAnalysis(
            source_path=(
                workbook.source_path
            ),
            budgets=tuple(
                self.analyze_budget(
                    budget
                )
                for budget
                in workbook.budgets
            ),
        )

    def build_rows(
        self,
        *,
        budget,
        resolved:
        OpexTemplateResolvedDistribution,
    ) -> tuple[
        OpexSmartEnrichedRow,
        ...,
    ]:
        distributions = {
            item.ceco: item
            for item
            in budget.distributions
        }

        resolved_amounts = dict(
            resolved.amounts
        )

        expected_cecos = set(
            distributions
        )

        resolved_cecos = set(
            resolved_amounts
        )

        if (
            expected_cecos
            != resolved_cecos
        ):
            missing = sorted(
                expected_cecos
                - resolved_cecos
            )

            extra = sorted(
                resolved_cecos
                - expected_cecos
            )

            raise (
                OpexSmartEnrichmentBuildError(
                    "La distribucion resuelta "
                    "no coincide con los CECO "
                    "de la plantilla. "
                    f"Faltantes={missing}; "
                    f"extras={extra}."
                )
            )

        rows = []

        for distribution in (
            budget.distributions
        ):
            try:
                enrichment = (
                    self._master_service
                    .enrich(
                        numero_cuenta=(
                            budget.numero_cuenta
                        ),
                        ceco=(
                            distribution.ceco
                        ),
                    )
                )
            except (
                OpexMasterEnrichmentError
            ) as exc:
                raise (
                    OpexSmartEnrichmentBuildError(
                        "No se puede construir "
                        "la fila "
                        f"{budget.sheet_name}, "
                        "Excel "
                        f"{distribution.excel_row}, "
                        "CECO "
                        f"{distribution.ceco}: "
                        f"{exc}"
                    )
                ) from exc

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
                    ceco=(
                        distribution.ceco
                    ),
                    monto_ceco=(
                        resolved_amounts[
                            distribution.ceco
                        ]
                    ),
                    enrichment=enrichment,
                )
            )

        return tuple(
            rows
        )
