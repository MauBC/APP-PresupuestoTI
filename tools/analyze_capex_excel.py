import argparse
from pathlib import Path
import sys


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


from app.services.capex_excel_loader import (
    build_capex_quality_report,
    load_capex_workbook,
)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Analiza calidad de una "
            "plantilla CAPEX."
        )
    )

    parser.add_argument(
        "--file",
        required=True,
        help="Excel CAPEX a analizar.",
    )

    parser.add_argument(
        "--expected-year",
        type=int,
        default=None,
        help=(
            "Anio esperado. "
            "Omitir para datos de ejemplo."
        ),
    )

    parser.add_argument(
        "--output",
        default=(
            "M6_CAPEX_CALIDAD.txt"
        ),
    )

    args = parser.parse_args()

    result = (
        load_capex_workbook(
            args.file,
            expected_year=(
                args.expected_year
            ),
        )
    )

    report = (
        build_capex_quality_report(
            result
        )
    )

    output = Path(
        args.output
    )

    output.write_text(
        report,
        encoding="utf-8",
    )

    print()
    print("=" * 80)
    print("M6 CAPEX - ANALISIS TERMINADO")
    print("=" * 80)
    print(
        "Filas leidas      :",
        result.rows_read,
    )
    print(
        "Filas validas     :",
        result.valid_count,
    )
    print(
        "Filas con error   :",
        result.invalid_count,
    )
    print(
        "Errores           :",
        result.error_count,
    )
    print(
        "Advertencias      :",
        result.warning_count,
    )
    print(
        "Informativos      :",
        result.info_count,
    )
    print()
    print(
        "Reporte:",
        output.resolve(),
    )


if __name__ == "__main__":
    main()
