from dataclasses import dataclass

from PySide6.QtCore import (
    QPointF,
    QRectF,
    Qt,
)
from PySide6.QtGui import (
    QColor,
    QIcon,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QPushButton,
)


@dataclass(
    frozen=True,
    slots=True,
)
class SidebarNavigationItem:
    label: str
    page_index: int
    icon_name: str


NAVIGATION_ITEMS = (
    SidebarNavigationItem(
        "Dashboard",
        0,
        "dashboard",
    ),
    SidebarNavigationItem(
        "Presupuesto",
        1,
        "budget",
    ),
    SidebarNavigationItem(
        "Agrupaciones",
        2,
        "grouping",
    ),
    SidebarNavigationItem(
        "Historial",
        3,
        "history",
    ),
)


def navigation_context_text(
    module_label,
    page_index,
) -> str:
    module = str(
        module_label
        if module_label is not None
        else ""
    ).strip()

    page = next(
        (
            item.label
            for item in NAVIGATION_ITEMS
            if item.page_index
            == page_index
        ),
        "Seccion",
    )

    if not module:
        return page

    return (
        f"{module}  /  {page}"
    )


def sidebar_width(
    *,
    expanded: bool,
    expanded_width: int,
    compact_width: int,
) -> int:
    return (
        int(expanded_width)
        if expanded
        else int(compact_width)
    )


class SidebarTextButton(
    QPushButton
):
    def __init__(
        self,
        text="",
        *,
        compact_text="",
        parent=None,
    ):
        super().__init__(
            parent
        )

        self._sidebar_expanded = True
        self._expanded_text = ""
        self._compact_text = str(
            compact_text
        )

        self.setText(
            text
        )

    def setText(
        self,
        text,
    ):
        self._expanded_text = str(
            text
            if text is not None
            else ""
        )

        visible_text = (
            self._expanded_text
            if self._sidebar_expanded
            else self._compact_text
        )

        super().setText(
            visible_text
        )

    def set_sidebar_expanded(
        self,
        expanded: bool,
    ):
        self._sidebar_expanded = bool(
            expanded
        )

        visible_text = (
            self._expanded_text
            if self._sidebar_expanded
            else self._compact_text
        )

        super().setText(
            visible_text
        )

    @property
    def expanded_text(
        self,
    ) -> str:
        return self._expanded_text


def sidebar_icon(
    name,
    *,
    size=22,
    normal="#E7F2EB",
    active="#155C3D",
):
    icon = QIcon()

    icon.addPixmap(
        _draw_icon(
            name,
            normal,
            size,
        ),
        QIcon.Mode.Normal,
        QIcon.State.Off,
    )

    icon.addPixmap(
        _draw_icon(
            name,
            active,
            size,
        ),
        QIcon.Mode.Normal,
        QIcon.State.On,
    )

    disabled = _draw_icon(
        name,
        "#98A2B3",
        size,
    )

    icon.addPixmap(
        disabled,
        QIcon.Mode.Disabled,
        QIcon.State.Off,
    )

    icon.addPixmap(
        disabled,
        QIcon.Mode.Disabled,
        QIcon.State.On,
    )

    return icon


def _draw_icon(
    name,
    color,
    size,
):
    pixmap = QPixmap(
        size,
        size,
    )

    pixmap.fill(
        Qt.GlobalColor.transparent
    )

    painter = QPainter(
        pixmap
    )

    painter.setRenderHint(
        QPainter.RenderHint.Antialiasing,
        True,
    )

    pen = QPen(
        QColor(color)
    )

    pen.setWidthF(
        1.8
    )

    pen.setCapStyle(
        Qt.PenCapStyle.RoundCap
    )

    pen.setJoinStyle(
        Qt.PenJoinStyle.RoundJoin
    )

    painter.setPen(
        pen
    )

    painter.setBrush(
        Qt.BrushStyle.NoBrush
    )

    key = str(
        name
    ).strip().lower()

    if key == "menu":
        for y in (
            6.0,
            11.0,
            16.0,
        ):
            painter.drawLine(
                QPointF(4.0, y),
                QPointF(18.0, y),
            )

    elif key == "dashboard":
        for rect in (
            QRectF(3, 3, 6.5, 6.5),
            QRectF(12.5, 3, 6.5, 6.5),
            QRectF(3, 12.5, 6.5, 6.5),
            QRectF(12.5, 12.5, 6.5, 6.5),
        ):
            painter.drawRoundedRect(
                rect,
                1.2,
                1.2,
            )

    elif key == "budget":
        painter.drawRoundedRect(
            QRectF(
                5,
                2.5,
                12,
                17,
            ),
            1.5,
            1.5,
        )

        painter.drawLine(
            QPointF(8, 7),
            QPointF(14, 7),
        )

        painter.drawLine(
            QPointF(8, 11),
            QPointF(14, 11),
        )

        painter.drawLine(
            QPointF(8, 15),
            QPointF(12, 15),
        )

    elif key == "grouping":
        painter.drawLine(
            QPointF(11, 6),
            QPointF(11, 10),
        )

        painter.drawLine(
            QPointF(11, 10),
            QPointF(6, 14),
        )

        painter.drawLine(
            QPointF(11, 10),
            QPointF(16, 14),
        )

        for center in (
            QPointF(11, 4),
            QPointF(6, 17),
            QPointF(16, 17),
        ):
            painter.drawEllipse(
                center,
                2.3,
                2.3,
            )

    elif key == "history":
        painter.drawEllipse(
            QRectF(
                3,
                3,
                16,
                16,
            )
        )

        painter.drawLine(
            QPointF(11, 11),
            QPointF(11, 6.5),
        )

        painter.drawLine(
            QPointF(11, 11),
            QPointF(15, 13),
        )

    elif key == "apply":
        painter.drawEllipse(
            QRectF(
                3,
                3,
                16,
                16,
            )
        )

        painter.drawLine(
            QPointF(7, 11),
            QPointF(10, 14),
        )

        painter.drawLine(
            QPointF(10, 14),
            QPointF(16, 8),
        )

    elif key == "cloud":
        path = QPainterPath()

        path.moveTo(
            5,
            16,
        )

        path.cubicTo(
            2.5,
            16,
            2.5,
            11.5,
            6,
            11,
        )

        path.cubicTo(
            6,
            7.5,
            10,
            6,
            12,
            9,
        )

        path.cubicTo(
            14.5,
            6.5,
            18.5,
            8.5,
            18,
            12,
        )

        path.cubicTo(
            21,
            12,
            21,
            16,
            17.5,
            16,
        )

        path.closeSubpath()

        painter.drawPath(
            path
        )

    painter.end()

    return pixmap
