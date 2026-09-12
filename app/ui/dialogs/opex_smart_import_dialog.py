from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from app.services.opex_smart_import_preparation_service import (
    OpexSmartImportPreparationService,
)
from app.ui.dialogs.app_message_box import (
    AppMessageBox,
)
from app.ui.workers.opex_smart_import_worker import (
    OpexSmartImportWorker,
)


class OpexSmartImportDialog(
    QDialog
):
    def __init__(
        self,
        *,
        actor,
        parent=None,
    ):
        super().__init__(
            parent
        )

        self._actor = str(
            actor
            if actor is not None
            else ""
        ).strip()

        self._result = None
        self._worker = None

        self._masters_directory = (
            Path(__file__)
            .resolve()
            .parents[3]
            / "maestros"
        )

        self.setObjectName(
            "opexSmartImportDialog"
        )

        self.setWindowTitle(
            "Importacion inteligente OPEX"
        )

        self.setMinimumWidth(
            760
        )

        self.setMinimumHeight(
            600
        )

        self._apply_style()
        self._setup_ui()

    def rows(
        self,
    ):
        if self._result is None:
            return ()

        return tuple(
            self._result.rows
        )

    def source_name(
        self,
    ) -> str:
        if self._result is None:
            return ""

        return (
            self._result.source_name
        )

    def _apply_style(
        self,
    ):
        self.setStyleSheet(
            """
            QDialog#opexSmartImportDialog {
                background-color: #FFFFFF;
                color: #1F2937;
            }

            QLabel#dialogTitle {
                font-size: 22px;
                font-weight: 700;
                color: #173F35;
            }

            QLabel#dialogSubtitle {
                color: #667085;
                font-size: 12px;
            }

            QLabel#sectionTitle {
                color: #173F35;
                font-size: 13px;
                font-weight: 700;
            }

            QLabel#periodBadge {
                background-color: #EEF7F1;
                color: #2F7650;
                border: 1px solid #CFE3D6;
                border-radius: 6px;
                padding: 6px 10px;
                font-weight: 700;
            }

            QFrame#summaryCard {
                background-color: #F8FAF9;
                border: 1px solid #D7E5DD;
                border-radius: 9px;
            }

            QLabel#summaryText {
                color: #344054;
                font-size: 12px;
            }

            QLabel#totalUsd {
                color: #173F35;
                font-size: 18px;
                font-weight: 700;
            }

            QLineEdit {
                min-height: 34px;
                border: 1px solid #D0D5DD;
                border-radius: 6px;
                padding: 0 10px;
                background-color: #FFFFFF;
            }

            QLineEdit:focus {
                border: 1px solid #2F7650;
            }

            QPushButton#primaryButton {
                background-color: #2F7650;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 9px 18px;
                font-weight: 700;
            }

            QPushButton#primaryButton:hover {
                background-color: #286544;
            }

            QPushButton#primaryButton:disabled {
                background-color: #D0D5DD;
                color: #667085;
            }

            QPushButton#secondaryButton {
                background-color: #FFFFFF;
                color: #344054;
                border: 1px solid #D0D5DD;
                border-radius: 6px;
                padding: 9px 16px;
            }

            QPushButton#secondaryButton:hover {
                background-color: #F8FAFC;
            }

            QPushButton#secondaryButton:disabled {
                color: #98A2B3;
                background-color: #F2F4F7;
            }

            QPlainTextEdit {
                background-color: #F8FAF9;
                border: 1px solid #D7E5DD;
                border-radius: 7px;
                padding: 8px;
                font-family: Consolas;
                font-size: 11px;
            }
            """
        )

    def _setup_ui(
        self,
    ):
        layout = QVBoxLayout(
            self
        )

        layout.setContentsMargins(
            26,
            24,
            26,
            24,
        )

        layout.setSpacing(
            14
        )

        title = QLabel(
            "Importacion inteligente OPEX"
        )

        title.setObjectName(
            "dialogTitle"
        )

        subtitle = QLabel(
            "Carga el formato simplificado. "
            "La aplicacion resolvera maestros, "
            "CECO, periodizacion y tipo de cambio "
            "antes de agregar las filas al Workspace."
        )

        subtitle.setObjectName(
            "dialogSubtitle"
        )

        subtitle.setWordWrap(
            True
        )

        layout.addWidget(
            title
        )

        layout.addWidget(
            subtitle
        )

        file_title = QLabel(
            "Archivo"
        )

        file_title.setObjectName(
            "sectionTitle"
        )

        layout.addWidget(
            file_title
        )

        file_layout = QHBoxLayout()

        self.file_input = QLineEdit()

        self.file_input.setReadOnly(
            True
        )

        self.file_input.setPlaceholderText(
            "Selecciona PLANTILLAOPEX.xlsx "
            "o un archivo compatible..."
        )

        self._browse_button = QPushButton(
            "Examinar..."
        )

        self._browse_button.setObjectName(
            "secondaryButton"
        )

        self._browse_button.clicked.connect(
            self._browse_file
        )

        file_layout.addWidget(
            self.file_input,
            1,
        )

        file_layout.addWidget(
            self._browse_button
        )

        layout.addLayout(
            file_layout
        )

        context_title = QLabel(
            "Datos de insercion"
        )

        context_title.setObjectName(
            "sectionTitle"
        )

        layout.addWidget(
            context_title
        )

        context_grid = QGridLayout()

        context_grid.setHorizontalSpacing(
            14
        )

        context_grid.setVerticalSpacing(
            6
        )

        context_grid.addWidget(
            QLabel("Origen"),
            0,
            0,
        )

        context_grid.addWidget(
            QLabel("Presupuestador"),
            0,
            1,
        )

        context_grid.addWidget(
            QLabel("Periodo"),
            0,
            2,
        )

        self.origin_input = QLineEdit()

        self.origin_input.setPlaceholderText(
            "Ej. PB, Local, TI..."
        )

        self.budgeter_input = QLineEdit()

        self.budgeter_input.setPlaceholderText(
            "Nombre del presupuestador"
        )

        period = QLabel(
            "2027 PB"
        )

        period.setObjectName(
            "periodBadge"
        )

        period.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        context_grid.addWidget(
            self.origin_input,
            1,
            0,
        )

        context_grid.addWidget(
            self.budgeter_input,
            1,
            1,
        )

        context_grid.addWidget(
            period,
            1,
            2,
        )

        context_grid.setColumnStretch(
            0,
            1,
        )

        context_grid.setColumnStretch(
            1,
            2,
        )

        layout.addLayout(
            context_grid
        )

        summary_title = QLabel(
            "Resumen"
        )

        summary_title.setObjectName(
            "sectionTitle"
        )

        layout.addWidget(
            summary_title
        )

        summary_card = QFrame()

        summary_card.setObjectName(
            "summaryCard"
        )

        summary_layout = QVBoxLayout(
            summary_card
        )

        summary_layout.setContentsMargins(
            16,
            14,
            16,
            14,
        )

        summary_layout.setSpacing(
            7
        )

        self.summary_label = QLabel(
            "Selecciona un archivo y completa "
            "Origen y Presupuestador."
        )

        self.summary_label.setObjectName(
            "summaryText"
        )

        self.summary_label.setWordWrap(
            True
        )

        self.total_usd_label = QLabel(
            "Equivalente total USD: -"
        )

        self.total_usd_label.setObjectName(
            "totalUsd"
        )

        summary_layout.addWidget(
            self.summary_label
        )

        summary_layout.addWidget(
            self.total_usd_label
        )

        layout.addWidget(
            summary_card
        )

        self.details = QPlainTextEdit()

        self.details.setReadOnly(
            True
        )

        self.details.setVisible(
            False
        )

        self.details.setMinimumHeight(
            170
        )

        layout.addWidget(
            self.details,
            1,
        )

        actions = QHBoxLayout()

        self.analyze_button = QPushButton(
            "Analizar plantilla"
        )

        self.analyze_button.setObjectName(
            "secondaryButton"
        )

        self.review_button = QPushButton(
            "Revisar decisiones"
        )

        self.review_button.setObjectName(
            "secondaryButton"
        )

        self.review_button.setEnabled(
            False
        )

        self.import_button = QPushButton(
            "Importar"
        )

        self.import_button.setObjectName(
            "primaryButton"
        )

        self.import_button.setEnabled(
            False
        )

        self._cancel_button = QPushButton(
            "Cancelar"
        )

        self._cancel_button.setObjectName(
            "secondaryButton"
        )

        self.analyze_button.clicked.connect(
            self._analyze
        )

        self.review_button.clicked.connect(
            self._toggle_details
        )

        self.import_button.clicked.connect(
            self._accept_import
        )

        self._cancel_button.clicked.connect(
            self.reject
        )

        actions.addWidget(
            self.analyze_button
        )

        actions.addWidget(
            self.review_button
        )

        actions.addStretch()

        actions.addWidget(
            self._cancel_button
        )

        actions.addWidget(
            self.import_button
        )

        layout.addLayout(
            actions
        )

        self.file_input.textChanged.connect(
            self._invalidate_preview
        )

        self.origin_input.textChanged.connect(
            self._invalidate_preview
        )

        self.budgeter_input.textChanged.connect(
            self._invalidate_preview
        )

    def _browse_file(
        self,
    ):
        path, _ = (
            QFileDialog
            .getOpenFileName(
                self,
                "Seleccionar plantilla inteligente OPEX",
                "",
                (
                    "Excel (*.xlsx *.xlsm);;"
                    "Todos los archivos (*.*)"
                ),
            )
        )

        if path:
            self.file_input.setText(
                path
            )

    def _invalidate_preview(
        self,
        *_,
    ):
        if (
            self._worker is not None
            and
            self._worker.isRunning()
        ):
            return

        self._result = None

        self.import_button.setEnabled(
            False
        )

        self.review_button.setEnabled(
            False
        )

        self.details.clear()

        self.details.setVisible(
            False
        )

        self.review_button.setText(
            "Revisar decisiones"
        )

        self.summary_label.setText(
            "Pendiente de analisis."
        )

        self.total_usd_label.setText(
            "Equivalente total USD: -"
        )

    def _request_values(
        self,
    ):
        source = (
            self.file_input
            .text()
            .strip()
        )

        origin = (
            self.origin_input
            .text()
            .strip()
        )

        budgeter = (
            self.budgeter_input
            .text()
            .strip()
        )

        (
            OpexSmartImportPreparationService
            .validate_request(
                source_path=source,
                origin=origin,
                budgeter=budgeter,
                actor=self._actor,
            )
        )

        return (
            source,
            origin,
            budgeter,
        )

    def _set_busy(
        self,
        busy,
    ):
        enabled = not busy

        self.file_input.setEnabled(
            enabled
        )

        self.origin_input.setEnabled(
            enabled
        )

        self.budgeter_input.setEnabled(
            enabled
        )

        self._browse_button.setEnabled(
            enabled
        )

        self.analyze_button.setEnabled(
            enabled
        )

        self._cancel_button.setEnabled(
            enabled
        )

        if busy:
            self.import_button.setEnabled(
                False
            )

            self.review_button.setEnabled(
                False
            )

    def _analyze(
        self,
    ):
        try:
            (
                source,
                origin,
                budgeter,
            ) = self._request_values()

        except Exception as exc:
            AppMessageBox.warning(
                self,
                "Datos incompletos",
                str(exc),
            )

            return

        if (
            self._worker is not None
            and
            self._worker.isRunning()
        ):
            return

        self._result = None

        self.summary_label.setText(
            "Analizando plantilla, maestros "
            "y tipo de cambio..."
        )

        self.total_usd_label.setText(
            "Equivalente total USD: calculando..."
        )

        self.details.clear()

        self.details.setVisible(
            False
        )

        self.review_button.setText(
            "Revisar decisiones"
        )

        self._set_busy(
            True
        )

        service = (
            OpexSmartImportPreparationService(
                masters_directory=(
                    self._masters_directory
                )
            )
        )

        worker = (
            OpexSmartImportWorker(
                service=service,
                source_path=source,
                origin=origin,
                budgeter=budgeter,
                actor=self._actor,
                parent=self,
            )
        )

        self._worker = worker

        worker.succeeded.connect(
            self._analysis_succeeded
        )

        worker.failed.connect(
            self._analysis_failed
        )

        worker.finished.connect(
            self._analysis_finished
        )

        worker.start()

    def _analysis_succeeded(
        self,
        result,
    ):
        self._result = result

        self.summary_label.setText(
            "✓ "
            f"{result.budget_count} "
            "presupuestos encontrados\n"
            "✓ "
            f"{len(result.rows):,} "
            "filas a generar\n"
            "✓ Maestros CUENTA / CEBE / "
            "RECUPERABLES cargados\n"
            "✓ TC 2027 cargado\n"
            "✓ "
            f"{result.auto_cebe_count} "
            "CEBE ambiguos resueltos "
            "automaticamente"
        )

        self.total_usd_label.setText(
            "Equivalente total USD: "
            f"US$ {result.total_usd:,.2f}"
        )

        self.details.setPlainText(
            self._decision_details(
                result
            )
        )

        self.review_button.setEnabled(
            True
        )

        self.import_button.setEnabled(
            True
        )

        self.import_button.setText(
            "Importar "
            f"{len(result.rows):,} filas"
        )

    def _analysis_failed(
        self,
        message,
    ):
        self._result = None

        self.summary_label.setText(
            "El analisis fallo. "
            "No se agregaron filas."
        )

        self.total_usd_label.setText(
            "Equivalente total USD: -"
        )

        AppMessageBox.warning(
            self,
            "No se pudo analizar la plantilla",
            "La importacion inteligente "
            "no pudo prepararse.\n\n"
            f"{message}",
        )

    def _analysis_finished(
        self,
    ):
        self._set_busy(
            False
        )

        worker = self._worker

        self._worker = None

        if worker is not None:
            worker.deleteLater()

    @staticmethod
    def _decision_details(
        result,
    ) -> str:
        lines = [
            "RESOLUCIONES AUTOMATICAS",
            "=" * 64,
            "",
        ]

        for decision in (
            result.decisions
        ):
            lines.extend(
                [
                    f"[{decision.sheet_name}]",
                    (
                        "Cuenta: "
                        f"{decision.account_name}"
                    ),
                    (
                        "Atributo 2: "
                        f"{decision.atributo_2}"
                    ),
                    (
                        "Distribucion: "
                        f"{decision.distribution_mode}"
                    ),
                ]
            )

            if decision.cebe_decisions:
                lines.append(
                    "CEBE:"
                )

                for cebe in (
                    decision.cebe_decisions
                ):
                    lines.append(
                        "  "
                        f"{cebe.centro_beneficio}"
                        " -> "
                        f"{cebe.tipo_servicio_cg}"
                    )

            else:
                lines.append(
                    "CEBE: sin ambiguedades"
                )

            lines.append(
                ""
            )

        lines.extend(
            [
                "RESUMEN",
                "=" * 64,
                (
                    "Total equivalente USD: "
                    f"US$ {result.total_usd:,.2f}"
                ),
                "",
                "Filas por pais:",
            ]
        )

        for (
            key,
            value,
        ) in result.country_counts:
            lines.append(
                f"  {key}: {value:,}"
            )

        lines.append(
            ""
        )

        lines.append(
            "Moneda de facturacion:"
        )

        for (
            key,
            value,
        ) in (
            result
            .invoice_currency_counts
        ):
            lines.append(
                f"  {key}: {value:,} filas"
            )

        lines.extend(
            [
                "",
                "Nota:",
                (
                    "Los valores fueron preparados "
                    "en memoria. BigQuery aun no "
                    "ha sido modificado."
                ),
            ]
        )

        return "\n".join(
            lines
        )

    def _toggle_details(
        self,
    ):
        visible = (
            self.details
            .isVisible()
        )

        self.details.setVisible(
            not visible
        )

        self.review_button.setText(
            (
                "Ocultar decisiones"
                if not visible
                else "Revisar decisiones"
            )
        )

    def _accept_import(
        self,
    ):
        if (
            self._result is None
            or
            not self._result.rows
        ):
            AppMessageBox.warning(
                self,
                "Importacion inteligente",
                "Analiza primero la plantilla.",
            )

            return

        self.accept()

    def closeEvent(
        self,
        event,
    ):
        if (
            self._worker is not None
            and
            self._worker.isRunning()
        ):
            event.ignore()
            return

        super().closeEvent(
            event
        )
