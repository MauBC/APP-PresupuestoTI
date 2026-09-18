import argparse
from pathlib import Path
import sys


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


from app.services.opex_smart_template_loader import (
    OpexSmartTemplateLoader,
)


def money(
    value,
):
    if value is None:
        return "-"

    return f"{value:,.2f}"


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Inspeccion read-only de una "
            "plantilla inteligente OPEX."
        )
    )

    parser.add_argument(
        "--file",
        required=True,
    )

    args = parser.parse_args()

    result = (
        OpexSmartTemplateLoader()
        .load(
            args.file
        )
    )

    print()
    print("=" * 90)
    print("OPEX SMART TEMPLATE")
    print("=" * 90)

    print(
        "Archivo             :",
        result.source_path,
    )

    print(
        "Presupuestos/hojas  :",
        result.budget_count,
    )

    print(
        "Filas OPEX futuras  :",
        result.generated_row_count,
    )

    for budget in result.budgets:
        print()
        print("-" * 90)

        print(
            "Hoja                :",
            budget.sheet_name,
        )

        print(
            "Gasto               :",
            budget.nombre_gasto,
        )

        print(
            "Proveedor           :",
            budget.proveedor,
        )

        print(
            "Moneda              :",
            budget.moneda_facturacion,
        )

        print(
            "Cuenta              :",
            budget.numero_cuenta,
        )

        print(
            "Tipo                :",
            budget.tipo,
        )

        print(
            "Monto               :",
            money(
                budget.monto
            ),
        )

        print(
            "CECOs               :",
            budget.ceco_count,
        )

        print(
            "Modo distribucion   :",
            budget.distribution_mode,
        )

        percentage = (
            budget.total_percentage
        )

        print(
            "Suma porcentaje     :",
            (
                f"{percentage * 100:.4f}%"
                if percentage is not None
                else "-"
            ),
        )

        print(
            "Suma importe        :",
            money(
                budget
                .total_distribution_amount
            ),
        )

        if (
            budget
            .total_distribution_amount
            is not None
        ):
            print(
                "Importe - MONTO     :",
                money(
                    budget
                    .total_distribution_amount
                    - budget.monto
                ),
            )

    print()
    print("=" * 90)

    print(
        "RESULTADO ESTRUCTURA : OK"
    )

    print(
        "NOTA                 : "
        "este inspector NO decide aun "
        "si PORCENTAJE o IMPORTE manda "
        "sobre MONTO."
    )

    print("=" * 90)


if __name__ == "__main__":
    main()
