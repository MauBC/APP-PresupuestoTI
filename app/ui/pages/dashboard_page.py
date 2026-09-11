from decimal import (
    Decimal,
    ROUND_HALF_UP,
)
from math import ceil

from PySide6.QtCore import (
    Qt,
    QTimer,
)
from PySide6.QtGui import (
    QColor,
    QCursor,
    QFont,
    QPainter,
)
from PySide6.QtCharts import (
    QBarCategoryAxis,
    QBarSeries,
    QBarSet,
    QChart,
    QChartView,
    QValueAxis,
)
from PySide6.QtWidgets import (
    QGraphicsSimpleTextItem,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QScrollArea,
    QTableView,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from app.config.budget_module_config import (
    BudgetModule,
)

from app.ui.models.result_table_model import (
    ResultTableModel,
)


MONTHLY_CHART_STEP_K = 100.0
DASHBOARD_TABLE_MIN_HEIGHT = 300


MONTH_LABELS = {
    "enero_usd": "Enero",
    "febrero_usd": "Febrero",
    "marzo_usd": "Marzo",
    "abril_usd": "Abril",
    "mayo_usd": "Mayo",
    "junio_usd": "Junio",
    "julio_usd": "Julio",
    "agosto_usd": "Agosto",
    "setiembre_usd": "Setiembre",
    "septiembre_usd": "Septiembre",
    "octubre_usd": "Octubre",
    "noviembre_usd": "Noviembre",
    "diciembre_usd": "Diciembre",
}


def dashboard_month_label(
    column,
):
    value = str(
        column
        if column is not None
        else ""
    ).strip().lower()

    if value in MONTH_LABELS:
        return MONTH_LABELS[
            value
        ]

    if value.endswith(
        "_usd"
    ):
        value = value[:-4]

    return (
        value
        .replace("_", " ")
        .strip()
        .title()
    )


def build_monthly_chart_data(
    monthly_totals,
):
    labels = []
    values_k = []

    for item in monthly_totals:
        labels.append(
            dashboard_month_label(
                item.get(
                    "column"
                )
            )
        )

        value = item.get(
            "total_usd"
        )

        raw_value = float(
            value
            if value is not None
            else 0
        )

        values_k.append(
            raw_value / 1000.0
        )

    return (
        tuple(labels),
        tuple(values_k),
    )


def monthly_chart_axis_max_k(
    values_k,
):
    maximum = max(
        values_k,
        default=0.0,
    )

    if maximum <= 0:
        return (
            MONTHLY_CHART_STEP_K
        )

    rounded = (
        ceil(
            maximum
            / MONTHLY_CHART_STEP_K
        )
        * MONTHLY_CHART_STEP_K
    )

    # Dejamos siempre 100k extra.
    # Esto evita cortar las etiquetas
    # que se dibujan sobre las barras.
    return (
        rounded
        + MONTHLY_CHART_STEP_K
    )


def format_monthly_bar_label_k(
    value_k,
):
    return (
        f"{float(value_k):,.0f}k"
    )


def format_monthly_bar_tooltip(
    month_label,
    value,
):
    amount = (
        value
        if value is not None
        else 0
    )

    return (
        f"{month_label}\n"
        f"US$ {amount:,.2f}"
    )


def comparison_visual_state(
    difference,
):
    value = (
        difference
        if isinstance(
            difference,
            Decimal,
        )
        else Decimal(
            str(
                difference
                if difference is not None
                else 0
            )
        )
    )

    if value > 0:
        return "increase"

    if value < 0:
        return "decrease"

    return "neutral"


def dashboard_has_active_filters(
    country_filter,
    budgeter_filter,
):
    return bool(
        str(
            country_filter
            if country_filter is not None
            else ""
        ).strip()
        or
        str(
            budgeter_filter
            if budgeter_filter is not None
            else ""
        ).strip()
    )


def dashboard_filter_status_text(
    country_filter,
    budgeter_filter,
    budgeter_title,
):
    parts = []

    country = str(
        country_filter
        if country_filter is not None
        else ""
    ).strip()

    budgeter = str(
        budgeter_filter
        if budgeter_filter is not None
        else ""
    ).strip()

    if country:
        parts.append(
            f"País: {country}"
        )

    if budgeter:
        parts.append(
            f"{budgeter_title}: "
            f"{budgeter}"
        )

    if not parts:
        return (
            "Dashboard calculado con "
            "los datos locales."
        )

    return (
        "Dashboard calculado | "
        + " | ".join(parts)
    )


def dashboard_peak_month(
    monthly_totals,
):
    if not monthly_totals:
        return (
            "",
            Decimal("0"),
        )

    best_column = ""
    best_amount = None

    for item in monthly_totals:
        column = item.get(
            "column"
        )

        value = item.get(
            "total_usd"
        )

        amount = (
            value
            if isinstance(
                value,
                Decimal,
            )
            else Decimal(
                str(
                    value
                    if value is not None
                    else 0
                )
            )
        )

        if (
            best_amount is None
            or amount > best_amount
        ):
            best_column = column
            best_amount = amount

    return (
        dashboard_month_label(
            best_column
        ),
        (
            best_amount
            if best_amount is not None
            else Decimal("0")
        ),
    )


def compare_dashboard_months(
    monthly_totals,
    base_column,
    target_column,
):
    values = {}

    for item in monthly_totals:
        column = item.get(
            "column"
        )

        value = item.get(
            "total_usd"
        )

        values[column] = (
            value
            if isinstance(
                value,
                Decimal,
            )
            else Decimal(
                str(
                    value
                    if value is not None
                    else 0
                )
            )
        )

    base = values.get(
        base_column,
        Decimal("0"),
    )

    target = values.get(
        target_column,
        Decimal("0"),
    )

    difference = (
        target
        - base
    )

    if base == 0:
        variation = (
            Decimal("0.00")
            if target == 0
            else None
        )

    else:
        variation = (
            (
                difference
                / base
            )
            * Decimal("100")
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

    return {
        "base_usd": base,
        "target_usd": target,
        "difference_usd": difference,
        "variation_percent": variation,
    }


class DashboardPage(QWidget):
    def __init__(
        self,
        analysis_service,
    ):
        super().__init__()

        self._analysis_service = (
            analysis_service
        )

        self._workspace_ready = False
        self._loaded_once = False
        self._filters_loaded = False

        self._current_monthly_totals = ()

        self._setup_ui()

    def _setup_ui(self):
        outer_layout = QVBoxLayout(
            self
        )

        outer_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        outer_layout.setSpacing(
            0
        )

        self.dashboard_scroll = (
            QScrollArea(
                self
            )
        )

        self.dashboard_scroll.setObjectName(
            "dashboardScroll"
        )

        self.dashboard_scroll.setWidgetResizable(
            True
        )

        self.dashboard_scroll.setFrameShape(
            QFrame.Shape.NoFrame
        )

        self.dashboard_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )

        self.dashboard_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        dashboard_content = QWidget()

        dashboard_content.setObjectName(
            "dashboardScrollContent"
        )

        self.dashboard_scroll.viewport().setObjectName(
            "dashboardScrollViewport"
        )

        layout = QVBoxLayout(
            dashboard_content
        )

        layout.setContentsMargins(
            32,
            28,
            32,
            32,
        )

        layout.setSpacing(
            18
        )

        self.dashboard_scroll.setWidget(
            dashboard_content
        )

        outer_layout.addWidget(
            self.dashboard_scroll
        )

        module_config = (
            self._analysis_service
            .module_config
        )

        module_label = (
            module_config.label
        )

        if (
            module_config.budgeter_column
            == "responsable"
        ):
            budgeter_card_title = (
                "Responsables"
            )

            budgeter_section_title = (
                "Presupuesto por responsable"
            )

            budgeter_filter_title = (
                "Responsable"
            )

        else:
            budgeter_card_title = (
                "Presupuestadores"
            )

            budgeter_section_title = (
                "Presupuesto por presupuestador"
            )

            budgeter_filter_title = (
                "Presupuestador"
            )

        self._budgeter_filter_title = (
            budgeter_filter_title
        )

        top_layout = QHBoxLayout()

        title_container = QVBoxLayout()

        title = QLabel(
            "Dashboard"
        )

        title.setObjectName(
            "pageTitle"
        )

        subtitle = QLabel(
            f"Resumen del presupuesto "
            f"{module_label} de la "
            "simulación local en USD."
        )

        subtitle.setObjectName(
            "pageSubtitle"
        )

        title_container.addWidget(
            title
        )

        title_container.addWidget(
            subtitle
        )

        self.refresh_button = QPushButton(
            "Recalcular"
        )

        self.refresh_button.setObjectName(
            "primaryButton"
        )

        self.refresh_button.setEnabled(
            False
        )

        top_layout.addLayout(
            title_container,
            1,
        )

        layout.addLayout(
            top_layout
        )

        filter_panel = QFrame()

        filter_panel.setObjectName(
            "filterPanel"
        )

        filter_panel_layout = (
            QVBoxLayout(
                filter_panel
            )
        )

        filter_panel_layout.setContentsMargins(
            18,
            14,
            18,
            16,
        )

        filter_panel_layout.setSpacing(
            10
        )

        filter_panel_title = QLabel(
            "Filtros"
        )

        filter_panel_title.setObjectName(
            "filterPanelTitle"
        )

        filters_layout = QHBoxLayout()

        filters_layout.setSpacing(
            10
        )

        country_filter_label = QLabel(
            "País"
        )

        country_filter_label.setObjectName(
            "filterLabel"
        )

        self.country_filter_combo = (
            QComboBox()
        )

        self.country_filter_combo.setMinimumWidth(
            180
        )

        self.country_filter_combo.addItem(
            "Todos",
            None,
        )

        self.country_filter_combo.setEnabled(
            False
        )

        budgeter_filter_label = QLabel(
            budgeter_filter_title
        )

        budgeter_filter_label.setObjectName(
            "filterLabel"
        )

        self.budgeter_filter_combo = (
            QComboBox()
        )

        self.budgeter_filter_combo.setMinimumWidth(
            220
        )

        self.budgeter_filter_combo.addItem(
            "Todos",
            None,
        )

        self.budgeter_filter_combo.setEnabled(
            False
        )

        self.clear_filters_button = QPushButton(
            "Limpiar filtros"
        )

        self.clear_filters_button.setObjectName(
            "secondaryButton"
        )

        self.clear_filters_button.setEnabled(
            False
        )

        filters_layout.addWidget(
            country_filter_label
        )

        filters_layout.addWidget(
            self.country_filter_combo
        )

        filters_layout.addSpacing(
            12
        )

        filters_layout.addWidget(
            budgeter_filter_label
        )

        filters_layout.addWidget(
            self.budgeter_filter_combo
        )

        filter_actions_layout = (
            QHBoxLayout()
        )

        filter_actions_layout.setSpacing(
            10
        )

        self.refresh_button.setMinimumWidth(
            135
        )

        self.refresh_button.setMaximumWidth(
            160
        )

        self.clear_filters_button.setMinimumWidth(
            135
        )

        self.clear_filters_button.setMaximumWidth(
            160
        )

        filter_actions_layout.addStretch(
            1
        )

        filter_actions_layout.addWidget(
            self.clear_filters_button
        )

        filter_actions_layout.addWidget(
            self.refresh_button
        )

        filters_layout.addStretch(
            1
        )

        filter_panel_layout.addWidget(
            filter_panel_title
        )

        filter_panel_layout.addLayout(
            filters_layout
        )

        filter_panel_layout.addLayout(
            filter_actions_layout
        )

        self.active_filters_label = QLabel(
            "Dashboard pendiente de calculo."
        )

        self.active_filters_label.setObjectName(
            "filterStatus"
        )

        filter_panel_layout.addWidget(
            self.active_filters_label
        )

        layout.addWidget(
            filter_panel
        )

        summary_label = QLabel(
            "RESUMEN"
        )

        summary_label.setObjectName(
            "dashboardSectionEyebrow"
        )

        layout.addWidget(
            summary_label
        )

        self.cards_layout = (
            QGridLayout()
        )

        self.cards_layout.setSpacing(
            14
        )

        (
            self.total_usd_value,
            total_card,
        ) = self._create_card(
            "Presupuesto total",
            "USD",
        )

        (
            self.rows_value,
            rows_card,
        ) = self._create_card(
            "Registros",
            "filas",
        )

        (
            self.countries_value,
            countries_card,
        ) = self._create_card(
            "Países",
            "países",
        )

        (
            self.budgeters_value,
            budgeters_card,
        ) = self._create_card(
            budgeter_card_title,
            "personas",
        )

        (
            self.average_value,
            average_card,
        ) = self._create_card(
            "Promedio anual por registro",
            "USD por registro",
        )

        (
            self.peak_month_value,
            peak_month_card,
        ) = self._create_card(
            "Mes con mayor presupuesto",
            "Mayor total mensual",
        )

        self._dashboard_cards = (
            total_card,
            rows_card,
            countries_card,
            budgeters_card,
            average_card,
            peak_month_card,
        )

        self._relayout_dashboard_cards(
            force_columns=6
        )

        layout.addLayout(
            self.cards_layout
        )

        dimensions_label = QLabel(
            "ANÁLISIS POR DIMENSIONES"
        )

        dimensions_label.setObjectName(
            "dashboardSectionEyebrow"
        )

        layout.addWidget(
            dimensions_label
        )

        tables_layout = QHBoxLayout()
        tables_layout.setSpacing(16)

        country_container = QVBoxLayout()

        country_title = QLabel(
            "Presupuesto por país"
        )

        country_title.setObjectName(
            "sectionTitle"
        )

        self.country_model = (
            ResultTableModel(self)
        )

        self.country_table = (
            self._create_table(
                self.country_model
            )
        )

        country_container.addWidget(
            country_title
        )

        country_container.addWidget(
            self.country_table
        )

        budgeter_container = QVBoxLayout()

        budgeter_title = QLabel(
            budgeter_section_title
        )

        budgeter_title.setObjectName(
            "sectionTitle"
        )

        self.budgeter_model = (
            ResultTableModel(self)
        )

        self.budgeter_table = (
            self._create_table(
                self.budgeter_model
            )
        )

        budgeter_container.addWidget(
            budgeter_title
        )

        budgeter_container.addWidget(
            self.budgeter_table
        )

        tables_layout.addLayout(
            country_container,
            1,
        )

        tables_layout.addLayout(
            budgeter_container,
            1,
        )

        layout.addLayout(
            tables_layout
        )

        if (
            module_config.module
            == BudgetModule.CAPEX
        ):
            extra_tables_layout = (
                QHBoxLayout()
            )

            extra_tables_layout.setSpacing(
                16
            )

            vicepresidency_container = (
                QVBoxLayout()
            )

            vicepresidency_title = QLabel(
                "Presupuesto por vicepresidencia"
            )

            vicepresidency_title.setObjectName(
                "sectionTitle"
            )

            self.vicepresidency_model = (
                ResultTableModel(
                    self,
                    amount_columns=(
                        "total_usd",
                    ),
                )
            )

            self.vicepresidency_table = (
                self._create_table(
                    self.vicepresidency_model
                )
            )

            vicepresidency_container.addWidget(
                vicepresidency_title
            )

            vicepresidency_container.addWidget(
                self.vicepresidency_table
            )

            manager_container = (
                QVBoxLayout()
            )

            manager_title = QLabel(
                "Presupuesto por gerente aprobador"
            )

            manager_title.setObjectName(
                "sectionTitle"
            )

            self.manager_model = (
                ResultTableModel(
                    self,
                    amount_columns=(
                        "total_usd",
                    ),
                )
            )

            self.manager_table = (
                self._create_table(
                    self.manager_model
                )
            )

            manager_container.addWidget(
                manager_title
            )

            manager_container.addWidget(
                self.manager_table
            )

            extra_tables_layout.addLayout(
                vicepresidency_container,
                1,
            )

            extra_tables_layout.addLayout(
                manager_container,
                1,
            )

            layout.addLayout(
                extra_tables_layout
            )

        monthly_container = QVBoxLayout()

        monthly_title = QLabel(
            "Distribución mensual"
        )

        monthly_title.setObjectName(
            "sectionTitle"
        )

        monthly_hint = QLabel(
            "Presupuesto USD distribuido "
            "entre enero y diciembre."
        )

        monthly_hint.setObjectName(
            "pageSubtitle"
        )

        self.monthly_chart_view = (
            QChartView(
                self
            )
        )

        self.monthly_chart_view.setRenderHint(
            QPainter.RenderHint.Antialiasing
        )

        self.monthly_chart_view.setMinimumHeight(
            350
        )

        self.monthly_chart_view.setMaximumHeight(
            420
        )

        monthly_container.addWidget(
            monthly_title
        )

        monthly_container.addWidget(
            monthly_hint
        )

        monthly_container.addWidget(
            self.monthly_chart_view
        )

        layout.addLayout(
            monthly_container
        )

        comparison_section_label = QLabel(
            "COMPARACIÓN MENSUAL"
        )

        comparison_section_label.setObjectName(
            "dashboardSectionEyebrow"
        )

        layout.addWidget(
            comparison_section_label
        )

        comparison_card = QFrame()

        comparison_card.setObjectName(
            "dashboardCard"
        )

        comparison_layout = (
            QVBoxLayout(
                comparison_card
            )
        )

        comparison_layout.setContentsMargins(
            20,
            18,
            20,
            18,
        )

        comparison_layout.setSpacing(
            12
        )

        comparison_title = QLabel(
            "Comparar meses"
        )

        comparison_title.setObjectName(
            "sectionTitle"
        )

        comparison_hint = QLabel(
            "Compara dos meses del "
            "presupuesto filtrado actual."
        )

        comparison_hint.setObjectName(
            "pageSubtitle"
        )

        comparison_selectors = (
            QHBoxLayout()
        )

        comparison_selectors.setSpacing(
            10
        )

        self.comparison_base_combo = (
            QComboBox()
        )

        self.comparison_target_combo = (
            QComboBox()
        )

        self.comparison_base_combo.setMinimumWidth(
            170
        )

        self.comparison_target_combo.setMinimumWidth(
            170
        )

        versus_label = QLabel(
            "vs"
        )

        versus_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        comparison_selectors.addWidget(
            self.comparison_base_combo
        )

        comparison_selectors.addWidget(
            versus_label
        )

        comparison_selectors.addWidget(
            self.comparison_target_combo
        )

        comparison_selectors.addStretch(
            1
        )

        metrics_layout = QGridLayout()

        metrics_layout.setHorizontalSpacing(
            24
        )

        metrics_layout.setVerticalSpacing(
            6
        )

        base_title = QLabel(
            "Mes base"
        )

        base_title.setObjectName(
            "cardTitle"
        )

        target_title = QLabel(
            "Mes comparado"
        )

        target_title.setObjectName(
            "cardTitle"
        )

        difference_title = QLabel(
            "Diferencia"
        )

        difference_title.setObjectName(
            "cardTitle"
        )

        variation_title = QLabel(
            "Variación"
        )

        variation_title.setObjectName(
            "cardTitle"
        )

        self.comparison_base_value = QLabel(
            "-"
        )

        self.comparison_target_value = QLabel(
            "-"
        )

        self.comparison_difference_value = QLabel(
            "-"
        )

        self.comparison_variation_value = QLabel(
            "-"
        )

        for widget in (
            self.comparison_base_value,
            self.comparison_target_value,
            self.comparison_difference_value,
            self.comparison_variation_value,
        ):
            widget.setObjectName(
                "cardValue"
            )

        self.comparison_base_value.setProperty(
            "comparisonRole",
            "neutralMetric",
        )

        self.comparison_target_value.setProperty(
            "comparisonRole",
            "neutralMetric",
        )

        self.comparison_difference_value.setProperty(
            "comparisonRole",
            "deltaMetric",
        )

        self.comparison_variation_value.setProperty(
            "comparisonRole",
            "deltaMetric",
        )

        metrics_layout.addWidget(
            base_title,
            0,
            0,
        )

        metrics_layout.addWidget(
            target_title,
            0,
            1,
        )

        metrics_layout.addWidget(
            difference_title,
            0,
            2,
        )

        metrics_layout.addWidget(
            variation_title,
            0,
            3,
        )

        metrics_layout.addWidget(
            self.comparison_base_value,
            1,
            0,
        )

        metrics_layout.addWidget(
            self.comparison_target_value,
            1,
            1,
        )

        metrics_layout.addWidget(
            self.comparison_difference_value,
            1,
            2,
        )

        metrics_layout.addWidget(
            self.comparison_variation_value,
            1,
            3,
        )

        comparison_layout.addWidget(
            comparison_title
        )

        comparison_layout.addWidget(
            comparison_hint
        )

        comparison_layout.addLayout(
            comparison_selectors
        )

        comparison_layout.addLayout(
            metrics_layout
        )

        layout.addWidget(
            comparison_card
        )

        self.status_label = QLabel(
            "Esperando carga del presupuesto..."
        )

        self.status_label.setObjectName(
            "tableStatus"
        )

        layout.addWidget(
            self.status_label
        )

        self.refresh_button.clicked.connect(
            self.refresh
        )

        self.country_filter_combo.currentIndexChanged.connect(
            self._on_dashboard_filter_changed
        )

        self.budgeter_filter_combo.currentIndexChanged.connect(
            self._on_dashboard_filter_changed
        )

        self.clear_filters_button.clicked.connect(
            self._clear_dashboard_filters
        )

        self.comparison_base_combo.currentIndexChanged.connect(
            self._update_monthly_comparison
        )

        self.comparison_target_combo.currentIndexChanged.connect(
            self._update_monthly_comparison
        )

    def _dashboard_card_columns(
        self,
    ) -> int:
        width = (
            self.dashboard_scroll
            .viewport()
            .width()
        )

        if width >= 1500:
            return 6

        if width >= 1050:
            return 3

        if width >= 700:
            return 2

        return 1

    def _relayout_dashboard_cards(
        self,
        *,
        force_columns=None,
    ):
        columns = (
            force_columns
            if force_columns is not None
            else self._dashboard_card_columns()
        )

        for card in (
            self._dashboard_cards
        ):
            self.cards_layout.removeWidget(
                card
            )

        for index, card in enumerate(
            self._dashboard_cards
        ):
            row = (
                index
                // columns
            )

            column = (
                index
                % columns
            )

            self.cards_layout.addWidget(
                card,
                row,
                column,
            )

        for column in range(
            max(
                columns,
                6,
            )
        ):
            self.cards_layout.setColumnStretch(
                column,
                (
                    1
                    if column < columns
                    else 0
                ),
            )

    def resizeEvent(
        self,
        event,
    ):
        super().resizeEvent(
            event
        )

        if hasattr(
            self,
            "_dashboard_cards",
        ):
            self._relayout_dashboard_cards()

    def _set_month_comparison_options(
        self,
        monthly_totals,
    ):
        previous_base = (
            self.comparison_base_combo
            .currentData()
        )

        previous_target = (
            self.comparison_target_combo
            .currentData()
        )

        self.comparison_base_combo.blockSignals(
            True
        )

        self.comparison_target_combo.blockSignals(
            True
        )

        try:
            self.comparison_base_combo.clear()
            self.comparison_target_combo.clear()

            for item in monthly_totals:
                column = item.get(
                    "column"
                )

                label = (
                    dashboard_month_label(
                        column
                    )
                )

                self.comparison_base_combo.addItem(
                    label,
                    column,
                )

                self.comparison_target_combo.addItem(
                    label,
                    column,
                )

            if previous_base is not None:
                index = (
                    self.comparison_base_combo
                    .findData(
                        previous_base
                    )
                )

                if index >= 0:
                    self.comparison_base_combo.setCurrentIndex(
                        index
                    )

            if previous_target is not None:
                index = (
                    self.comparison_target_combo
                    .findData(
                        previous_target
                    )
                )

                if index >= 0:
                    self.comparison_target_combo.setCurrentIndex(
                        index
                    )

            if (
                previous_target is None
                and
                self.comparison_target_combo.count()
                > 1
            ):
                self.comparison_target_combo.setCurrentIndex(
                    1
                )

        finally:
            self.comparison_base_combo.blockSignals(
                False
            )

            self.comparison_target_combo.blockSignals(
                False
            )

    def _set_comparison_state(
        self,
        widget,
        state,
    ):
        widget.setProperty(
            "comparisonState",
            state,
        )

        style = widget.style()

        style.unpolish(
            widget
        )

        style.polish(
            widget
        )

        widget.update()

    def _update_monthly_comparison(
        self,
        *_,
    ):
        if not self._current_monthly_totals:
            self.comparison_base_value.setText(
                "US$ 0.00"
            )

            self.comparison_target_value.setText(
                "US$ 0.00"
            )

            self.comparison_difference_value.setText(
                "US$ 0.00"
            )

            self.comparison_variation_value.setText(
                "0.00%"
            )

            self._set_comparison_state(
                self.comparison_difference_value,
                "neutral",
            )

            self._set_comparison_state(
                self.comparison_variation_value,
                "neutral",
            )

            return

        base_column = (
            self.comparison_base_combo
            .currentData()
        )

        target_column = (
            self.comparison_target_combo
            .currentData()
        )

        if (
            base_column is None
            or target_column is None
        ):
            return

        result = (
            compare_dashboard_months(
                self._current_monthly_totals,
                base_column,
                target_column,
            )
        )

        base = result[
            "base_usd"
        ]

        target = result[
            "target_usd"
        ]

        difference = result[
            "difference_usd"
        ]

        variation = result[
            "variation_percent"
        ]

        self.comparison_base_value.setText(
            f"US$ {base:,.2f}"
        )

        self.comparison_target_value.setText(
            f"US$ {target:,.2f}"
        )

        difference_prefix = (
            "+"
            if difference > 0
            else ""
        )

        self.comparison_difference_value.setText(
            f"{difference_prefix}"
            f"US$ {difference:,.2f}"
        )

        if variation is None:
            variation_text = (
                "N/D"
            )

        else:
            variation_prefix = (
                "+"
                if variation > 0
                else ""
            )

            variation_text = (
                f"{variation_prefix}"
                f"{variation:,.2f}%"
            )

        self.comparison_variation_value.setText(
            variation_text
        )

        visual_state = (
            comparison_visual_state(
                difference
            )
        )

        self._set_comparison_state(
            self.comparison_difference_value,
            visual_state,
        )

        self._set_comparison_state(
            self.comparison_variation_value,
            (
                visual_state
                if variation is not None
                else "neutral"
            ),
        )

    def _create_card(
        self,
        title_text,
        description,
    ):
        card = QFrame()

        card.setObjectName(
            "dashboardCard"
        )

        card.setMinimumHeight(
            125
        )

        layout = QVBoxLayout(card)

        layout.setContentsMargins(
            20,
            18,
            20,
            18,
        )

        title = QLabel(
            title_text
        )

        title.setObjectName(
            "cardTitle"
        )

        value = QLabel("-")

        value.setObjectName(
            "cardValue"
        )

        detail = QLabel(
            description
        )

        detail.setObjectName(
            "cardDescription"
        )

        layout.addWidget(title)
        layout.addWidget(value)
        layout.addWidget(detail)

        return value, card

    def _create_table(
        self,
        model,
    ):
        table = QTableView()

        table.setModel(
            model
        )

        table.setAlternatingRowColors(
            True
        )

        table.setMinimumHeight(
            DASHBOARD_TABLE_MIN_HEIGHT
        )

        table.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )

        table.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )

        table.setSortingEnabled(
            True
        )

        table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )

        table.verticalHeader().setVisible(
            False
        )

        header = (
            table.horizontalHeader()
        )

        header.setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )

        return table

    def _dashboard_filter_values(
        self,
    ):
        return (
            self.country_filter_combo.currentData(),
            self.budgeter_filter_combo.currentData(),
        )

    def _set_filter_combo_items(
        self,
        combo,
        values,
    ):
        previous = (
            combo.currentData()
        )

        combo.blockSignals(
            True
        )

        try:
            combo.clear()

            combo.addItem(
                "Todos",
                None,
            )

            for value in values:
                combo.addItem(
                    value,
                    value,
                )

            if previous is not None:
                index = combo.findData(
                    previous
                )

                if index >= 0:
                    combo.setCurrentIndex(
                        index
                    )

        finally:
            combo.blockSignals(
                False
            )

    def _load_dashboard_filters(
        self,
    ):
        options = (
            self._analysis_service
            .get_dashboard_filter_options()
        )

        self._set_filter_combo_items(
            self.country_filter_combo,
            options[
                "countries"
            ],
        )

        self._set_filter_combo_items(
            self.budgeter_filter_combo,
            options[
                "budgeters"
            ],
        )

        self._filters_loaded = True

        self._update_clear_filters_button_state()

    def _update_clear_filters_button_state(
        self,
    ):
        if not self._workspace_ready:
            self.clear_filters_button.setEnabled(
                False
            )
            return

        (
            country_filter,
            budgeter_filter,
        ) = self._dashboard_filter_values()

        self.clear_filters_button.setEnabled(
            dashboard_has_active_filters(
                country_filter,
                budgeter_filter,
            )
        )

    def _on_dashboard_filter_changed(
        self,
        *_,
    ):
        if (
            not self._workspace_ready
            or not self._filters_loaded
        ):
            return

        self._loaded_once = False

        self._update_clear_filters_button_state()

        self.refresh()

    def _clear_dashboard_filters(
        self,
    ):
        self.country_filter_combo.blockSignals(
            True
        )

        self.budgeter_filter_combo.blockSignals(
            True
        )

        try:
            self.country_filter_combo.setCurrentIndex(
                0
            )

            self.budgeter_filter_combo.setCurrentIndex(
                0
            )

        finally:
            self.country_filter_combo.blockSignals(
                False
            )

            self.budgeter_filter_combo.blockSignals(
                False
            )

        self._loaded_once = False

        self._update_clear_filters_button_state()

        if self._workspace_ready:
            self.refresh()

    def set_workspace_ready(self):
        self._workspace_ready = True
        self._filters_loaded = False

        self.country_filter_combo.setEnabled(
            True
        )

        self.budgeter_filter_combo.setEnabled(
            True
        )

        self._update_clear_filters_button_state()

        self.refresh_button.setEnabled(
            True
        )

        self.status_label.setText(
            "Presupuesto local disponible."
        )

    def set_workspace_error(
        self,
        message: str,
    ):
        self._workspace_ready = False

        self.refresh_button.setEnabled(
            False
        )

        self.country_filter_combo.setEnabled(
            False
        )

        self.budgeter_filter_combo.setEnabled(
            False
        )

        self.clear_filters_button.setEnabled(
            False
        )

        self.status_label.setText(
            "Error al preparar el presupuesto: "
            + message
        )

    def invalidate(self):
        self._loaded_once = False
        self._filters_loaded = False

    def ensure_loaded(self):
        if (
            self._workspace_ready
            and
            not self._loaded_once
        ):
            self.refresh()

    def refresh(self):
        if not self._workspace_ready:
            self.status_label.setText(
                "Esperando carga del presupuesto..."
            )
            return

        self.refresh_button.setEnabled(
            False
        )

        self.status_label.setText(
            "Recalculando dashboard local..."
        )

        try:
            if not self._filters_loaded:
                self._load_dashboard_filters()

            (
                country_filter,
                budgeter_filter,
            ) = self._dashboard_filter_values()

            result = (
                self._analysis_service
                .get_dashboard(
                    country_filter=country_filter,
                    budgeter_filter=budgeter_filter,
                )
            )

            self._on_loaded(result)

        except Exception as exc:
            self.status_label.setText(
                "Error al calcular dashboard: "
                f"{type(exc).__name__}: {exc}"
            )

        finally:
            self.refresh_button.setEnabled(
                True
            )

    def _dashboard_dimension_rows(
        self,
        dimension,
    ):
        (
            country_filter,
            budgeter_filter,
        ) = self._dashboard_filter_values()

        result = (
            self._analysis_service
            .get_grouped_totals(
                (
                    dimension,
                ),
                country_filter=country_filter,
                budgeter_filter=budgeter_filter,
            )
        )

        annual_column = (
            self._analysis_service
            .module_config
            .annual_column
        )

        return tuple(
            {
                dimension: (
                    row.get(
                        dimension
                    )
                    or "(Sin valor)"
                ),
                "registros": (
                    row.get(
                        "registros",
                        0,
                    )
                ),
                "total_usd": (
                    row.get(
                        annual_column
                    )
                ),
            }
            for row in result.rows
        )

    def _position_monthly_labels(
        self,
        chart,
        values_k,
        labels,
        upper_limit_k,
    ):
        plot_area = chart.plotArea()

        count = len(
            values_k
        )

        if (
            count == 0
            or plot_area.width() <= 0
            or plot_area.height() <= 0
            or upper_limit_k <= 0
        ):
            return

        category_width = (
            plot_area.width()
            / count
        )

        for (
            index,
            (
                value_k,
                label,
            ),
        ) in enumerate(
            zip(
                values_k,
                labels,
            )
        ):
            center_x = (
                plot_area.left()
                + category_width
                * (
                    index
                    + 0.5
                )
            )

            ratio = max(
                0.0,
                min(
                    float(value_k)
                    / float(
                        upper_limit_k
                    ),
                    1.0,
                ),
            )

            bar_top_y = (
                plot_area.bottom()
                - plot_area.height()
                * ratio
            )

            bounds = (
                label.boundingRect()
            )

            x = (
                center_x
                - bounds.width()
                / 2
            )

            y = (
                bar_top_y
                - bounds.height()
                - 5
            )

            minimum_y = (
                plot_area.top()
                + 2
            )

            if y < minimum_y:
                y = minimum_y

            label.setPos(
                x,
                y,
            )

    def _update_monthly_chart(
        self,
        monthly_totals,
    ):
        (
            labels,
            values_k,
        ) = build_monthly_chart_data(
            monthly_totals
        )

        bar_set = QBarSet(
            "Presupuesto mensual"
        )

        for value in values_k:
            bar_set.append(
                value
            )

        bar_set.setColor(
            QColor(
                "#08783E"
            )
        )

        bar_set.setBorderColor(
            QColor(
                "#066333"
            )
        )

        series = QBarSeries()

        series.append(
            bar_set
        )

        series.setBarWidth(
            0.58
        )

        # Las etiquetas automaticas de
        # QBarSeries pueden ocultarse por
        # clipping o deteccion de solapamiento.
        # Se dibujan manualmente mas abajo.
        series.setLabelsVisible(
            False
        )

        chart = QChart()

        chart.addSeries(
            series
        )

        chart.legend().hide()

        chart.setAnimationOptions(
            QChart.AnimationOption
            .SeriesAnimations
        )

        chart.setBackgroundBrush(
            QColor(
                "#FFFFFF"
            )
        )

        chart.setBackgroundRoundness(
            10
        )

        chart_title_font = QFont()
        chart_title_font.setPointSize(
            11
        )
        chart_title_font.setBold(
            True
        )

        chart.setTitleFont(
            chart_title_font
        )

        chart.setTitle(
            "Distribución mensual (miles de USD)"
        )

        axis_x = QBarCategoryAxis()

        axis_x.append(
            list(
                labels
            )
        )

        axis_x.setLabelsAngle(
            -35
        )

        axis_x.setLabelsColor(
            QColor(
                "#475467"
            )
        )

        axis_label_font = QFont()
        axis_label_font.setPointSize(
            9
        )

        axis_x.setLabelsFont(
            axis_label_font
        )

        axis_y = QValueAxis()

        axis_y.setTitleText(
            "Miles de USD"
        )

        axis_y.setLabelsFont(
            axis_label_font
        )

        axis_title_font = QFont()
        axis_title_font.setPointSize(
            9
        )
        axis_title_font.setBold(
            True
        )

        axis_y.setTitleFont(
            axis_title_font
        )

        axis_y.setLabelFormat(
            "%.0f"
        )

        axis_y.setLabelsColor(
            QColor(
                "#475467"
            )
        )

        axis_y.setGridLineColor(
            QColor(
                "#E4E7EC"
            )
        )

        axis_y.setTickType(
            QValueAxis.TickType
            .TicksDynamic
        )

        axis_y.setTickAnchor(
            0.0
        )

        axis_y.setTickInterval(
            MONTHLY_CHART_STEP_K
        )

        axis_y.setMinorTickCount(
            0
        )

        upper_limit_k = (
            monthly_chart_axis_max_k(
                values_k
            )
        )

        axis_y.setRange(
            0.0,
            upper_limit_k,
        )

        chart.addAxis(
            axis_x,
            Qt.AlignmentFlag.AlignBottom,
        )

        chart.addAxis(
            axis_y,
            Qt.AlignmentFlag.AlignLeft,
        )

        series.attachAxis(
            axis_x
        )

        series.attachAxis(
            axis_y
        )

        tooltip_values = tuple(
            item.get(
                "total_usd"
            )
            for item in monthly_totals
        )

        def show_monthly_tooltip(
            status,
            index,
            *_,
        ):
            if (
                not status
                or index < 0
                or index >= len(labels)
            ):
                QToolTip.hideText()
                return

            QToolTip.showText(
                QCursor.pos(),
                format_monthly_bar_tooltip(
                    labels[index],
                    tooltip_values[index],
                ),
                self.monthly_chart_view,
            )

        series.hovered.connect(
            show_monthly_tooltip
        )

        self._monthly_hover_handler = (
            show_monthly_tooltip
        )

        value_labels = []

        bar_label_font = QFont()

        bar_label_font.setPointSize(
            9
        )

        bar_label_font.setBold(
            True
        )

        for value_k in values_k:
            item = (
                QGraphicsSimpleTextItem(
                    format_monthly_bar_label_k(
                        value_k
                    ),
                    chart,
                )
            )

            item.setFont(
                bar_label_font
            )

            item.setBrush(
                QColor(
                    "#344054"
                )
            )

            item.setZValue(
                10
            )

            value_labels.append(
                item
            )

        def position_labels(
            *args,
        ):
            self._position_monthly_labels(
                chart,
                values_k,
                value_labels,
                upper_limit_k,
            )

        chart.plotAreaChanged.connect(
            position_labels
        )

        QTimer.singleShot(
            0,
            position_labels,
        )

        old_chart = (
            self.monthly_chart_view
            .chart()
        )

        self.monthly_chart_view.setChart(
            chart
        )

        if (
            old_chart is not None
            and old_chart is not chart
        ):
            old_chart.deleteLater()

    def _on_loaded(
        self,
        result,
    ):
        self.total_usd_value.setText(
            f"US$ {result.total_usd:,.2f}"
        )

        self.rows_value.setText(
            f"{result.total_rows:,}"
        )

        self.countries_value.setText(
            f"{result.total_countries:,}"
        )

        self.budgeters_value.setText(
            f"{result.total_budgeters:,}"
        )

        self.average_value.setText(
            "US$ "
            f"{result.average_usd_per_row:,.2f}"
        )

        (
            peak_month,
            peak_amount,
        ) = dashboard_peak_month(
            result.monthly_totals
        )

        if peak_month:
            self.peak_month_value.setText(
                f"{peak_month} - "
                f"US$ {peak_amount:,.0f}"
            )

        else:
            self.peak_month_value.setText(
                "-"
            )

        self._current_monthly_totals = (
            result.monthly_totals
        )

        self._set_month_comparison_options(
            result.monthly_totals
        )

        self._update_monthly_comparison()

        self._update_monthly_chart(
            result.monthly_totals
        )

        self.country_model.set_data(
            result.by_country,
            (
                "pais",
                "registros",
                "total_usd",
            ),
        )

        budgeter_column = (
            self._analysis_service
            .module_config
            .budgeter_column
            or "presupuestador"
        )

        if (
            budgeter_column
            == "responsable"
        ):
            budgeter_rows = tuple(
                {
                    "responsable":
                        row.get(
                            "presupuestador"
                        ),
                    "registros":
                        row.get(
                            "registros"
                        ),
                    "total_usd":
                        row.get(
                            "total_usd"
                        ),
                }
                for row in (
                    result.by_budgeter
                )
            )

        else:
            budgeter_rows = (
                result.by_budgeter
            )

        self.budgeter_model.set_data(
            budgeter_rows,
            (
                budgeter_column,
                "registros",
                "total_usd",
            ),
        )

        module_config = (
            self._analysis_service
            .module_config
        )

        if (
            module_config.module
            == BudgetModule.CAPEX
        ):
            vicepresidency_rows = (
                self._dashboard_dimension_rows(
                    "vicepresidencia"
                )
            )

            manager_rows = (
                self._dashboard_dimension_rows(
                    "gerente_aprobador"
                )
            )

            self.vicepresidency_model.set_data(
                vicepresidency_rows,
                (
                    "vicepresidencia",
                    "registros",
                    "total_usd",
                ),
            )

            self.manager_model.set_data(
                manager_rows,
                (
                    "gerente_aprobador",
                    "registros",
                    "total_usd",
                ),
            )

        self._loaded_once = True

        (
            country_filter,
            budgeter_filter,
        ) = self._dashboard_filter_values()

        status_text = (
            dashboard_filter_status_text(
                country_filter,
                budgeter_filter,
                self._budgeter_filter_title,
            )
        )

        self.status_label.setText(
            status_text
        )

        self.active_filters_label.setText(
            status_text
        )
