
import argparse

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(ROOT),
    )


from app.config.budget_modules import (
    get_budget_module_config,
)
from app.services.budget_excel_import_service import (
    BudgetExcelImportService,
)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Valida un Excel para alta "
            "masiva sin modificar BigQuery."
        )
    )

    parser.add_argument(
        "--module",
        required=True,
        choices=(
            "OPEX",
            "CAPEX",
        ),
    )

    parser.add_argument(
        "--file",
        required=True,
    )

    parser.add_argument(
        "--actor",
        default="excel-preview",
    )

    parser.add_argument(
        "--sheet",
        default=None,
    )

    parser.add_argument(
        "--simulation",
        action="store_true",
    )

    args = parser.parse_args()

    config = (
        get_budget_module_config(
            args.module
        )
    )

    sheet = args.sheet

    if (
        args.module == "OPEX"
        and sheet is not None
        and str(sheet).isdigit()
    ):
        sheet = int(
            sheet
        )

    expected_year = (
        None
        if args.simulation
        else 2027
    )

    result = (
        BudgetExcelImportService(
            config
        )
        .prepare(
            args.file,
            actor=args.actor,
            sheet_name=sheet,
            expected_year=(
                expected_year
            ),
        )
    )

    print()
    print("=" * 80)
    print("EXCEL IMPORT PREVIEW")
    print("=" * 80)
    print(
        "Modulo        :",
        result.module,
    )
    print(
        "Archivo       :",
        result.source_path,
    )
    print(
        "Hoja          :",
        result.sheet_name,
    )
    print(
        "Filas leidas  :",
        f"{result.rows_read:,}",
    )
    print(
        "Importables   :",
        f"{result.importable_count:,}",
    )
    print(
        "Errores       :",
        f"{result.error_count:,}",
    )
    print(
        "Advertencias  :",
        f"{result.warning_count:,}",
    )
    print(
        "Informativos  :",
        f"{result.info_count:,}",
    )
    print(
        "Resultado     :",
        (
            "VALIDO"
            if result.is_valid
            else "BLOQUEADO"
        ),
    )

    if result.issues:
        print()
        print("PRIMEROS ISSUES")
        print("-" * 80)

        for issue in (
            result.issues[:25]
        ):
            print(
                f"Fila {issue.row_number} | "
                f"{issue.severity.value} | "
                f"{issue.code} | "
                f"{issue.column} | "
                f"{issue.message}"
            )

    print("=" * 80)

    if not result.is_valid:
        raise SystemExit(
            2
        )


if __name__ == "__main__":
    main()
