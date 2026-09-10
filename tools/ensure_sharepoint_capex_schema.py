
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

from app.clients.sharepoint_client import (
    SharePointClient,
)
from app.config.settings import (
    settings,
)
from app.config.sharepoint_summary_config import (
    CAPEX_SHAREPOINT_COLUMN_SPECS,
)
from app.services.sharepoint_schema_service import (
    SharePointSchemaService,
)


def print_plan(
    plan,
):
    print(
        "Presentes          :",
        len(
            plan.present
        ),
    )

    print(
        "Faltantes          :",
        len(
            plan.missing
        ),
    )

    print(
        "Incompatibles      :",
        len(
            plan.incompatible
        ),
    )

    if plan.present:
        print()
        print(
            "COLUMNAS PRESENTES"
        )
        print("-" * 90)

        for name in plan.present:
            print(
                "[OK]     ",
                name,
            )

    if plan.missing:
        print()
        print(
            "COLUMNAS A CREAR"
        )
        print("-" * 90)

        for spec in plan.missing:
            flags = []

            if spec.indexed:
                flags.append(
                    "INDEX"
                )

            if spec.enforce_unique:
                flags.append(
                    "UNIQUE"
                )

            suffix = (
                " | "
                + ", ".join(
                    flags
                )
                if flags
                else ""
            )

            print(
                f"[CREATE] {spec.name:<22}"
                f" | {spec.kind:<8}"
                f"{suffix}"
            )

    if plan.incompatible:
        print()
        print(
            "INCOMPATIBLES"
        )
        print("-" * 90)

        for item in (
            plan.incompatible
        ):
            print(
                "[ERROR]  ",
                item,
            )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Verifica o crea el esquema "
            "de Resumen_Capex."
        )
    )

    parser.add_argument(
        "--apply",
        action="store_true",
        help=(
            "Crea las columnas faltantes. "
            "Sin este flag solo inspecciona."
        ),
    )

    args = parser.parse_args()

    list_name = (
        settings
        .SHAREPOINT_CAPEX_LIST_NAME
    )

    client = (
        SharePointClient()
    )

    service = (
        SharePointSchemaService(
            client
        )
    )

    print()
    print("=" * 90)
    print(
        "SHAREPOINT CAPEX SCHEMA"
    )
    print("=" * 90)

    print(
        "Lista              :",
        list_name,
    )

    print(
        "Modo               :",
        (
            "APPLY"
            if args.apply
            else "DRY-RUN"
        ),
    )

    print()

    before = service.plan(
        list_name=list_name,
        specs=(
            CAPEX_SHAREPOINT_COLUMN_SPECS
        ),
    )

    print_plan(
        before
    )

    if not before.is_compatible:
        print()
        print(
            "RESULTADO          : BLOQUEADO"
        )
        print(
            "ESCRITURAS         : 0"
        )
        print("=" * 90)

        raise SystemExit(
            2
        )

    if not args.apply:
        print()
        print(
            "RESULTADO          : "
            "DRY-RUN OK"
        )

        print(
            "ESCRITURAS         : 0"
        )

        print("=" * 90)

        return

    if not before.missing:
        print()
        print(
            "RESULTADO          : "
            "ESQUEMA YA COMPLETO"
        )
        print(
            "ESCRITURAS         : 0"
        )
        print("=" * 90)

        return

    created_count = len(
        before.missing
    )

    after = service.ensure(
        list_name=list_name,
        specs=(
            CAPEX_SHAREPOINT_COLUMN_SPECS
        ),
    )

    print()
    print(
        "VERIFICACION FINAL"
    )
    print("-" * 90)

    print_plan(
        after
    )

    print()
    print(
        "RESULTADO          :",
        (
            "OK"
            if after.is_complete
            else "ERROR"
        ),
    )

    print(
        "COLUMNAS CREADAS   :",
        created_count,
    )

    print("=" * 90)


if __name__ == "__main__":
    main()
