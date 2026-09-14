from PySide6.QtCore import (
    QEvent,
    QObject,
    Qt,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QTableView,
)


def resolve_frozen_columns(
    *,
    columns,
    preferred_columns,
):
    available = set(
        columns
        or ()
    )

    seen = set()
    result = []

    for column in (
        preferred_columns
        or ()
    ):
        column = str(
            column
        ).strip()

        if not column:
            continue

        if column in seen:
            continue

        if column not in available:
            continue

        seen.add(
            column
        )

        result.append(
            column
        )

    return tuple(
        result
    )


class FrozenColumnsController(
    QObject
):
    def __init__(
        self,
        *,
        main_table,
        preferred_columns,
        parent=None,
    ):
        super().__init__(
            parent
            if parent is not None
            else main_table
        )

        self._main_table = (
            main_table
        )

        self._preferred_columns = tuple(
            preferred_columns
            or ()
        )

        self._columns = ()
        self._frozen_columns = ()
        self._frozen_indexes = ()

        self._syncing_width = False

        self.view = QTableView(
            main_table
        )

        self.view.setObjectName(
            "frozenBudgetTable"
        )

        self.view.setModel(
            main_table.model()
        )

        self.view.setSelectionModel(
            main_table.selectionModel()
        )

        self.view.setAlternatingRowColors(
            main_table
            .alternatingRowColors()
        )

        self.view.setSelectionBehavior(
            QAbstractItemView
            .SelectionBehavior
            .SelectRows
        )

        self.view.setSelectionMode(
            QAbstractItemView
            .SelectionMode
            .SingleSelection
        )

        self.view.setEditTriggers(
            QAbstractItemView
            .EditTrigger
            .NoEditTriggers
        )

        self.view.setHorizontalScrollMode(
            QAbstractItemView
            .ScrollMode
            .ScrollPerPixel
        )

        self.view.setVerticalScrollMode(
            QAbstractItemView
            .ScrollMode
            .ScrollPerPixel
        )

        self.view.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy
            .ScrollBarAlwaysOff
        )

        self.view.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy
            .ScrollBarAlwaysOff
        )

        self.view.setFocusPolicy(
            Qt.FocusPolicy.NoFocus
        )

        self.view.setFocusProxy(
            main_table
        )

        self.view.verticalHeader().setVisible(
            False
        )

        frozen_header = (
            self.view.horizontalHeader()
        )

        frozen_header.setSectionResizeMode(
            QHeaderView
            .ResizeMode
            .Interactive
        )

        frozen_header.setDefaultSectionSize(
            main_table
            .horizontalHeader()
            .defaultSectionSize()
        )

        frozen_header.setMinimumSectionSize(
            main_table
            .horizontalHeader()
            .minimumSectionSize()
        )

        frozen_header.setSectionsMovable(
            False
        )

        frozen_header.setSectionsClickable(
            True
        )

        self.view.verticalHeader().setDefaultSectionSize(
            main_table
            .verticalHeader()
            .defaultSectionSize()
        )

        main_table.installEventFilter(
            self
        )

        main_table.verticalScrollBar().valueChanged.connect(
            self.view
            .verticalScrollBar()
            .setValue
        )

        self.view.verticalScrollBar().valueChanged.connect(
            main_table
            .verticalScrollBar()
            .setValue
        )

        main_table.horizontalHeader().sectionResized.connect(
            self._main_section_resized
        )

        frozen_header.sectionResized.connect(
            self._frozen_section_resized
        )

        main_table.verticalHeader().sectionResized.connect(
            self._main_row_resized
        )

        main_table.horizontalHeader().sortIndicatorChanged.connect(
            self._sync_sort_indicator
        )

        frozen_header.sectionClicked.connect(
            self._sort_from_frozen_header
        )

        self.view.clicked.connect(
            main_table.setCurrentIndex
        )

        self.view.hide()

    @property
    def frozen_columns(
        self,
    ):
        return self._frozen_columns

    def sync(
        self,
        *,
        columns,
    ):
        self._columns = tuple(
            columns
            or ()
        )

        self._frozen_columns = (
            resolve_frozen_columns(
                columns=self._columns,
                preferred_columns=(
                    self._preferred_columns
                ),
            )
        )

        if not self._frozen_columns:
            self._frozen_indexes = ()
            self.view.hide()
            return

        indexes = []

        for column in self._frozen_columns:
            indexes.append(
                self._columns.index(
                    column
                )
            )

        self._frozen_indexes = tuple(
            indexes
        )

        model = self.view.model()

        if model is None:
            self.view.hide()
            return

        column_count = (
            model.columnCount()
        )

        for index in range(
            column_count
        ):
            self.view.setColumnHidden(
                index,
                index
                not in self._frozen_indexes,
            )

        self._sync_frozen_visual_order()

        self._syncing_width = True

        try:
            for index in (
                self._frozen_indexes
            ):
                self.view.setColumnWidth(
                    index,
                    self._main_table
                    .columnWidth(
                        index
                    ),
                )

        finally:
            self._syncing_width = False

        main_header = (
            self._main_table
            .horizontalHeader()
        )

        self._sync_sort_indicator(
            main_header
            .sortIndicatorSection(),
            main_header
            .sortIndicatorOrder(),
        )

        self._update_geometry()

        self.view.show()
        self.view.raise_()

    def _sync_frozen_visual_order(
        self,
    ):
        header = (
            self.view
            .horizontalHeader()
        )

        for (
            target_visual,
            logical_index,
        ) in enumerate(
            self._frozen_indexes
        ):
            current_visual = (
                header.visualIndex(
                    logical_index
                )
            )

            if (
                current_visual
                != target_visual
            ):
                header.moveSection(
                    current_visual,
                    target_visual,
                )

    def _main_section_resized(
        self,
        logical_index,
        _old_size,
        new_size,
    ):
        if (
            self._syncing_width
            or logical_index
            not in self._frozen_indexes
        ):
            return

        self._syncing_width = True

        try:
            self.view.setColumnWidth(
                logical_index,
                new_size,
            )

        finally:
            self._syncing_width = False

        self._update_geometry()

    def _frozen_section_resized(
        self,
        logical_index,
        _old_size,
        new_size,
    ):
        if (
            self._syncing_width
            or logical_index
            not in self._frozen_indexes
        ):
            return

        self._syncing_width = True

        try:
            self._main_table.setColumnWidth(
                logical_index,
                new_size,
            )

        finally:
            self._syncing_width = False

        self._update_geometry()

    def _main_row_resized(
        self,
        logical_index,
        _old_size,
        new_size,
    ):
        self.view.setRowHeight(
            logical_index,
            new_size,
        )

    def _sort_from_frozen_header(
        self,
        logical_index,
    ):
        if (
            logical_index
            not in self._frozen_indexes
        ):
            return

        header = (
            self._main_table
            .horizontalHeader()
        )

        if (
            header.sortIndicatorSection()
            == logical_index
        ):
            order = (
                Qt.SortOrder.AscendingOrder
                if (
                    header.sortIndicatorOrder()
                    == Qt.SortOrder
                    .DescendingOrder
                )
                else
                Qt.SortOrder
                .DescendingOrder
            )

        else:
            order = (
                Qt.SortOrder
                .AscendingOrder
            )

        self._main_table.sortByColumn(
            logical_index,
            order,
        )

    def _sync_sort_indicator(
        self,
        logical_index,
        order,
    ):
        header = (
            self.view
            .horizontalHeader()
        )

        if (
            logical_index
            in self._frozen_indexes
        ):
            header.setSortIndicatorShown(
                True
            )

            header.setSortIndicator(
                logical_index,
                order,
            )

        else:
            header.setSortIndicatorShown(
                False
            )

    def _update_geometry(
        self,
    ):
        if not self._frozen_indexes:
            return

        frozen_width = sum(
            self.view.columnWidth(
                index
            )
            for index
            in self._frozen_indexes
        )

        x = (
            self._main_table
            .verticalHeader()
            .width()
            +
            self._main_table.frameWidth()
        )

        y = (
            self._main_table.frameWidth()
        )

        height = (
            self._main_table
            .viewport()
            .height()
            +
            self._main_table
            .horizontalHeader()
            .height()
        )

        self.view.setGeometry(
            x,
            y,
            frozen_width + 1,
            height,
        )

        self.view.raise_()

    def eventFilter(
        self,
        watched,
        event,
    ):
        if (
            watched
            is self._main_table
            and event.type()
            in {
                QEvent.Type.Resize,
                QEvent.Type.Show,
            }
        ):
            self._update_geometry()

        return super().eventFilter(
            watched,
            event,
        )
