
from decimal import (
    Decimal,
    InvalidOperation,
)

from app.models.sharepoint_summary_sync import (
    SharePointCreateAction,
    SharePointDeleteAction,
    SharePointSummarySyncPlan,
    SharePointUpdateAction,
)


class SharePointSummarySyncPlanError(
    RuntimeError
):
    pass


class SharePointSummarySyncPlanner:
    def __init__(
        self,
        *,
        compare_fields,
        module,
    ):
        self._compare_fields = tuple(
            compare_fields
        )

        self._module = str(
            module
        ).strip().upper()

        if not self._compare_fields:
            raise ValueError(
                "compare_fields no puede "
                "estar vacio."
            )

        if not self._module:
            raise ValueError(
                "module no puede "
                "estar vacio."
            )

    def build(
        self,
        *,
        desired_items,
        current_items,
    ) -> SharePointSummarySyncPlan:
        desired = tuple(
            desired_items
        )

        current = tuple(
            current_items
        )

        desired_by_key = {}

        for item in desired:
            key = str(
                item.summary_key
            ).strip()

            if not key:
                raise (
                    SharePointSummarySyncPlanError(
                        "Existe un item deseado "
                        "sin SummaryKey."
                    )
                )

            if key in desired_by_key:
                raise (
                    SharePointSummarySyncPlanError(
                        "SummaryKey duplicada "
                        "en datos deseados: "
                        f"{key}"
                    )
                )

            desired_by_key[
                key
            ] = item

        current_by_key = {}

        unmanaged = []

        for item in current:
            item_id = str(
                item.get(
                    "id",
                    "",
                )
                or ""
            ).strip()

            fields = (
                item.get(
                    "fields",
                    {}
                )
                or {}
            )

            if not isinstance(
                fields,
                dict,
            ):
                raise (
                    SharePointSummarySyncPlanError(
                        "SharePoint devolvio "
                        "fields invalido."
                    )
                )

            key = str(
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
                not key
                or module != self._module
            ):
                if item_id:
                    unmanaged.append(
                        item_id
                    )

                continue

            if not item_id:
                raise (
                    SharePointSummarySyncPlanError(
                        "SharePoint devolvio "
                        "un item administrado "
                        "sin id."
                    )
                )

            if key in current_by_key:
                raise (
                    SharePointSummarySyncPlanError(
                        "SharePoint contiene "
                        "SummaryKey duplicada: "
                        f"{key}"
                    )
                )

            current_by_key[
                key
            ] = item

        creates = []
        updates = []
        deletes = []
        unchanged = []

        for (
            key,
            desired_item,
        ) in desired_by_key.items():

            current_item = (
                current_by_key.get(
                    key
                )
            )

            if current_item is None:
                creates.append(
                    SharePointCreateAction(
                        summary_key=key,
                        fields=(
                            desired_item
                            .fields
                        ),
                    )
                )

                continue

            current_fields = (
                current_item.get(
                    "fields",
                    {}
                )
                or {}
            )

            desired_fields = (
                desired_item
                .fields_dict()
            )

            changed = any(
                not self._same_value(
                    field,
                    desired_fields.get(
                        field
                    ),
                    current_fields.get(
                        field
                    ),
                )
                for field
                in self._compare_fields
            )

            if not changed:
                unchanged.append(
                    key
                )

                continue

            updates.append(
                SharePointUpdateAction(
                    item_id=str(
                        current_item[
                            "id"
                        ]
                    ),
                    summary_key=key,
                    fields=(
                        desired_item
                        .fields
                    ),
                    etag=(
                        self._etag(
                            current_item
                        )
                    ),
                )
            )

        desired_keys = set(
            desired_by_key
        )

        for (
            key,
            current_item,
        ) in current_by_key.items():

            if key in desired_keys:
                continue

            deletes.append(
                SharePointDeleteAction(
                    item_id=str(
                        current_item[
                            "id"
                        ]
                    ),
                    summary_key=key,
                    etag=(
                        self._etag(
                            current_item
                        )
                    ),
                )
            )

        creates.sort(
            key=lambda item:
                item.summary_key
        )

        updates.sort(
            key=lambda item:
                item.summary_key
        )

        deletes.sort(
            key=lambda item:
                item.summary_key
        )

        unchanged.sort()
        unmanaged.sort()

        return (
            SharePointSummarySyncPlan(
                creates=tuple(
                    creates
                ),
                updates=tuple(
                    updates
                ),
                deletes=tuple(
                    deletes
                ),
                unchanged_keys=tuple(
                    unchanged
                ),
                unmanaged_item_ids=tuple(
                    unmanaged
                ),
                current_item_count=(
                    len(current)
                ),
                desired_item_count=(
                    len(desired)
                ),
            )
        )

    @staticmethod
    def _etag(
        item,
    ):
        value = (
            item.get(
                "eTag"
            )
            or
            item.get(
                "@odata.etag"
            )
        )

        if value is None:
            fields = (
                item.get(
                    "fields",
                    {}
                )
                or {}
            )

            value = fields.get(
                "@odata.etag"
            )

        text = str(
            value
            if value is not None
            else ""
        ).strip()

        return (
            text
            or None
        )

    @classmethod
    def _same_value(
        cls,
        field,
        desired,
        current,
    ) -> bool:
        if field == "TotalUSD":
            return (
                cls._decimal(
                    desired
                )
                ==
                cls._decimal(
                    current
                )
            )

        if field == "RegistrosOrigen":
            return (
                cls._integer(
                    desired
                )
                ==
                cls._integer(
                    current
                )
            )

        if field == "Modulo":
            return (
                cls._text(
                    desired
                ).upper()
                ==
                cls._text(
                    current
                ).upper()
            )

        return (
            cls._text(
                desired
            )
            ==
            cls._text(
                current
            )
        )

    @staticmethod
    def _text(
        value,
    ) -> str:
        if value is None:
            return ""

        return str(
            value
        ).strip()

    @staticmethod
    def _decimal(
        value,
    ) -> Decimal:
        if value is None:
            return Decimal(
                "0"
            )

        try:
            return Decimal(
                str(value)
            ).quantize(
                Decimal(
                    "0.01"
                )
            )

        except (
            InvalidOperation,
            TypeError,
            ValueError,
        ) as exc:
            raise (
                SharePointSummarySyncPlanError(
                    "SharePoint contiene "
                    "un TotalUSD invalido."
                )
            ) from exc

    @staticmethod
    def _integer(
        value,
    ) -> int:
        if value is None:
            return 0

        if isinstance(
            value,
            bool,
        ):
            raise (
                SharePointSummarySyncPlanError(
                    "SharePoint contiene "
                    "RegistrosOrigen invalido."
                )
            )

        try:
            decimal_value = Decimal(
                str(value)
            )

        except (
            InvalidOperation,
            TypeError,
            ValueError,
        ) as exc:
            raise (
                SharePointSummarySyncPlanError(
                    "SharePoint contiene "
                    "RegistrosOrigen invalido."
                )
            ) from exc

        if (
            not decimal_value.is_finite()
            or
            decimal_value
            != decimal_value
            .to_integral_value()
        ):
            raise (
                SharePointSummarySyncPlanError(
                    "SharePoint contiene "
                    "RegistrosOrigen no entero."
                )
            )

        return int(
            decimal_value
        )
