
import sys
from pathlib import Path


ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)

if str(ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(ROOT),
    )


import argparse
from decimal import Decimal
from time import perf_counter

from app.config.budget_modules import (
    get_budget_module_config,
)
from app.config.budget_summary_config import (
    get_budget_summary_definition,
)
from app.repositories.budget_summary_repository import (
    BudgetSummaryRepository,
)
from app.services.bigquery_service import (
    BigQueryService,
)
from app.services.budget_summary_service import (
    BudgetSummaryService,
)


def display_value(
    value,
):
    if value is None:
        return "(NULL)"

    return str(
        value
    )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Genera y verifica un resumen "
            "Power Apps directamente desde "
            "BigQuery. Solo lectura."
        )
    )

    parser.add_argument(
        "--module",
        choices=(
            "OPEX",
            "CAPEX",
        ),
        default="CAPEX",
    )

    parser.add_argument(
        "--summary",
        default="capex_powerapps",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=20,
    )

    args = parser.parse_args()

    if args.limit < 0:
        raise ValueError(
            "--limit no puede "
            "ser negativo."
        )

    config = (
        get_budget_module_config(
            args.module
        )
    )

    definition = (
        get_budget_summary_definition(
            config.module,
            args.summary,
        )
    )

    bigquery = (
        BigQueryService()
    )

    repository = (
        BudgetSummaryRepository(
            bigquery,
            module_config=config,
        )
    )

    service = (
        BudgetSummaryService(
            repository
        )
    )

    started = (
        perf_counter()
    )

    result = service.build(
        definition
    )

    elapsed = (
        perf_counter()
        - started
    )

    if result.source_row_count:
        reduction = (
            Decimal(
                result.source_row_count
                - result.grouped_row_count
            )
            /
            Decimal(
                result.source_row_count
            )
            *
            Decimal("100")
        )

    else:
        reduction = Decimal("0")

    print()
    print("=" * 90)
    print(
        "POWER APPS SUMMARY PREVIEW"
    )
    print("=" * 90)

    print(
        "Modulo             :",
        config.label,
    )

    print(
        "Resumen            :",
        definition.name,
    )

    print(
        "Tabla origen       :",
        config.main_table,
    )

    print(
        "Agrupacion         :",
        ", ".join(
            definition.group_by
        ),
    )

    print(
        "Columna importe    :",
        definition.amount_column,
    )

    print(
        "Filas origen       :",
        f"{result.source_row_count:,}",
    )

    print(
        "Filas resumen      :",
        f"{result.grouped_row_count:,}",
    )

    print(
        "Reduccion          :",
        f"{reduction:.2f}%",
    )

    print(
        "Total origen USD   :",
        f"{result.source_total_usd:,.2f}",
    )

    print(
        "Total resumen USD  :",
        f"{result.summary_total_usd:,.2f}",
    )

    print(
        "Diferencia USD     :",
        f"{result.difference_usd:,.2f}",
    )

    print(
        "Registros balance  :",
        (
            "OK"
            if result.rows_balanced
            else "ERROR"
        ),
    )

    print(
        "Importes balance   :",
        (
            "OK"
            if result.amounts_balanced
            else "ERROR"
        ),
    )

    print(
        "Tiempo             :",
        f"{elapsed:.3f} s",
    )

    print(
        "RESULTADO          :",
        (
            "OK"
            if result.is_balanced
            else "ERROR"
        ),
    )

    print(
        "MODO               : READ-ONLY"
    )

    if (
        args.limit > 0
        and result.rows
    ):
        print()
        print(
            "PRIMEROS GRUPOS"
        )

        print("-" * 90)

        for row in (
            result.rows[
                :args.limit
            ]
        ):
            values = (
                row.dimension_dict()
            )

            print()

            for column in (
                definition.group_by
            ):
                print(
                    f"{column:<22}: "
                    f"{display_value(values.get(column))}"
                )

            print(
                f"{'registros_origen':<22}: "
                f"{row.registros_origen:,}"
            )

            print(
                f"{'total_usd':<22}: "
                f"{row.total_usd:,.2f}"
            )

            print(
                f"{'summary_key':<22}: "
                f"{row.summary_key[:16]}..."
            )

    print()
    print("=" * 90)


if __name__ == "__main__":
    main()
