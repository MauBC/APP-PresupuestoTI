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


META_COLUMNS = {
    "ID",
    "ContentType",
    "Modified",
    "Created",
    "Author",
    "Editor",
    "_UIVersionString",
    "Attachments",
    "Edit",
    "LinkTitle",
    "LinkTitleNoMenu",
    "DocIcon",
    "ItemChildCount",
    "FolderChildCount",
    "_ComplianceFlags",
    "_ComplianceTag",
    "_ComplianceTagWrittenTime",
    "_ComplianceTagUserId",
    "_IsRecord",
    "AppAuthor",
    "AppEditor",
    "_ColorTag",
    "ComplianceAssetId",
}


def column_kind(column):
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


def compact_value(value):
    if value is None:
        return "(NULL)"

    text = str(value)

    if len(text) > 80:
        return (
            text[:77]
            + "..."
        )

    return text


def main():
    list_name = (
        settings
        .SHAREPOINT_OPEX_LIST_NAME
    )

    client = (
        SharePointClient()
    )

    print()
    print("=" * 100)
    print(
        "SHAREPOINT OPEX INSPECTION"
    )
    print("=" * 100)

    print(
        "MODO               : READ-ONLY"
    )

    print(
        "Hostname           :",
        settings.SHAREPOINT_HOSTNAME,
    )

    print(
        "Site path          :",
        settings.SHAREPOINT_SITE_PATH,
    )

    print(
        "Lista              :",
        list_name,
    )

    print()

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
        (
            site.get("displayName")
            or site.get("name")
        ),
    )

    print(
        "List ID            :",
        target_list.get("id"),
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
    print("-" * 100)

    business_columns = []

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

        kind = column_kind(
            column
        )

        print(
            f"{name:<35}"
            f" | {display:<35}"
            f" | {kind:<14}"
            f" | required="
            f"{bool(column.get('required'))}"
        )

        if (
            name
            and name not in META_COLUMNS
        ):
            business_columns.append(
                name
            )

    print()
    print(
        "COLUMNAS DE NEGOCIO / PERSONALIZADAS"
    )
    print("-" * 100)

    for name in business_columns:
        print(
            "[FIELD]",
            name,
        )

    print()
    print(
        "MUESTRA DE ITEMS"
    )
    print("-" * 100)

    for index, item in enumerate(
        items[:5],
        start=1,
    ):
        print()
        print(
            f"ITEM {index}"
            f" | id={item.get('id')}"
        )

        fields = (
            item.get(
                "fields",
                {}
            )
            or {}
        )

        for name in business_columns:
            if name not in fields:
                continue

            print(
                f"  {name:<30}"
                f" = "
                f"{compact_value(fields[name])}"
            )

    if not items:
        print(
            "(lista sin items)"
        )

    print()
    print(
        "RESUMEN"
    )
    print("-" * 100)

    print(
        "Items              :",
        len(items),
    )

    print(
        "Campos negocio     :",
        len(
            business_columns
        ),
    )

    managed = 0
    unmanaged = 0

    for item in items:
        fields = (
            item.get(
                "fields",
                {}
            )
            or {}
        )

        summary_key = str(
            fields.get(
                "SummaryKey",
                "",
            )
            or ""
        ).strip()

        module = str(
            fields.get(
                "Modulo",
                "",
            )
            or ""
        ).strip().upper()

        if (
            summary_key
            and module == "OPEX"
        ):
            managed += 1
        else:
            unmanaged += 1

    print(
        "Managed por sync   :",
        managed,
    )

    print(
        "Unmanaged/protegido:",
        unmanaged,
    )

    print()
    print(
        "RESULTADO CONEXION : OK"
    )

    print(
        "ESCRITURAS         : 0"
    )

    print("=" * 100)


if __name__ == "__main__":
    main()
