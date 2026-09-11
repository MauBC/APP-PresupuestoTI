from decimal import Decimal

from PySide6.QtCore import (
    QSortFilterProxyModel,
    Qt,
    Signal,
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

from app.config.grouping_config import (
    MAX_GROUPING_LEVELS,
)
from app.services.dimension_allocation_service import (
    DimensionAllocationService,
)
from app.services.group_monthly_distribution_service import (
    GroupMonthlyDistributionService,
)
from app.services.presupuesto_change_summary_service import (
    PresupuestoChangeSummaryService,
)
from app.services.presupuesto_group_edit_service import (
    PresupuestoGroupEditError,
    PresupuestoGroupEditService,
)
from app.ui.dialogs.app_message_box import (
    AppMessageBox,
    ask_confirmation,
)
from app.ui.dialogs.change_summary_dialog import (
    ChangeSummaryDialog,
)
from app.ui.dialogs.group_edit_dialog import (
    GroupEditDialog,
)
from app.ui.dialogs.monthly_distribution_dialog import (
    MonthlyDistributionDialog,
)
from app.ui.dialogs.dimension_allocation_dialog import (
    DimensionAllocationDialog,
)
from app.ui.models.result_table_model import (
    ResultTableModel,
)


ZERO = Decimal("0.00")


class AggregationPage(QWidget):
    workspace_changed = Signal()

    def __init__(
        self,
        *,
        workspace,
        analysis_service,
    ):
        super().__init__()

        self._workspace = workspace

        self._analysis_service = (
            analysis_service
        )

        self._group_edit_service = (
            PresupuestoGroupEditService(
                workspace
            )
        )

        self._group_monthly_distribution_service = (
            GroupMonthlyDistributionService(
                workspace
            )
        )

        self._change_summary_service = (
            PresupuestoChangeSummaryService(
                workspace
            )
        )

        self._dimension_allocation_service = (
            DimensionAllocationService(
                workspace
            )
        )

        self._workspace_ready = False
        self._loaded_once = False
        self._current_result = None

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        layout.setContentsMargins(
            32,
            28,
            32,
            32,
        )

        layout.setSpacing(12)

        title = QLabel(
            "Agrupaciones"
        )

        title.setObjectName(
            "pageTitle"
        )

        subtitle = QLabel(
            "Agrupa el presupuesto por hasta "
            f"{MAX_GROUPING_LEVELS} dimensiones "
            "y modifica totales USD "
            "de forma masiva."
        )

        subtitle.setObjectName(
            "pageSubtitle"
        )

        layout.addWidget(title)
        layout.addWidget(subtitle)

        group_layout = QVBoxLayout()

        group_row_1 = QHBoxLayout()
        group_row_2 = QHBoxLayout()

        self.group_combos = tuple(
            self._create_group_combo(
                allow_none=(
                    index > 0
                )
            )
            for index
            in range(
                MAX_GROUPING_LEVELS
            )
        )

        (
            self.group_1,
            self.group_2,
            self.group_3,
            self.group_4,
            self.group_5,
        ) = self.group_combos

        default_group = (
            self._workspace
            .module_config
            .budgeter_column
        )

        if (
            default_group
            not in self._workspace
            .module_config
            .groupable_columns
        ):
            groupable = (
                self._workspace
                .module_config
                .groupable_columns
            )

            default_group = (
                groupable[0]
                if groupable
                else None
            )

        if default_group is not None:
            self._set_combo_value(
                self.group_1,
                default_group,
            )

        self.group_button = QPushButton(
            "Aplicar agrupacion"
        )

        self.group_button.setObjectName(
            "primaryButton"
        )

        self.group_button.setEnabled(
            False
        )

        group_row_1.addWidget(
            QLabel("Agrupar por:")
        )

        group_row_1.addWidget(
            self.group_1
        )

        group_row_1.addWidget(
            self.group_2
        )

        group_row_1.addWidget(
            self.group_3
        )

        group_row_2.addWidget(
            QLabel("Niveles 4-5:")
        )

        group_row_2.addWidget(
            self.group_4
        )

        group_row_2.addWidget(
            self.group_5
        )

        group_row_2.addWidget(
            self.group_button
        )

        group_row_2.addStretch()

        group_layout.addLayout(
            group_row_1
        )

        group_layout.addLayout(
            group_row_2
        )

        layout.addLayout(
            group_layout
        )

        distribution_layout = (
            QHBoxLayout()
        )

        distribution_layout.addWidget(
            QLabel(
                "Distribucion avanzada:"
            )
        )

        self.distribute_group_months_button = (
            QPushButton(
                "Distribuir meses del grupo"
            )
        )

        self.distribute_group_months_button.setEnabled(
            False
        )

        self.distribute_ceco_button = (
            QPushButton(
                "Distribuir por CECO"
            )
        )

        self.distribute_country_button = (
            QPushButton(
                "Distribuir por pais"
            )
        )

        self.distribute_ceco_button.setEnabled(
            False
        )

        self.distribute_country_button.setEnabled(
            False
        )

        distribution_layout.addWidget(
            self.distribute_group_months_button
        )

        distribution_layout.addWidget(
            self.distribute_ceco_button
        )

        distribution_layout.addWidget(
            self.distribute_country_button
        )

        distribution_layout.addStretch()

        layout.addLayout(
            distribution_layout
        )

        search_layout = QHBoxLayout()

        self.search_input = QLineEdit()

        self.search_input.setPlaceholderText(
            "Buscar dentro del resultado agrupado..."
        )

        self.summary_label = QLabel(
            "Sin resultados"
        )

        self.summary_label.setObjectName(
            "analysisSummary"
        )

        search_layout.addWidget(
            self.search_input,
            1,
        )

        search_layout.addWidget(
            self.summary_label
        )

        layout.addLayout(
            search_layout
        )

        navigation_layout = QHBoxLayout()

        self.selected_context_label = QLabel(
            "Fila seleccionada: ninguna"
        )

        self.selected_context_label.setStyleSheet(
            "QLabel {"
            "background-color: #F1F3F5;"
            "color: #344054;"
            "border: 1px solid #D8DEE4;"
            "border-radius: 6px;"
            "padding: 7px 10px;"
            "font-weight: 600;"
            "}"
        )

        self.group_state_button = QPushButton(
            "Deshabilitar grupo"
        )

        self.group_state_button.setObjectName(
            "warningButton"
        )

        self.group_state_button.setEnabled(
            False
        )

        self.group_state_button.setToolTip(
            "Deshabilita todas las filas "
            "reales habilitadas que pertenecen "
            "a la agrupacion seleccionada."
        )

        self.go_start_button = QPushButton(
            "Ir al inicio"
        )

        self.go_annual_button = QPushButton(
            "Ir a ANIO USD"
        )

        self.go_start_button.setEnabled(
            False
        )

        self.go_annual_button.setEnabled(
            False
        )

        navigation_layout.addWidget(
            self.selected_context_label,
            1,
        )

        navigation_layout.addWidget(
            self.group_state_button
        )

        navigation_layout.addWidget(
            self.go_start_button
        )

        navigation_layout.addWidget(
            self.go_annual_button
        )

        layout.addLayout(
            navigation_layout
        )

        changes_layout = QHBoxLayout()

        self.pending_label = QLabel(
            "Cambios pendientes: 0"
        )

        self.pending_label.setObjectName(
            "pendingSummary"
        )

        self.variation_label = QLabel(
            "Variacion total: US$ 0.00"
        )

        self._set_variation_badge(
            ZERO,
            None,
        )

        self.view_changes_button = QPushButton(
            "Ver cambios"
        )

        self.undo_button = QPushButton(
            "Deshacer ultima operacion"
        )

        self.discard_button = QPushButton(
            "Descartar todos"
        )

        self.discard_button.setObjectName(
            "dangerButton"
        )

        changes_layout.addWidget(
            self.pending_label
        )

        changes_layout.addWidget(
            self.variation_label
        )

        changes_layout.addStretch()

        changes_layout.addWidget(
            self.view_changes_button
        )

        changes_layout.addWidget(
            self.undo_button
        )

        changes_layout.addWidget(
            self.discard_button
        )

        layout.addLayout(
            changes_layout
        )

        hint = QLabel(
            "Doble clic en ENERO USD - DICIEMBRE USD "
            "o ANIO USD para modificar todo el grupo."
        )

        hint.setObjectName(
            "tableStatus"
        )

        layout.addWidget(
            hint
        )

        self.model = ResultTableModel(
            self,
            amount_columns=(
                self._workspace
                .module_config
                .amount_columns
            ),
        )

        self.proxy_model = (
            QSortFilterProxyModel(
                self
            )
        )

        self.proxy_model.setSourceModel(
            self.model
        )

        self.proxy_model.setFilterKeyColumn(
            -1
        )

        self.proxy_model.setFilterCaseSensitivity(
            Qt.CaseSensitivity.CaseInsensitive
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

        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )

        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )

        self.table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )

        self.table.setHorizontalScrollMode(
            QAbstractItemView.ScrollMode.ScrollPerPixel
        )

        self.table.setVerticalScrollMode(
            QAbstractItemView.ScrollMode.ScrollPerPixel
        )

        self.table.verticalHeader().setVisible(
            True
        )

        self.table.verticalHeader().setDefaultSectionSize(
            28
        )

        self.table.verticalHeader().setMinimumWidth(
            44
        )

        self.table.verticalHeader().setMaximumWidth(
            44
        )

        header = (
            self.table.horizontalHeader()
        )

        header.setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive
        )

        header.setDefaultSectionSize(
            145
        )

        layout.addWidget(
            self.table,
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

        self.search_input.textChanged.connect(
            self.proxy_model
            .setFilterFixedString
        )

        self.group_button.clicked.connect(
            self.load_grouping
        )

        self.distribute_group_months_button.clicked.connect(
            self._show_group_month_distribution
        )

        self.distribute_ceco_button.clicked.connect(
            lambda:
                self._show_dimension_distribution(
                    self._workspace
                    .module_config
                    .ceco_column
                )
        )

        self.distribute_country_button.clicked.connect(
            lambda:
                self._show_dimension_distribution(
                    self._workspace
                    .module_config
                    .country_column
                )
        )

        self.table.doubleClicked.connect(
            self._edit_group_cell
        )

        self.table.clicked.connect(
            self._update_selected_context
        )

        self.table.clicked.connect(
            self._update_group_month_distribution_control
        )

        self.group_state_button.clicked.connect(
            self.disable_selected_group
        )

        self.go_start_button.clicked.connect(
            self._go_to_start
        )

        self.go_annual_button.clicked.connect(
            self._go_to_annual
        )

        self.view_changes_button.clicked.connect(
            self.show_change_summary
        )

        self.undo_button.clicked.connect(
            self.undo_last
        )

        self.discard_button.clicked.connect(
            self.discard_all
        )

        self._update_change_controls()

    def set_workspace_ready(self):
        self._workspace_ready = True
        self._update_distribution_controls()

        self.group_button.setEnabled(
            True
        )

        self.status_label.setText(
            "Presupuesto local disponible."
        )

        self._update_change_controls()

    def set_workspace_error(
        self,
        message: str,
    ):
        self._workspace_ready = False
        self._update_distribution_controls()

        self.group_button.setEnabled(
            False
        )

        self.status_label.setText(
            "Error al preparar presupuesto: "
            + message
        )

        self.group_state_button.setEnabled(
            False
        )

    def invalidate(self):
        self._loaded_once = False

    def _create_group_combo(
        self,
        allow_none: bool,
    ):
        combo = QComboBox()

        if allow_none:
            combo.addItem(
                "Ninguno",
                None,
            )

        for column in (
            self._workspace
            .module_config
            .groupable_columns
        ):
            label = (
                column
                .replace("_", " ")
                .title()
            )

            combo.addItem(
                label,
                column,
            )

        return combo

    def _set_combo_value(
        self,
        combo,
        value,
    ):
        index = combo.findData(
            value
        )

        if index >= 0:
            combo.setCurrentIndex(
                index
            )

    def ensure_loaded(self):
        if (
            self._workspace_ready
            and not self._loaded_once
        ):
            self.load_grouping()

    def _selected_groups(self):
        return [
            combo.currentData()
            for combo
            in self.group_combos
            if combo.currentData()
        ]

    def load_grouping(self):
        if not self._workspace_ready:
            self.status_label.setText(
                "Esperando carga del presupuesto..."
            )
            return

        groups = self._selected_groups()

        if len(groups) != len(set(groups)):
            self.status_label.setText(
                "No se puede repetir una columna "
                "en la agrupacion."
            )
            return

        self.group_button.setEnabled(
            False
        )

        self.status_label.setText(
            "Calculando agrupacion local..."
        )

        try:
            result = (
                self._analysis_service
                .get_grouped_totals(
                    groups
                )
            )

            self._on_loaded(
                result
            )

        except Exception as exc:
            self.status_label.setText(
                "Error: "
                f"{type(exc).__name__}: {exc}"
            )

        finally:
            self.group_button.setEnabled(
                True
            )

    def _on_loaded(
        self,
        result,
    ):
        self._current_result = result

        self.model.set_data(
            result.rows,
            result.columns,
        )

        self.search_input.clear()

        self._loaded_once = True

        total_usd = sum(
            (
                row.get(
                    self._workspace
                    .module_config
                    .annual_column
                )
                or Decimal("0")
            )
            for row in result.rows
        )

        self.summary_label.setText(
            f"{len(result.rows):,} grupos | "
            f"Total USD: {total_usd:,.2f}"
        )

        group_names = ", ".join(
            column
            .replace("_", " ")
            .title()
            for column
            in result.group_columns
        )

        self.status_label.setText(
            "Agrupacion local por: "
            + group_names
        )

        has_rows = bool(
            result.rows
        )

        self.go_start_button.setEnabled(
            has_rows
        )

        self.go_annual_button.setEnabled(
            has_rows
        )

        self.selected_context_label.setText(
            "Fila seleccionada: ninguna"
        )

        self._update_group_month_distribution_control()
        self._update_change_controls()

        self._update_group_state_button()

    def _update_selected_context(
        self,
        proxy_index,
    ):
        if not proxy_index.isValid():
            return

        if self._current_result is None:
            return

        source_index = (
            self.proxy_model
            .mapToSource(
                proxy_index
            )
        )

        row = self.model.row_dict(
            source_index.row()
        )

        parts = [
            f"Fila seleccionada: "
            f"{proxy_index.row() + 1}"
        ]

        for column in (
            self._current_result
            .group_columns
        ):
            value = row.get(
                column
            )

            label = (
                column
                .replace("_", " ")
                .title()
            )

            parts.append(
                f"{label}: {value}"
            )

        self.selected_context_label.setText(
            "  |  ".join(parts)
        )

        self._update_group_state_button()


    def _selected_group_scope(
        self,
    ):
        if self._current_result is None:
            return None

        proxy_index = (
            self.table.currentIndex()
        )

        if not proxy_index.isValid():
            return None

        source_index = (
            self.proxy_model.mapToSource(
                proxy_index
            )
        )

        if not source_index.isValid():
            return None

        row = (
            self.model.row_dict(
                source_index.row()
            )
        )

        group_columns = tuple(
            self._current_result
            .group_columns
        )

        if not group_columns:
            return None

        group_values = tuple(
            row.get(column)
            for column
            in group_columns
        )

        return (
            row,
            group_columns,
            group_values,
        )

    def _update_group_state_button(
        self,
    ):
        if not hasattr(
            self,
            "group_state_button",
        ):
            return

        scope = (
            self._selected_group_scope()
        )

        if (
            not self._workspace_ready
            or scope is None
        ):
            self.group_state_button.setEnabled(
                False
            )

            self.group_state_button.setText(
                "Deshabilitar grupo"
            )

            return

        (
            _,
            group_columns,
            group_values,
        ) = scope

        try:
            row_ids = (
                self._group_edit_service
                .get_group_row_ids(
                    group_columns=(
                        group_columns
                    ),
                    group_values=(
                        group_values
                    ),
                    enabled=True,
                )
            )

        except Exception:
            row_ids = ()

        self.group_state_button.setEnabled(
            bool(row_ids)
        )

        if row_ids:
            self.group_state_button.setText(
                "Deshabilitar grupo "
                f"({len(row_ids):,})"
            )

        else:
            self.group_state_button.setText(
                "Deshabilitar grupo"
            )

    def disable_selected_group(
        self,
    ):
        scope = (
            self._selected_group_scope()
        )

        if scope is None:
            return

        (
            row,
            group_columns,
            group_values,
        ) = scope

        try:
            row_ids = (
                self._group_edit_service
                .get_group_row_ids(
                    group_columns=(
                        group_columns
                    ),
                    group_values=(
                        group_values
                    ),
                    enabled=True,
                )
            )

        except Exception as exc:
            AppMessageBox.warning(
                self,
                "Deshabilitar grupo",
                "No se pudo identificar "
                "la agrupacion.\n\n"
                f"{type(exc).__name__}: "
                f"{exc}",
            )
            return

        if not row_ids:
            return

        context_lines = []

        for column, value in zip(
            group_columns,
            group_values,
        ):
            label = (
                column
                .replace("_", " ")
                .title()
            )

            context_lines.append(
                f"{label}: {value}"
            )

        context = "\n".join(
            context_lines
        )

        annual_column = (
            self._workspace
            .module_config
            .annual_column
        )

        total = (
            row.get(
                annual_column
            )
            or ZERO
        )

        confirmed = ask_confirmation(
            self,
            "Deshabilitar agrupacion",
            f"{context}\n\n"
            f"Filas reales afectadas: "
            f"{len(row_ids):,}\n"
            f"Total del grupo: "
            f"US$ {total:,.2f}\n\n"
            "Todas estas filas dejaran de "
            "participar en Dashboard y "
            "Agrupaciones.\n\n"
            "Los importes NO se eliminaran. "
            "El cambio permanecera local "
            "hasta usar Aplicar cambios.",
            confirm_text=(
                "Deshabilitar grupo"
            ),
        )

        if not confirmed:
            return

        try:
            affected = (
                self._group_edit_service
                .set_group_enabled(
                    group_columns=(
                        group_columns
                    ),
                    group_values=(
                        group_values
                    ),
                    enabled=False,
                )
            )

        except Exception as exc:
            AppMessageBox.warning(
                self,
                "Deshabilitar grupo",
                "No se pudo deshabilitar "
                "la agrupacion.\n\n"
                f"{type(exc).__name__}: "
                f"{exc}",
            )
            return

        if not affected:
            return

        self.workspace_changed.emit()

        self.load_grouping()

        self.status_label.setText(
            "Agrupacion deshabilitada "
            "localmente: "
            f"{affected:,} filas reales. "
            "Los importes se conservaron."
        )

    def _go_to_start(self):
        self._go_to_column_index(
            0
        )

    def _go_to_annual(self):
        column_index = (
            self._find_column_index(
                self._workspace
                .module_config
                .annual_column
            )
        )

        if column_index is None:
            self.status_label.setText(
                "No se encontro la columna "
                "de total anual."
            )
            return

        self._go_to_column_index(
            column_index
        )

    def _go_to_column_index(
        self,
        column_index,
    ):
        if self.proxy_model.rowCount() == 0:
            return

        current = (
            self.table.currentIndex()
        )

        if current.isValid():
            row_index = current.row()
        else:
            row_index = 0

        target = self.proxy_model.index(
            row_index,
            column_index,
        )

        if not target.isValid():
            return

        self.table.setCurrentIndex(
            target
        )

        self.table.scrollTo(
            target,
            QAbstractItemView.ScrollHint.PositionAtCenter,
        )

        self._update_selected_context(
            target
        )

    def _find_column_index(
        self,
        column_name,
    ):
        for index in range(
            self.model.columnCount()
        ):
            if (
                self.model.column_name(
                    index
                )
                == column_name
            ):
                return index

        return None

    def _update_distribution_controls(
        self,
    ):
        config = (
            self._workspace
            .module_config
        )

        self._update_group_month_distribution_control()

        self.distribute_ceco_button.setEnabled(
            bool(
                self._workspace_ready
                and
                config.ceco_column
                and
                config.capabilities
                .ceco_distribution
            )
        )

        self.distribute_country_button.setEnabled(
            bool(
                self._workspace_ready
                and
                config.country_column
                and
                config.capabilities
                .country_distribution
            )
        )

    def _update_group_month_distribution_control(
        self,
        *_,
    ):
        config = (
            self._workspace
            .module_config
        )

        enabled = (
            self._workspace_ready
            and
            self._current_result
            is not None
            and
            config.capabilities
            .monthly_distribution
            and
            self.table.currentIndex()
            .isValid()
        )

        self.distribute_group_months_button.setEnabled(
            bool(
                enabled
            )
        )

    def _show_group_month_distribution(
        self,
    ):
        if not self._workspace_ready:
            return

        if self._current_result is None:
            return

        proxy_index = (
            self.table.currentIndex()
        )

        if not proxy_index.isValid():
            AppMessageBox.information(
                self,
                "Distribucion mensual",
                "Selecciona primero una fila "
                "de la agrupacion.",
            )
            return

        source_index = (
            self.proxy_model
            .mapToSource(
                proxy_index
            )
        )

        row = self.model.row_dict(
            source_index.row()
        )

        group_columns = tuple(
            self._current_result
            .group_columns
        )

        group_values = tuple(
            row.get(
                column
            )
            for column
            in group_columns
        )

        try:
            dialog = (
                MonthlyDistributionDialog(
                    row=row,
                    module_config=(
                        self._workspace
                        .module_config
                    ),
                    parent=self,
                )
            )

            if not dialog.exec():
                return

            preview = (
                self._group_monthly_distribution_service
                .apply(
                    group_columns=(
                        group_columns
                    ),
                    group_values=(
                        group_values
                    ),
                    percentages=(
                        dialog.percentages()
                    ),
                    annual_total=(
                        dialog.annual_total()
                    ),
                )
            )

        except Exception as exc:
            AppMessageBox.warning(
                self,
                "Distribucion mensual",
                "No se pudo distribuir "
                "el grupo.\n\n"
                f"{type(exc).__name__}: {exc}",
            )
            return

        self.workspace_changed.emit()

        self.load_grouping()

        self.status_label.setText(
            "Distribucion mensual del grupo "
            "aplicada localmente: "
            f"{preview.row_count:,} registros | "
            f"Total anual USD "
            f"{preview.current_total:,.2f} -> "
            f"{preview.target_total:,.2f}. "
            "BigQuery no ha sido modificado."
        )

    def _dimension_scope(
        self,
        dimension,
    ):
        if self._current_result is None:
            return (), ()

        current = (
            self.table.currentIndex()
        )

        if not current.isValid():
            return (), ()

        source_index = (
            self.proxy_model
            .mapToSource(
                current
            )
        )

        row = self.model.row_dict(
            source_index.row()
        )

        columns = []
        values = []

        for column in (
            self._current_result
            .group_columns
        ):
            if column == dimension:
                continue

            columns.append(
                column
            )

            values.append(
                row.get(
                    column
                )
            )

        return (
            tuple(columns),
            tuple(values),
        )

    def _show_dimension_distribution(
        self,
        dimension,
    ):
        if not dimension:
            return

        if not self._workspace_ready:
            return

        (
            scope_columns,
            scope_values,
        ) = self._dimension_scope(
            dimension
        )

        config = (
            self._workspace
            .module_config
        )

        if dimension == config.ceco_column:
            label = "CECO"

        elif (
            dimension
            == config.country_column
        ):
            label = "Pais"

        else:
            label = (
                dimension
                .replace("_", " ")
                .title()
            )

        try:
            dialog = (
                DimensionAllocationDialog(
                    service=(
                        self._dimension_allocation_service
                    ),
                    dimension=dimension,
                    dimension_label=label,
                    scope_columns=(
                        scope_columns
                    ),
                    scope_values=(
                        scope_values
                    ),
                    parent=self,
                )
            )

        except Exception as exc:
            self._show_edit_error(
                exc
            )
            return

        if not dialog.exec():
            return

        try:
            preview = (
                self._dimension_allocation_service
                .apply(
                    dimension=dimension,
                    percentages=(
                        dialog.percentages()
                    ),
                    scope_columns=(
                        scope_columns
                    ),
                    scope_values=(
                        scope_values
                    ),
                )
            )

        except Exception as exc:
            self._show_edit_error(
                exc
            )
            return

        self.workspace_changed.emit()

        self.load_grouping()

        self.status_label.setText(
            "Distribucion por "
            f"{label} aplicada localmente: "
            f"{preview.row_count:,} registros | "
            f"{preview.dimension_count:,} "
            "grupos | "
            f"US$ "
            f"{preview.current_total:,.2f}. "
            "BigQuery no ha sido modificado."
        )

    def _edit_group_cell(
        self,
        proxy_index,
    ):
        if not self._workspace_ready:
            return

        if self._current_result is None:
            return

        self._update_selected_context(
            proxy_index
        )

        source_index = (
            self.proxy_model
            .mapToSource(
                proxy_index
            )
        )

        column = self.model.column_name(
            source_index.column()
        )

        if (
            column
            not in self._workspace
            .module_config
            .amount_columns
        ):
            self.status_label.setText(
                "Solo los importes configurados "
                "para el modulo pueden modificarse."
            )
            return

        row = self.model.row_dict(
            source_index.row()
        )

        group_columns = tuple(
            self._current_result.group_columns
        )

        group_values = tuple(
            row.get(column_name)
            for column_name
            in group_columns
        )

        current_total = (
            row.get(column)
            or Decimal("0")
        )

        try:
            initial_preview = (
                self._group_edit_service
                .preview(
                    group_columns=group_columns,
                    group_values=group_values,
                    column=column,
                    target_total=current_total,
                )
            )

        except Exception as exc:
            self._show_edit_error(
                exc
            )
            return

        dialog = GroupEditDialog(
            initial_preview,
            self,
            annual_column=(
                self._workspace
                .module_config
                .annual_column
            ),
        )

        if not dialog.exec():
            return

        try:
            target = (
                dialog.target_total()
            )

            preview = (
                self._group_edit_service
                .preview(
                    group_columns=group_columns,
                    group_values=group_values,
                    column=column,
                    target_total=target,
                )
            )

            if (
                preview.target_total
                == preview.current_total
            ):
                self.status_label.setText(
                    "El nuevo total es igual "
                    "al total actual."
                )
                return

            self._group_edit_service.apply(
                group_columns=group_columns,
                group_values=group_values,
                column=column,
                target_total=target,
            )

        except Exception as exc:
            self._show_edit_error(
                exc
            )
            return

        self.workspace_changed.emit()

        self.load_grouping()

        self.status_label.setText(
            "Simulacion masiva aplicada: "
            f"{preview.row_count:,} registros | "
            f"{column.replace('_', ' ').upper()} | "
            f"{preview.current_total:,.2f} -> "
            f"{preview.target_total:,.2f} USD"
        )

    def show_change_summary(self):
        if not self._workspace.has_changes:
            AppMessageBox.information(
                self,
                "Resumen de cambios",
                "No existen cambios pendientes.",
            )
            return

        try:
            summary = (
                self._change_summary_service
                .build()
            )

        except Exception as exc:
            AppMessageBox.warning(
                self,
                "Resumen de cambios",
                f"No se pudo generar el resumen: "
                f"{type(exc).__name__}: {exc}",
            )
            return

        dialog = ChangeSummaryDialog(
            summary,
            self,
            module_label=(
                self._workspace
                .module_config
                .label
            ),
        )

        dialog.exec()

    def undo_last(self):
        if not self._workspace.has_changes:
            return

        changed = (
            self._workspace.undo_last()
        )

        if not changed:
            return

        self.workspace_changed.emit()

        self.load_grouping()

        self.status_label.setText(
            "Ultima operacion deshecha."
        )

    def discard_all(self):
        if not self._workspace.has_changes:
            return

        result = AppMessageBox.question(
            self,
            "Descartar cambios",
            "Se descartaran todos los "
            "cambios de la simulacion local.\n\n"
            "¿Desea continuar?",
            AppMessageBox.StandardButton.Yes
            |
            AppMessageBox.StandardButton.No,
            AppMessageBox.StandardButton.No,
        )

        if (
            result
            != AppMessageBox.StandardButton.Yes
        ):
            return

        self._workspace.discard_all()

        self.workspace_changed.emit()

        self.load_grouping()

        self.status_label.setText(
            "Todos los cambios locales "
            "fueron descartados."
        )

    def _update_change_controls(self):
        if not self._workspace.is_loaded:
            rows = 0
            fields = 0
            difference = ZERO
            variation_percent = None

        else:
            try:
                summary = (
                    self._change_summary_service
                    .build()
                )

                rows = (
                    summary.pending_rows
                )

                fields = (
                    summary.pending_fields
                )

                difference = (
                    summary.difference
                )

                variation_percent = (
                    summary.variation_percent
                )

            except Exception:
                rows = (
                    self._workspace
                    .pending_row_count
                )

                fields = (
                    self._workspace
                    .pending_change_count
                )

                difference = ZERO
                variation_percent = None

        self.pending_label.setText(
            f"Cambios pendientes: "
            f"{rows:,} filas / "
            f"{fields:,} campos"
        )

        self._set_variation_badge(
            difference,
            variation_percent,
        )

        has_changes = (
            rows > 0
        )

        self.view_changes_button.setEnabled(
            has_changes
        )

        self.undo_button.setEnabled(
            has_changes
        )

        self.discard_button.setEnabled(
            has_changes
        )

    def _set_variation_badge(
        self,
        difference,
        variation_percent,
    ):
        if difference > ZERO:
            color = "#B42318"
            background = "#FEE4E2"
            sign = "+"

        elif difference < ZERO:
            color = "#067647"
            background = "#D1FADF"
            sign = ""

        else:
            color = "#475467"
            background = "#F2F4F7"
            sign = ""

        if difference < ZERO:
            amount_text = (
                f"-US$ "
                f"{abs(difference):,.2f}"
            )
        else:
            amount_text = (
                f"{sign}US$ "
                f"{difference:,.2f}"
            )

        if variation_percent is None:
            percent_text = ""
        else:
            percent_sign = (
                "+"
                if variation_percent > ZERO
                else ""
            )

            percent_text = (
                f" ({percent_sign}"
                f"{variation_percent:,.2f} %)"
            )

        self.variation_label.setText(
            "Variacion total: "
            + amount_text
            + percent_text
        )

        self.variation_label.setStyleSheet(
            "QLabel {"
            f"background-color: {background};"
            f"color: {color};"
            "border-radius: 6px;"
            "padding: 7px 10px;"
            "font-weight: 700;"
            "}"
        )

    def _show_edit_error(
        self,
        error,
    ):
        if isinstance(
            error,
            PresupuestoGroupEditError,
        ):
            message = str(error)

        elif isinstance(
            error,
            ValueError,
        ):
            message = str(error)

        else:
            message = (
                f"{type(error).__name__}: "
                f"{error}"
            )

        self.status_label.setText(
            "No se pudo aplicar "
            "la simulacion: "
            + message
        )

        AppMessageBox.warning(
            self,
            "Cambio no valido",
            message,
        )
