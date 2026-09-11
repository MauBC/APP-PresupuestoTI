from PySide6.QtCore import (
    Qt,
    QTimer,
)
from PySide6.QtGui import (
    QColor,
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
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from app.config.budget_module_config import (
    BudgetModule,
)
from math import ceil

from app.ui.models.result_table_model import (
    ResultTableModel,
)


MONTHLY_CHART_STEP_K = 100.0


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

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        layout.setContentsMargins(
            32,
            28,
            32,
            32,
        )

        layout.setSpacing(18)

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

        else:
            budgeter_card_title = (
                "Presupuestadores"
            )

            budgeter_section_title = (
                "Presupuesto por presupuestador"
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
            "simulacion local en USD."
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

        self.refresh_button.setEnabled(
            False
        )

        top_layout.addLayout(
            title_container,
            1,
        )

        top_layout.addWidget(
            self.refresh_button
        )

        layout.addLayout(
            top_layout
        )

        cards = QHBoxLayout()
        cards.setSpacing(14)

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
            "Paises",
            "paises",
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
            "Promedio por registro",
            "USD por registro",
        )

        cards.addWidget(total_card)
        cards.addWidget(rows_card)
        cards.addWidget(countries_card)
        cards.addWidget(budgeters_card)
        cards.addWidget(average_card)

        layout.addLayout(cards)

        tables_layout = QHBoxLayout()
        tables_layout.setSpacing(16)

        country_container = QVBoxLayout()

        country_title = QLabel(
            "Presupuesto por pais"
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
            tables_layout,
            1,
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
                extra_tables_layout,
                1,
            )

        monthly_container = QVBoxLayout()

        monthly_title = QLabel(
            "Distribucion mensual"
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

    def set_workspace_ready(self):
        self._workspace_ready = True

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

        self.status_label.setText(
            "Error al preparar el presupuesto: "
            + message
        )

    def invalidate(self):
        self._loaded_once = False

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
            result = (
                self._analysis_service
                .get_dashboard()
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
        result = (
            self._analysis_service
            .get_grouped_totals(
                (
                    dimension,
                )
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

        chart.setTitle(
            "Distribucion mensual (miles de USD)"
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

        axis_y = QValueAxis()

        axis_y.setTitleText(
            "Miles de USD"
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

        value_labels = []

        for value_k in values_k:
            item = (
                QGraphicsSimpleTextItem(
                    format_monthly_bar_label_k(
                        value_k
                    ),
                    chart,
                )
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

        self.status_label.setText(
            "Dashboard calculado con "
            "los datos locales."
        )
