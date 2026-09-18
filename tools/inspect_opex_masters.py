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


from app.services.opex_master_data_loader import (
    OpexMasterDataLoader,
)


def show_source(
    title,
    source,
):
    print()
    print("-" * 88)
    print(title)
    print("-" * 88)

    print(
        "Archivo          :",
        source.path,
    )

    print(
        "Hoja             :",
        source.sheet_name,
    )

    print(
        "Fila encabezados :",
        source.header_row,
    )

    print(
        "Filas fisicas    :",
        f"{source.physical_rows:,}",
    )

    print(
        "Claves unicas    :",
        f"{source.unique_rows:,}",
    )

    print(
        "Duplicados iguales:",
        f"{source.duplicate_rows:,}",
    )

    print(
        "Clave vacia ignorada:",
        f"{source.ignored_blank_key_rows:,}",
    )

    print(
        "Clave invalida ignorada:",
        f"{source.ignored_invalid_key_rows:,}",
    )

    print(
        "Claves conflictivas:",
        f"{source.conflict_keys:,}",
    )


def blank_count(
    records,
    field,
):
    return sum(
        1
        for record
        in records.values()
        if not getattr(
            record,
            field,
        )
    )


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--dir",
        required=True,
    )

    args = parser.parse_args()

    snapshot = (
        OpexMasterDataLoader(
            args.dir
        )
        .load()
    )

    print()
    print("=" * 88)
    print("MAESTROS OPEX")
    print("=" * 88)

    show_source(
        "CUENTA",
        snapshot.account_source,
    )

    show_source(
        "CEBE",
        snapshot.cebe_source,
    )

    show_source(
        "RECUPERABLES",
        snapshot.recoverable_source,
    )

    print()
    print("-" * 88)
    print("CONFLICTOS")
    print("-" * 88)

    conflict_groups = (
        (
            "CUENTA",
            snapshot.account_conflicts,
        ),
        (
            "CEBE",
            snapshot.cebe_conflicts,
        ),
        (
            "RECUPERABLES",
            snapshot.recoverable_conflicts,
        ),
    )

    for name, conflicts in conflict_groups:
        print(
            f"{name:<18}: "
            f"{len(conflicts):,}"
        )

        for key, conflict in conflicts.items():
            locations = ", ".join(
                conflict.locations
            )

            print(
                f"  - {key}: {locations}"
            )

    print()
    print("-" * 88)
    print("CAMPOS VACIOS DETECTADOS")
    print("-" * 88)

    checks = (
        (
            "CUENTA.Nombre Cuenta",
            snapshot.accounts,
            "nombre_cuenta",
        ),
        (
            "CUENTA.Categoria Gasto",
            snapshot.accounts,
            "categoria_gasto",
        ),
        (
            "CUENTA.Atributo 2",
            snapshot.accounts,
            "atributo_2",
        ),
        (
            "CEBE.Desc_CeBe",
            snapshot.cebes,
            "desc_cebe",
        ),
        (
            "CEBE.Macroservicio CG",
            snapshot.cebes,
            "macroservicio_cg",
        ),
        (
            "CEBE.Tipo Servicio CG",
            snapshot.cebes,
            "tipo_servicio_cg",
        ),
        (
            "CEBE.Region CG",
            snapshot.cebes,
            "region_cg",
        ),
        (
            "CEBE.Sede CG",
            snapshot.cebes,
            "sede_cg",
        ),
        (
            "CEBE.Seg Rs",
            snapshot.cebes,
            "segmentacion",
        ),
        (
            "RECUPERABLES.Sociedad",
            snapshot.recoverables,
            "sociedad",
        ),
        (
            "RECUPERABLES.Compania",
            snapshot.recoverables,
            "compania",
        ),
        (
            "RECUPERABLES.Pais",
            snapshot.recoverables,
            "pais",
        ),
    )

    for label, records, field in checks:
        print(
            f"{label:<32}: "
            f"{blank_count(records, field):,}"
        )

    print()
    print("-" * 88)
    print("PREFIJOS RECUPERABLES")
    print("-" * 88)

    prefixes = sorted(
        snapshot.recoverables,
        key=lambda value: (
            -len(value),
            value,
        ),
    )

    print(
        ", ".join(
            prefixes
        )
    )

    print()
    print("=" * 88)
    print("RESULTADO: MAESTROS CARGADOS")
    print("=" * 88)


if __name__ == "__main__":
    main()
