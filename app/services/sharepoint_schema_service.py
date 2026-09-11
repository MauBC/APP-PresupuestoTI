
from app.models.sharepoint_schema import (
    SharePointSchemaPlan,
)


class SharePointSchemaError(
    RuntimeError
):
    pass


class SharePointSchemaService:
    def __init__(
        self,
        client,
    ):
        self._client = client

    def plan(
        self,
        *,
        list_name,
        specs,
    ) -> SharePointSchemaPlan:
        current_columns = (
            self._client
            .get_columns(
                list_name
            )
        )

        by_name = {
            str(
                column.get(
                    "name",
                    "",
                )
                or ""
            ).strip():
                column
            for column
            in current_columns
            if str(
                column.get(
                    "name",
                    "",
                )
                or ""
            ).strip()
        }

        present = []
        missing = []
        incompatible = []

        for spec in specs:
            current = (
                by_name.get(
                    spec.name
                )
            )

            if current is None:
                missing.append(
                    spec
                )

                continue

            actual_kind = (
                self._column_kind(
                    current
                )
            )

            if actual_kind != spec.kind:
                incompatible.append(
                    f"{spec.name}: "
                    f"esperado={spec.kind}, "
                    f"actual={actual_kind}"
                )

                continue

            present.append(
                spec.name
            )

        return SharePointSchemaPlan(
            present=tuple(
                present
            ),
            missing=tuple(
                missing
            ),
            incompatible=tuple(
                incompatible
            ),
        )

    def ensure(
        self,
        *,
        list_name,
        specs,
    ) -> SharePointSchemaPlan:
        before = self.plan(
            list_name=list_name,
            specs=specs,
        )

        if not before.is_compatible:
            raise SharePointSchemaError(
                "El esquema SharePoint "
                "contiene columnas "
                "incompatibles: "
                + "; ".join(
                    before.incompatible
                )
            )

        for spec in before.missing:
            self._client.create_column(
                list_name,
                spec.graph_payload(),
            )

        after = self.plan(
            list_name=list_name,
            specs=specs,
        )

        if not after.is_complete:
            details = []

            if after.missing:
                details.append(
                    "faltantes="
                    + ", ".join(
                        spec.name
                        for spec
                        in after.missing
                    )
                )

            if after.incompatible:
                details.append(
                    "incompatibles="
                    + "; ".join(
                        after.incompatible
                    )
                )

            raise SharePointSchemaError(
                "El esquema no quedo "
                "completo despues de "
                "la creacion. "
                + " | ".join(
                    details
                )
            )

        return after

    @staticmethod
    def _column_kind(
        column,
    ) -> str:
        for kind in (
            "text",
            "number",
            "dateTime",
        ):
            if kind in column:
                return kind

        return "otro"
