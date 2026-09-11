
import sys
from pathlib import Path
from time import perf_counter


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

from app.services.capex_sharepoint_sync_service import (
    CapexSharePointSyncService,
)


def print_plan(
    preparation,
):
    summary = (
        preparation
        .summary_result
    )

    plan = (
        preparation.plan
    )

    print(
        "Detalle BigQuery      :",
        f"{summary.source_row_count:,}",
    )

    print(
        "Resumen BigQuery      :",
        f"{summary.grouped_row_count:,}",
    )

    print(
        "SharePoint actual     :",
        f"{plan.current_item_count:,}",
    )

    print()
    print(
        "PLAN"
    )
    print("-" * 90)

    print(
        "CREATE                :",
        f"{plan.create_count:,}",
    )

    print(
        "UPDATE                :",
        f"{plan.update_count:,}",
    )

    print(
        "UNCHANGED             :",
        f"{plan.unchanged_count:,}",
    )

    print(
        "DELETE                :",
        f"{plan.delete_count:,}",
    )

    print(
        "UNMANAGED             :",
        f"{plan.unmanaged_count:,}",
    )

    print(
        "ESCRITURAS PLAN       :",
        f"{plan.write_count:,}",
    )

    print()
    print(
        "CONTROL FINANCIERO"
    )
    print("-" * 90)

    print(
        "Total origen USD      :",
        f"{summary.source_total_usd:,.2f}",
    )

    print(
        "Total resumen USD     :",
        f"{summary.summary_total_usd:,.2f}",
    )

    print(
        "Diferencia USD        :",
        f"{summary.difference_usd:,.2f}",
    )

    print(
        "Balance               :",
        (
            "OK"
            if summary.is_balanced
            else "ERROR"
        ),
    )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Sincroniza el resumen CAPEX "
            "BigQuery hacia SharePoint."
        )
    )

    parser.add_argument(
        "--apply",
        action="store_true",
        help=(
            "Ejecuta las escrituras "
            "SharePoint."
        ),
    )

    parser.add_argument(
        "--confirm",
        default="",
        help=(
            "Para --apply debe coincidir "
            "con el nombre de la lista."
        ),
    )

    parser.add_argument(
        "--source-batch-id",
        default=None,
    )

    parser.add_argument(
        "--allow-large-delete",
        action="store_true",
        help=(
            "Permite eliminaciones masivas. "
            "No usar salvo operacion "
            "intencional."
        ),
    )

    args = parser.parse_args()

    service = (
        CapexSharePointSyncService()
    )

    print()
    print("=" * 90)
    print(
        "CAPEX -> SHAREPOINT SYNC"
    )
    print("=" * 90)

    print(
        "Lista                 :",
        service.list_name,
    )

    print(
        "Modo                  :",
        (
            "APPLY"
            if args.apply
            else "DRY-RUN"
        ),
    )

    print()

    started = (
        perf_counter()
    )

    preparation = (
        service.prepare()
    )

    prepare_seconds = (
        perf_counter()
        - started
    )

    print_plan(
        preparation
    )

    print()
    print(
        "Preparacion           :",
        f"{prepare_seconds:.3f} s",
    )

    if not args.apply:
        print()
        print(
            "ESCRITURAS REALIZADAS : 0"
        )
        print(
            "RESULTADO             : "
            "DRY-RUN OK"
        )
        print("=" * 90)
        return

    if (
        str(
            args.confirm
        ).strip()
        != service.list_name
    ):
        print()
        print(
            "RESULTADO             : "
            "BLOQUEADO"
        )
        print(
            "Motivo                : "
            "--confirm debe ser "
            f"{service.list_name}"
        )
        print(
            "ESCRITURAS REALIZADAS : 0"
        )
        print("=" * 90)

        raise SystemExit(
            2
        )

    publish_started = (
        perf_counter()
    )

    outcome = service.publish(
        preparation,
        source_batch_id=(
            args.source_batch_id
        ),
        allow_large_delete=(
            args.allow_large_delete
        ),
    )

    publish_seconds = (
        perf_counter()
        - publish_started
    )

    result = (
        outcome.publish_result
    )

    verification = (
        outcome.verification_plan
    )

    print()
    print(
        "PUBLICACION"
    )
    print("-" * 90)

    print(
        "CREATED               :",
        f"{result.created_count:,}",
    )

    print(
        "UPDATED               :",
        f"{result.updated_count:,}",
    )

    print(
        "DELETED               :",
        f"{result.deleted_count:,}",
    )

    print(
        "TOTAL WRITES          :",
        f"{result.write_count:,}",
    )

    print(
        "SyncRunId             :",
        result.sync_run_id,
    )

    print(
        "SourceBatchId         :",
        (
            result.source_batch_id
            or "(manual)"
        ),
    )

    print()
    print(
        "VERIFICACION POSTERIOR"
    )
    print("-" * 90)

    print(
        "CREATE pendiente      :",
        verification.create_count,
    )

    print(
        "UPDATE pendiente      :",
        verification.update_count,
    )

    print(
        "DELETE pendiente      :",
        verification.delete_count,
    )

    print(
        "UNCHANGED             :",
        verification.unchanged_count,
    )

    print(
        "UNMANAGED             :",
        verification.unmanaged_count,
    )

    print()
    print(
        "Publicacion+verify    :",
        f"{publish_seconds:.3f} s",
    )

    print(
        "RESULTADO             : OK"
    )

    print("=" * 90)


if __name__ == "__main__":
    main()
