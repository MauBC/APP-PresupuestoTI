from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QLabel,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.models.opex_smart_import import (
    OpexSmartImportSheetOverride,
)
from app.ui.dialogs.app_message_box import (
    AppMessageBox,
)


class OpexSmartDecisionDialog(
    QDialog
):
    def __init__(
        self,
        *,
        result,
        parent=None,
    ):
        super().__init__(
            parent
        )

        self._result = result
        self._overrides = ()
        self._controls = {}

        self.setObjectName(
            "opexSmartDecisionDialog"
        )

        self.setWindowTitle(
            "Revisar decisiones OPEX"
        )

        self.resize(
            840,
            620,
        )

        self.setMinimumSize(
            720,
            520,
        )

        self._apply_style()
        self._setup_ui()

    def overrides(
        self,
    ):
        return tuple(
            self._overrides
        )

    def _apply_style(
        self,
    ):
        self.setStyleSheet(
            """
            QDialog#opexSmartDecisionDialog {
                background-color: #FFFFFF;
                color: #1F2937;
            }

            QLabel#title {
                font-size: 20px;
                font-weight: 700;
                color: #173F35;
            }

            QLabel#subtitle {
                color: #667085;
                font-size: 12px;
            }

            QLabel#hint {
                background-color: #FFF7ED;
                color: #9A3412;
                border: 1px solid #FED7AA;
                border-radius: 7px;
                padding: 9px 12px;
            }

            QTabWidget::pane {
                border: 1px solid #D7E5DD;
                border-radius: 7px;
                background-color: #FFFFFF;
            }

            QTabBar::tab {
                padding: 8px 18px;
                margin-right: 2px;
                background-color: #F2F4F7;
                border: 1px solid #D0D5DD;
                border-bottom: none;
            }

            QTabBar::tab:selected {
                background-color: #EEF7F1;
                color: #2F7650;
                font-weight: 700;
            }

            QWidget#decisionSheetPage,
            QScrollArea#decisionScroll,
            QWidget#decisionScrollViewport,
            QWidget#decisionScrollContent {
                background-color: #FFFFFF;
                color: #1F2937;
            }

            QScrollArea#decisionScroll {
                border: none;
            }

            QLabel {
                background-color: transparent;
                color: #344054;
            }

            QGroupBox {
                background-color: #FFFFFF;
                font-weight: 700;
                color: #173F35;
                border: 1px solid #D7E5DD;
                border-radius: 7px;
                margin-top: 14px;
                padding-top: 14px;
            }

            QGroupBox::title {
                background-color: #FFFFFF;
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 6px;
            }

            QComboBox {
                min-height: 34px;
                border: 1px solid #D0D5DD;
                border-radius: 6px;
                padding: 0 9px;
                background-color: #FFFFFF;
                color: #1F2937;
                selection-background-color: #DCEFE4;
                selection-color: #173F35;
            }

            QComboBox:focus {
                border: 1px solid #2F7650;
            }

            QComboBox QAbstractItemView {
                background-color: #FFFFFF;
                color: #1F2937;
                border: 1px solid #D0D5DD;
                selection-background-color: #DCEFE4;
                selection-color: #173F35;
                outline: 0;
            }

            QComboBox QAbstractItemView::item {
                min-height: 30px;
                padding: 4px 8px;
            }

            QComboBox QAbstractItemView::item:hover {
                background-color: #EEF7F1;
                color: #173F35;
            }

            QDialogButtonBox QPushButton {
                min-width: 120px;
                min-height: 34px;
                border-radius: 6px;
                padding: 0 14px;
            }
            """
        )

    def _setup_ui(
        self,
    ):
        root = QVBoxLayout(
            self
        )

        root.setContentsMargins(
            24,
            22,
            24,
            22,
        )

        root.setSpacing(
            12
        )

        title = QLabel(
            "Revisar decisiones"
        )

        title.setObjectName(
            "title"
        )

        subtitle = QLabel(
            "La aplicacion aplico valores seguros "
            "cuando fue posible. Cuando existan "
            "varias alternativas oficiales debes "
            "elegir la correcta antes de importar."
        )

        subtitle.setObjectName(
            "subtitle"
        )

        subtitle.setWordWrap(
            True
        )

        hint = QLabel(
            "Solo se muestran alternativas "
            "oficiales encontradas en los maestros. "
            "Al aplicar una decision se recalcularan "
            "las filas y los importes."
        )

        hint.setObjectName(
            "hint"
        )

        hint.setWordWrap(
            True
        )

        root.addWidget(
            title
        )

        root.addWidget(
            subtitle
        )

        root.addWidget(
            hint
        )

        self.tabs = QTabWidget()

        root.addWidget(
            self.tabs,
            1,
        )

        decisions = {
            decision.sheet_name:
                decision
            for decision
            in self._result.decisions
        }

        for review in (
            self._result.review_options
        ):
            decision = decisions.get(
                review.sheet_name
            )

            page = self._build_sheet_page(
                review=review,
                decision=decision,
            )

            self.tabs.addTab(
                page,
                review.sheet_name,
            )

        buttons = QDialogButtonBox(
            QDialogButtonBox
            .StandardButton.Cancel
            |
            QDialogButtonBox
            .StandardButton.Save
        )

        save_button = (
            buttons.button(
                QDialogButtonBox
                .StandardButton.Save
            )
        )

        save_button.setText(
            "Aplicar decisiones"
        )

        cancel_button = (
            buttons.button(
                QDialogButtonBox
                .StandardButton.Cancel
            )
        )

        cancel_button.setText(
            "Cancelar"
        )

        buttons.accepted.connect(
            self._apply
        )

        buttons.rejected.connect(
            self.reject
        )

        root.addWidget(
            buttons
        )

    def _build_sheet_page(
        self,
        *,
        review,
        decision,
    ):
        container = QWidget()

        container.setObjectName(
            "decisionSheetPage"
        )

        outer = QVBoxLayout(
            container
        )

        outer.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        scroll = QScrollArea()

        scroll.setObjectName(
            "decisionScroll"
        )

        scroll.viewport().setObjectName(
            "decisionScrollViewport"
        )

        scroll.setWidgetResizable(
            True
        )

        scroll.setFrameShape(
            QFrame.Shape.NoFrame
        )

        content = QWidget()

        content.setObjectName(
            "decisionScrollContent"
        )

        layout = QVBoxLayout(
            content
        )

        layout.setContentsMargins(
            18,
            18,
            18,
            18,
        )

        layout.setSpacing(
            14
        )

        general = QGroupBox(
            "Configuracion"
        )

        form = QFormLayout(
            general
        )

        form.setHorizontalSpacing(
            18
        )

        form.setVerticalSpacing(
            10
        )

        account_combo = QComboBox()

        account_combo.addItem(
            "Selecciona una opcion oficial...",
            None,
        )

        for option in (
            review.account_options
        ):
            label = (
                f"{option.categoria_gasto}"
                " | "
                f"{option.nombre_cuenta}"
                " | "
                f"{option.atributo_2}"
            )

            account_combo.addItem(
                label,
                option,
            )

        self._select_account(
            account_combo,
            decision,
        )

        distribution_combo = (
            QComboBox()
        )

        for mode in (
            review.distribution_modes
        ):
            distribution_combo.addItem(
                mode,
                mode,
            )

        self._select_distribution(
            distribution_combo,
            decision,
        )

        form.addRow(
            "Cuenta / Atributo 2",
            account_combo,
        )

        form.addRow(
            "Distribucion",
            distribution_combo,
        )

        layout.addWidget(
            general
        )

        cebe_controls = {}

        if review.cebe_choices:
            cebe_group = QGroupBox(
                "CEBE ambiguos"
            )

            cebe_form = QFormLayout(
                cebe_group
            )

            cebe_form.setHorizontalSpacing(
                18
            )

            cebe_form.setVerticalSpacing(
                9
            )

            selected_cebes = {}

            if decision is not None:
                selected_cebes = {
                    item.centro_beneficio:
                        item.tipo_servicio_cg
                    for item
                    in decision.cebe_decisions
                }

            for choice in (
                review.cebe_choices
            ):
                combo = QComboBox()

                for option in (
                    choice.options
                ):
                    label = (
                        option.tipo_servicio_cg
                    )

                    if option.desc_cebe:
                        label += (
                            " — "
                            + option.desc_cebe
                        )

                    combo.addItem(
                        label,
                        option,
                    )

                expected = (
                    selected_cebes.get(
                        choice
                        .centro_beneficio
                    )
                )

                if expected is not None:
                    for index in range(
                        combo.count()
                    ):
                        option = (
                            combo.itemData(
                                index
                            )
                        )

                        if (
                            option
                            .tipo_servicio_cg
                            == expected
                        ):
                            combo.setCurrentIndex(
                                index
                            )

                            break

                cebe_form.addRow(
                    choice.centro_beneficio,
                    combo,
                )

                cebe_controls[
                    choice
                    .centro_beneficio
                ] = combo

            layout.addWidget(
                cebe_group
            )

        else:
            no_ambiguity = QLabel(
                "Esta hoja no tiene CEBE "
                "ambiguos."
            )

            no_ambiguity.setAlignment(
                Qt.AlignmentFlag.AlignCenter
            )

            layout.addWidget(
                no_ambiguity
            )

        layout.addStretch()

        scroll.setWidget(
            content
        )

        outer.addWidget(
            scroll
        )

        self._controls[
            review.sheet_name
        ] = {
            "review": review,
            "account":
                account_combo,
            "distribution":
                distribution_combo,
            "cebes":
                cebe_controls,
        }

        return container

    @staticmethod
    def _select_account(
        combo,
        decision,
    ):
        if decision is None:
            combo.setCurrentIndex(
                0
            )
            return

        for index in range(
            combo.count()
        ):
            option = combo.itemData(
                index
            )

            if option is None:
                continue

            if (
                option.nombre_cuenta
                == decision.account_name
                and
                option.atributo_2
                == decision.atributo_2
            ):
                combo.setCurrentIndex(
                    index
                )
                return

        combo.setCurrentIndex(
            0
        )

    @staticmethod
    def _select_distribution(
        combo,
        decision,
    ):
        if decision is None:
            return

        for index in range(
            combo.count()
        ):
            if (
                combo.itemData(
                    index
                )
                ==
                decision.distribution_mode
            ):
                combo.setCurrentIndex(
                    index
                )

                return

    def _apply(
        self,
    ):
        overrides = []

        for (
            sheet_name,
            controls,
        ) in self._controls.items():
            account = (
                controls["account"]
                .currentData()
            )

            if account is None:
                AppMessageBox.warning(
                    self,
                    "Decision pendiente",
                    (
                        "Selecciona una opcion "
                        "oficial de cuenta para "
                        f"{sheet_name}."
                    ),
                )
                return

            distribution_mode = (
                controls[
                    "distribution"
                ]
                .currentData()
            )

            if distribution_mode is None:
                AppMessageBox.warning(
                    self,
                    "Decision pendiente",
                    (
                        "Selecciona una "
                        "distribucion para "
                        f"{sheet_name}."
                    ),
                )
                return

            cebes = tuple(
                combo.currentData()
                for combo
                in controls[
                    "cebes"
                ].values()
            )

            overrides.append(
                OpexSmartImportSheetOverride(
                    sheet_name=(
                        sheet_name
                    ),
                    account=account,
                    distribution_mode=(
                        distribution_mode
                    ),
                    cebe_selections=(
                        cebes
                    ),
                )
            )

        self._overrides = tuple(
            overrides
        )

        self.accept()
