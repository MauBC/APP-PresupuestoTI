from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QLabel,
    QLayout,
    QScrollArea,
    QSizePolicy,
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
                background-color: #FFFFFF;
                color: #344054;
                border: 1px solid #D0D5DD;
            }
            QPushButton#applyDecisions {
                background-color: #2F7650;
                color: #FFFFFF;
                border: 1px solid #2F7650;
                font-weight: 700;
            }
            QPushButton#applyDecisions:disabled {
                background-color: #F2F4F7;
                color: #667085;
                border: 1px solid #D0D5DD;
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

        self.pending_label = QLabel()
        self.pending_label.setWordWrap(True)
        root.addWidget(self.pending_label)

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
        self.save_button = save_button
        save_button.setObjectName("applyDecisions")

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
        for controls in self._controls.values():
            for combo in (controls["account"], controls["distribution"], *controls["cebes"].values()):
                combo.currentIndexChanged.connect(self._update_pending)
        self._update_pending()

    def _update_pending(self):
        total = 0
        for index, (sheet_name, controls) in enumerate(self._controls.items()):
            combos = (controls["account"], controls["distribution"], *controls["cebes"].values())
            pending = sum(combo.currentData() is None for combo in combos)
            total += pending
            self.tabs.setTabText(index, f"{sheet_name} ({pending} pendientes)" if pending else sheet_name)
        self.pending_label.setText(
            f"Faltan {total} decisiones. Revisa las pestañas indicadas."
            if total else "Todas las decisiones están completas. Puedes aplicar y recalcular."
        )
        self.save_button.setEnabled(total == 0 and bool(self._controls))

    @staticmethod
    def _make_readable_combo(combo, form):
        combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        combo.setMinimumContentsLength(20)
        detail = QLabel()
        detail.setWordWrap(True)
        detail.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        detail.setTextFormat(Qt.TextFormat.PlainText)
        detail.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        def update_detail():
            text = combo.currentData(Qt.ItemDataRole.ToolTipRole) or combo.currentText()
            detail.setText(text)
            combo.setToolTip(text)

        combo.currentIndexChanged.connect(update_detail)
        update_detail()
        form.addRow(detail)

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
        layout.setSizeConstraint(QLayout.SizeConstraint.SetMinAndMaxSize)

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
        self._make_readable_combo(account_combo, form)

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
                        item
                    for item
                    in decision.cebe_decisions
                }

            for choice in (
                review.cebe_choices
            ):
                combo = QComboBox()
                combo.addItem("Selecciona un CEBE oficial...", None)

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
                    label += f" | {option.region_cg} / {option.sede_cg}"

                    combo.addItem(
                        label,
                        option,
                    )
                    combo.setItemData(
                        combo.count() - 1,
                        f"{option.desc_cebe}\n"
                        f"Macroservicio: {option.macroservicio_cg} | Tipo: {option.tipo_servicio_cg}\n"
                        f"Región: {option.region_cg} | Sede: {option.sede_cg}\n"
                        f"Segmentación: {option.segmentacion}",
                        Qt.ItemDataRole.ToolTipRole,
                    )

                expected = (
                    selected_cebes.get(
                        choice
                        .centro_beneficio
                    )
                )

                if expected is not None:
                    exact = expected.selected_option
                    candidates = [
                        index for index in range(1, combo.count())
                        if (combo.itemData(index) == exact if exact is not None else
                            combo.itemData(index).tipo_servicio_cg == expected.tipo_servicio_cg)
                    ]
                    if len(candidates) == 1:
                        combo.setCurrentIndex(candidates[0])

                cebe_form.addRow(
                    choice.centro_beneficio,
                    combo,
                )
                self._make_readable_combo(combo, cebe_form)

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

        candidates = []
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
                and (decision.categoria_gasto is None or
                     option.categoria_gasto == decision.categoria_gasto)
            ):
                candidates.append(index)
        combo.setCurrentIndex(candidates[0] if len(candidates) == 1 else 0)

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
        self._update_pending()
        if not self.save_button.isEnabled():
            return
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
