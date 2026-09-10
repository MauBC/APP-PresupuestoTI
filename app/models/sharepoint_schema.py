
from dataclasses import dataclass


@dataclass(
    frozen=True,
    slots=True,
)
class SharePointColumnSpec:
    name: str
    display_name: str
    kind: str
    required: bool = False
    indexed: bool = False
    enforce_unique: bool = False
    max_length: int | None = None
    decimal_places: str | None = None

    def __post_init__(
        self,
    ):
        name = str(
            self.name
        ).strip()

        display_name = str(
            self.display_name
        ).strip()

        kind = str(
            self.kind
        ).strip()

        if not name:
            raise ValueError(
                "name no puede estar vacio."
            )

        if not display_name:
            raise ValueError(
                "display_name no puede estar vacio."
            )

        if kind not in {
            "text",
            "number",
            "dateTime",
        }:
            raise ValueError(
                "Tipo SharePoint no soportado: "
                f"{kind}"
            )

        if (
            self.enforce_unique
            and not self.indexed
        ):
            raise ValueError(
                "Una columna unica debe "
                "estar indexada."
            )

        object.__setattr__(
            self,
            "name",
            name,
        )

        object.__setattr__(
            self,
            "display_name",
            display_name,
        )

        object.__setattr__(
            self,
            "kind",
            kind,
        )

    def graph_payload(
        self,
    ) -> dict:
        payload = {
            "name":
                self.name,
            "displayName":
                self.display_name,
            "description":
                "",
            "required":
                self.required,
            "hidden":
                False,
            "indexed":
                self.indexed,
            "enforceUniqueValues":
                self.enforce_unique,
        }

        if self.kind == "text":
            payload["text"] = {
                "allowMultipleLines":
                    False,
                "appendChangesToExistingText":
                    False,
                "linesForEditing":
                    0,
                "maxLength":
                    (
                        self.max_length
                        if self.max_length
                        is not None
                        else 255
                    ),
            }

        elif self.kind == "number":
            payload["number"] = {
                "displayAs":
                    "number",
                "decimalPlaces":
                    (
                        self.decimal_places
                        if self.decimal_places
                        is not None
                        else "automatic"
                    ),
            }

        elif self.kind == "dateTime":
            payload["dateTime"] = {
                "format":
                    "dateTime",
                "displayAs":
                    "standard",
            }

        return payload


@dataclass(
    frozen=True,
    slots=True,
)
class SharePointSchemaPlan:
    present: tuple[
        str,
        ...
    ]

    missing: tuple[
        SharePointColumnSpec,
        ...
    ]

    incompatible: tuple[
        str,
        ...
    ]

    @property
    def is_compatible(
        self,
    ) -> bool:
        return not self.incompatible

    @property
    def is_complete(
        self,
    ) -> bool:
        return (
            self.is_compatible
            and not self.missing
        )
