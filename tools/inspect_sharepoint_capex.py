
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


from app.clients.sharepoint_client import (
    SharePointClient,
)
from app.config.settings import (
    settings,
)
from app.config.sharepoint_summary_config import (
    CAPEX_SHAREPOINT_FIELDS,
)


def column_kind(
    column,
):
    known = (
        "text",
        "number",
        "dateTime",
        "choice",
        "boolean",
        "currency",
        "lookup",
        "personOrGroup",
    )

    for name in known:
        if name in column:
            return name

    return "otro"


def main():
    list_name = (
        settings
        .SHAREPOINT_CAPEX_LIST_NAME
    )

    print()
    print("=" * 90)
    print(
        "SHAREPOINT CAPEX INSPECTION"
    )
    print("=" * 90)
    print(
        "MODO               : READ-ONLY"
    )
    print(
        "Hostname           :",
        settings
        .SHAREPOINT_HOSTNAME,
    )
    print(
        "Site path          :",
        settings
        .SHAREPOINT_SITE_PATH,
    )
    print(
        "Lista              :",
        list_name,
    )
    print()

    client = (
        SharePointClient()
    )

    site = (
        client.get_site()
    )

    target_list = (
        client.get_list(
            list_name
        )
    )

    columns = (
        client.get_columns(
            list_name
        )
    )

    items = (
        client.get_items(
            list_name
        )
    )

    print(
        "Site ID            :",
        site.get("id"),
    )

    print(
        "Site               :",
        site.get(
            "displayName"
        )
        or site.get("name"),
    )

    print(
        "List ID            :",
        target_list.get(
            "id"
        ),
    )

    print(
        "List display name  :",
        target_list.get(
            "displayName"
        ),
    )

    print(
        "Items actuales     :",
        f"{len(items):,}",
    )

    print(
        "Columnas actuales  :",
        f"{len(columns):,}",
    )

    print()
    print(
        "COLUMNAS SHAREPOINT"
    )
    print("-" * 90)

    actual_names = set()

    for column in columns:
        name = str(
            column.get(
                "name",
                "",
            )
            or ""
        ).strip()

        display = str(
            column.get(
                "displayName",
                "",
            )
            or ""
        ).strip()

        if name:
            actual_names.add(
                name
            )

        print(
            f"{name:<35} "
            f"| {display:<30} "
            f"| {column_kind(column):<14} "
            f"| required="
            f"{bool(column.get('required'))}"
        )

    expected = set(
        CAPEX_SHAREPOINT_FIELDS
    )

    missing = sorted(
        expected
        - actual_names
    )

    present = sorted(
        expected
        & actual_names
    )

    print()
    print(
        "CONTRATO CAPEX"
    )
    print("-" * 90)

    print(
        "Presentes          :",
        (
            ", ".join(
                present
            )
            if present
            else "(ninguna)"
        ),
    )

    print(
        "Faltantes          :",
        (
            ", ".join(
                missing
            )
            if missing
            else "(ninguna)"
        ),
    )

    print()
    print(
        "RESULTADO CONEXION : OK"
    )

    print(
        "RESULTADO ESQUEMA  :",
        (
            "LISTO"
            if not missing
            else "REQUIERE COLUMNAS"
        ),
    )

    print(
        "ESCRITURAS         : 0"
    )

    print("=" * 90)


if __name__ == "__main__":
    main()
