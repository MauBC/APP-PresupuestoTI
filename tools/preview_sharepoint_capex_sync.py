
import sys
from decimal import Decimal
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


from app.clients.sharepoint_client import (
    SharePointClient,
)
from app.config.settings import (
    settings,
)
from app.services.capex_sharepoint_summary_service import (
    CapexSharePointSummaryService,
)


ZERO = Decimal("0")


def main():
    total_started = (
        perf_counter()
    )

    summary_service = (
        CapexSharePointSummaryService()
    )

    print()
    print("=" * 90)
    print(
        "CAPEX -> SHAREPOINT SYNC PREVIEW"
    )
    print("=" * 90)
    print(
        "MODO                  : DRY-RUN"
    )
    print(
        "BigQuery              : READ-ONLY"
    )
    print(
        "SharePoint            : READ-ONLY"
    )
    print(
        "Lista                 :",
        settings
        .SHAREPOINT_CAPEX_LIST_NAME,
    )
    print()

    summary_started = (
        perf_counter()
    )

    summary = (
        summary_service
        .build_summary()
    )

    summary_seconds = (
        perf_counter()
        - summary_started
    )

    if not summary.is_balanced:
        raise RuntimeError(
            "El resumen BigQuery "
            "no esta balanceado."
        )

    desired_items = (
        summary_service
        .map_summary(
            summary
        )
    )

    sharepoint_started = (
        perf_counter()
    )

    client = (
        SharePointClient()
    )

    current_items = (
        client.get_items(
            settings
            .SHAREPOINT_CAPEX_LIST_NAME
        )
    )

    sharepoint_seconds = (
        perf_counter()
        - sharepoint_started
    )

    plan_started = (
        perf_counter()
    )

    plan = (
        summary_service
        .build_plan(
            desired_items=(
                desired_items
            ),
            current_items=(
                current_items
            ),
        )
    )

    plan_seconds = (
        perf_counter()
        - plan_started
    )

    total_seconds = (
        perf_counter()
        - total_started
    )

    desired_total = sum(
        (
            row.total_usd
            for row
            in summary.rows
        ),
        ZERO,
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
        f"{desired_total:,.2f}",
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

    print()
    print(
        "TIEMPOS"
    )
    print("-" * 90)

    print(
        "Resumen BigQuery      :",
        f"{summary_seconds:.3f} s",
    )

    print(
        "Lectura SharePoint    :",
        f"{sharepoint_seconds:.3f} s",
    )

    print(
        "Plan local            :",
        f"{plan_seconds:.3f} s",
    )

    print(
        "Total                 :",
        f"{total_seconds:.3f} s",
    )

    print()
    print(
        "ESCRITURAS REALIZADAS : 0"
    )

    print(
        "RESULTADO             :",
        (
            "OK"
            if summary.is_balanced
            else "ERROR"
        ),
    )

    if plan.unmanaged_count:
        print()
        print(
            "NOTA: existen items "
            "SharePoint sin contrato "
            "administrado. No seran "
            "modificados ni eliminados."
        )

    print("=" * 90)


if __name__ == "__main__":
    main()
