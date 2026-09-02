from PySide6.QtCore import (
    QSortFilterProxyModel,
    Qt,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from app.ui.models.presupuesto_table_model import (
    PresupuestoTableModel,
)
from app.ui.workers.presupuesto_loader import (
    PresupuestoLoadThread,
)


class PresupuestoPage(QWidget):
    def __init__(self):
        super().__init__()

        self._page_index = 0
        self._page_size = 250
        self._total_rows = 0

        self._loaded_once = False
        self._loader = None

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        layout.setContentsMargins(
            32,
            28,
            32,
            32,
        )

        layout.setSpacing(16)

        title = QLabel(
            "Presupuesto"
        )
        title.setObjectName(
            "pageTitle"
        )

        subtitle = QLabel(
            "Consulta de registros "
            "presupuestales almacenados "
            "en Google Cloud"
        )
        subtitle.setObjectName(
            "pageSubtitle"
        )

        layout.addWidget(title)
        layout.addWidget(subtitle)

        toolbar = QHBoxLayout()

        self.search_input = QLineEdit()

        self.search_input.setPlaceholderText(
            "Buscar en la pagina actual..."
        )

        self.page_size_combo = QComboBox()

        self.page_size_combo.addItems(
            [
                "100",
                "250",
                "500",
                "1000",
            ]
        )

        self.page_size_combo.setCurrentText(
            "250"
        )

        self.refresh_button = QPushButton(
            "Actualizar"
        )

        toolbar.addWidget(
            self.search_input,
            1,
        )

        toolbar.addWidget(
            QLabel("Filas:")
        )

        toolbar.addWidget(
            self.page_size_combo
        )

        toolbar.addWidget(
            self.refresh_button
        )

        layout.addLayout(
            toolbar
        )

        self.model = (
            PresupuestoTableModel(
                self
            )
        )

        self.proxy_model = (
            QSortFilterProxyModel(
                self
            )
        )

        self.proxy_model.setSourceModel(
            self.model
        )

        self.proxy_model.setFilterCaseSensitivity(
            Qt.CaseSensitivity.CaseInsensitive
        )

        self.proxy_model.setFilterKeyColumn(
            -1
        )

        self.proxy_model.setSortRole(
            Qt.ItemDataRole.UserRole
        )

        self.table = QTableView()

        self.table.setModel(
            self.proxy_model
        )

        self.table.setAlternatingRowColors(
            True
        )

        self.table.setSortingEnabled(
            True
        )

        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectItems
        )

        self.table.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )

        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )

        self.table.setHorizontalScrollMode(
            QAbstractItemView.ScrollMode.ScrollPerPixel
        )

        self.table.setVerticalScrollMode(
            QAbstractItemView.ScrollMode.ScrollPerPixel
        )

        self.table.verticalHeader().setVisible(
            False
        )

        header = (
            self.table.horizontalHeader()
        )

        header.setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive
        )

        header.setDefaultSectionSize(
            150
        )

        header.setMinimumSectionSize(
            80
        )

        layout.addWidget(
            self.table,
            1,
        )

        footer = QHBoxLayout()

        self.status_label = QLabel(
            "Datos no cargados"
        )

        self.status_label.setObjectName(
            "tableStatus"
        )

        self.previous_button = QPushButton(
            "Anterior"
        )

        self.page_label = QLabel(
            "Pagina -"
        )

        self.next_button = QPushButton(
            "Siguiente"
        )

        footer.addWidget(
            self.status_label,
            1,
        )

        footer.addWidget(
            self.previous_button
        )

        footer.addWidget(
            self.page_label
        )

        footer.addWidget(
            self.next_button
        )

        layout.addLayout(
            footer
        )

        self.search_input.textChanged.connect(
            self.proxy_model.setFilterFixedString
        )

        self.refresh_button.clicked.connect(
            self.refresh
        )

        self.previous_button.clicked.connect(
            self.previous_page
        )

        self.next_button.clicked.connect(
            self.next_page
        )

        self.page_size_combo.currentTextChanged.connect(
            self._page_size_changed
        )

        self._update_navigation()

    def ensure_loaded(self):
        if self._loaded_once:
            return

        self._load_page(0)

    def refresh(self):
        self._load_page(
            self._page_index
        )

    def previous_page(self):
        if self._page_index <= 0:
            return

        self._load_page(
            self._page_index - 1
        )

    def next_page(self):
        total_pages = (
            self._calculate_total_pages()
        )

        if (
            self._page_index
            >= total_pages - 1
        ):
            return

        self._load_page(
            self._page_index + 1
        )

    def _page_size_changed(
        self,
        text: str,
    ):
        self._page_size = int(text)

        if self._loaded_once:
            self._load_page(0)

    def _load_page(
        self,
        page_index: int,
    ):
        if (
            self._loader is not None
            and self._loader.isRunning()
        ):
            return

        self._set_loading(
            True
        )

        self.status_label.setText(
            "Cargando datos desde BigQuery..."
        )

        self._loader = (
            PresupuestoLoadThread(
                page_index=page_index,
                page_size=self._page_size,
                parent=self,
            )
        )

        self._loader.loaded.connect(
            self._on_loaded
        )

        self._loader.failed.connect(
            self._on_failed
        )

        self._loader.finished.connect(
            self._on_loader_finished
        )

        self._loader.start()

    def _on_loaded(
        self,
        result,
    ):
        self.model.set_page(
            result
        )

        self._page_index = (
            result.page_index
        )

        self._total_rows = (
            result.total_rows
        )

        self._loaded_once = True

        self.search_input.clear()

        self._update_navigation()

    def _on_failed(
        self,
        error_message: str,
    ):
        self.status_label.setText(
            "Error al cargar datos: "
            + error_message
        )

    def _on_loader_finished(self):
        self._set_loading(
            False
        )

        if self._loader is not None:
            self._loader.deleteLater()
            self._loader = None

    def _set_loading(
        self,
        loading: bool,
    ):
        self.refresh_button.setEnabled(
            not loading
        )

        self.page_size_combo.setEnabled(
            not loading
        )

        self.previous_button.setEnabled(
            False if loading else True
        )

        self.next_button.setEnabled(
            False if loading else True
        )

        if not loading:
            self._update_navigation()

    def _calculate_total_pages(self):
        if self._total_rows == 0:
            return 1

        return (
            self._total_rows
            + self._page_size
            - 1
        ) // self._page_size

    def _update_navigation(self):
        total_pages = (
            self._calculate_total_pages()
        )

        self.previous_button.setEnabled(
            self._page_index > 0
        )

        self.next_button.setEnabled(
            self._page_index
            < total_pages - 1
        )

        self.page_label.setText(
            f"Pagina "
            f"{self._page_index + 1} "
            f"de {total_pages}"
        )

        if self._total_rows == 0:
            self.status_label.setText(
                "Sin registros"
            )

            return

        first_row = (
            self._page_index
            * self._page_size
            + 1
        )

        last_row = min(
            first_row
            + self._page_size
            - 1,
            self._total_rows,
        )

        self.status_label.setText(
            f"Mostrando "
            f"{first_row:,} - "
            f"{last_row:,} "
            f"de "
            f"{self._total_rows:,} "
            f"registros"
        )