from dataclasses import dataclass
import json

from PySide6.QtCore import QSettings

from app.config.budget_module_config import (
    BudgetModule,
)
from app.config.settings import settings


VALID_PAGE_SIZES = (
    100,
    250,
    500,
    1000,
)

VALID_ENABLED_FILTERS = (
    "enabled",
    "all",
    "disabled",
)

MIN_PAGE_INDEX = 0
MAX_NAVIGATION_PAGE_INDEX = 3


@dataclass(
    frozen=True,
    slots=True,
)
class PresupuestoViewState:
    search: str = ""
    page_size: int = 250
    enabled_filter: str = "enabled"
    months_visible: bool = False
    page_index: int = 0


@dataclass(
    frozen=True,
    slots=True,
)
class AggregationViewState:
    search: str = ""
    months_visible: bool = False
    groups: tuple = ()


class UiViewStateStore:
    ORGANIZATION = "Ransa"

    def __init__(
        self,
        backend=None,
    ):
        self._settings = (
            backend
            if backend is not None
            else QSettings(
                self.ORGANIZATION,
                settings.APP_NAME,
            )
        )

    @staticmethod
    def _module_value(
        module,
    ) -> str:
        value = getattr(
            module,
            "value",
            module,
        )

        normalized = str(
            value
        ).strip().upper()

        return BudgetModule(
            normalized
        ).value

    @staticmethod
    def _bool_value(
        value,
        default=False,
    ) -> bool:
        if isinstance(
            value,
            bool,
        ):
            return value

        if value is None:
            return bool(
                default
            )

        text = str(
            value
        ).strip().lower()

        if text in {
            "1",
            "true",
            "yes",
            "on",
        }:
            return True

        if text in {
            "0",
            "false",
            "no",
            "off",
            "",
        }:
            return False

        return bool(
            default
        )

    @staticmethod
    def _int_value(
        value,
        default,
    ) -> int:
        try:
            return int(
                value
            )

        except (
            TypeError,
            ValueError,
        ):
            return int(
                default
            )

    def _module_key(
        self,
        module,
        suffix,
    ) -> str:
        module_value = (
            self._module_value(
                module
            )
        )

        return (
            f"modules/"
            f"{module_value}/"
            f"{suffix}"
        )

    def sidebar_expanded(
        self,
        default=False,
    ) -> bool:
        return self._bool_value(
            self._settings.value(
                "global/sidebar_expanded",
                default,
            ),
            default,
        )

    def set_sidebar_expanded(
        self,
        expanded,
    ):
        self._settings.setValue(
            "global/sidebar_expanded",
            bool(expanded),
        )

    def active_module(
        self,
        default=BudgetModule.OPEX,
    ) -> BudgetModule:
        default_module = (
            BudgetModule(
                self._module_value(
                    default
                )
            )
        )

        raw = self._settings.value(
            "global/active_module",
            default_module.value,
        )

        try:
            return BudgetModule(
                str(raw)
                .strip()
                .upper()
            )

        except ValueError:
            return default_module

    def set_active_module(
        self,
        module,
    ):
        self._settings.setValue(
            "global/active_module",
            self._module_value(
                module
            ),
        )

    def last_page(
        self,
        module,
        default=0,
    ) -> int:
        result = self._int_value(
            self._settings.value(
                self._module_key(
                    module,
                    "last_page",
                ),
                default,
            ),
            default,
        )

        if not (
            MIN_PAGE_INDEX
            <= result
            <= MAX_NAVIGATION_PAGE_INDEX
        ):
            return int(
                default
            )

        return result

    def set_last_page(
        self,
        module,
        page_index,
    ):
        value = self._int_value(
            page_index,
            0,
        )

        if not (
            MIN_PAGE_INDEX
            <= value
            <= MAX_NAVIGATION_PAGE_INDEX
        ):
            return

        self._settings.setValue(
            self._module_key(
                module,
                "last_page",
            ),
            value,
        )

    def presupuesto_state(
        self,
        module,
    ) -> PresupuestoViewState:
        prefix = lambda name: (
            self._module_key(
                module,
                f"presupuesto/{name}",
            )
        )

        page_size = self._int_value(
            self._settings.value(
                prefix(
                    "page_size"
                ),
                250,
            ),
            250,
        )

        if (
            page_size
            not in VALID_PAGE_SIZES
        ):
            page_size = 250

        enabled_filter = str(
            self._settings.value(
                prefix(
                    "enabled_filter"
                ),
                "enabled",
            )
        ).strip().lower()

        if (
            enabled_filter
            not in VALID_ENABLED_FILTERS
        ):
            enabled_filter = (
                "enabled"
            )

        page_index = max(
            0,
            self._int_value(
                self._settings.value(
                    prefix(
                        "page_index"
                    ),
                    0,
                ),
                0,
            ),
        )

        return PresupuestoViewState(
            search=str(
                self._settings.value(
                    prefix(
                        "search"
                    ),
                    "",
                )
                or ""
            ),
            page_size=page_size,
            enabled_filter=(
                enabled_filter
            ),
            months_visible=(
                self._bool_value(
                    self._settings.value(
                        prefix(
                            "months_visible"
                        ),
                        False,
                    )
                )
            ),
            page_index=page_index,
        )

    def set_presupuesto_state(
        self,
        module,
        state:
            PresupuestoViewState,
    ):
        prefix = lambda name: (
            self._module_key(
                module,
                f"presupuesto/{name}",
            )
        )

        self._settings.setValue(
            prefix(
                "search"
            ),
            state.search,
        )

        self._settings.setValue(
            prefix(
                "page_size"
            ),
            state.page_size,
        )

        self._settings.setValue(
            prefix(
                "enabled_filter"
            ),
            state.enabled_filter,
        )

        self._settings.setValue(
            prefix(
                "months_visible"
            ),
            state.months_visible,
        )

        self._settings.setValue(
            prefix(
                "page_index"
            ),
            state.page_index,
        )

    def aggregation_state(
        self,
        module,
    ) -> AggregationViewState:
        prefix = lambda name: (
            self._module_key(
                module,
                f"aggregation/{name}",
            )
        )

        groups_raw = (
            self._settings.value(
                prefix(
                    "groups"
                ),
                "",
            )
        )

        groups = ()

        if groups_raw:
            try:
                parsed = json.loads(
                    str(groups_raw)
                )

                if isinstance(
                    parsed,
                    list,
                ):
                    groups = tuple(
                        (
                            None
                            if value is None
                            else str(value)
                        )
                        for value
                        in parsed[:5]
                    )

            except (
                TypeError,
                ValueError,
                json.JSONDecodeError,
            ):
                groups = ()

        return AggregationViewState(
            search=str(
                self._settings.value(
                    prefix(
                        "search"
                    ),
                    "",
                )
                or ""
            ),
            months_visible=(
                self._bool_value(
                    self._settings.value(
                        prefix(
                            "months_visible"
                        ),
                        False,
                    )
                )
            ),
            groups=groups,
        )

    def set_aggregation_state(
        self,
        module,
        state:
            AggregationViewState,
    ):
        prefix = lambda name: (
            self._module_key(
                module,
                f"aggregation/{name}",
            )
        )

        self._settings.setValue(
            prefix(
                "search"
            ),
            state.search,
        )

        self._settings.setValue(
            prefix(
                "months_visible"
            ),
            state.months_visible,
        )

        self._settings.setValue(
            prefix(
                "groups"
            ),
            json.dumps(
                list(
                    state.groups
                ),
                ensure_ascii=False,
            ),
        )

    def sync(
        self,
    ):
        sync = getattr(
            self._settings,
            "sync",
            None,
        )

        if callable(
            sync
        ):
            sync()
