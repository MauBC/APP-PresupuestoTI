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

from app.ui.models.result_table_model import (
    ResultTableModel,
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

        cards.addWidget(total_card)
        cards.addWidget(rows_card)
        cards.addWidget(countries_card)
        cards.addWidget(budgeters_card)

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

        self._loaded_once = True

        self.status_label.setText(
            "Dashboard calculado con "
            "los datos locales."
        )
