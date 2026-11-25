"""Painted icons for the OneClick shell.

The home screen uses a small set of line icons instead of emoji so the
Starbucks-inspired layout stays sharp on Windows at any scale.
"""

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QSizePolicy, QWidget


def _pen(color: QColor, width: float) -> QPen:
    pen = QPen(color)
    pen.setWidthF(width)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    return pen


def paint_icon(painter: QPainter, kind: str, rect: QRectF, color: QColor) -> None:
    painter.save()
    stroke = max(1.4, min(rect.width(), rect.height()) * 0.085)
    if kind == "swap":
        _swap(painter, rect, color, stroke)
    elif kind == "home":
        _home(painter, rect, color, stroke)
    elif kind == "gear":
        _gear(painter, rect, color, stroke)
    elif kind == "info":
        _info(painter, rect, color, stroke)
    elif kind == "help":
        _help(painter, rect, color, stroke)
    elif kind == "ethernet":
        _ethernet(painter, rect, color, stroke)
    elif kind == "user":
        _user(painter, rect, color, stroke)
    elif kind == "refresh":
        _refresh(painter, rect, color, stroke)
    elif kind == "monitor":
        _monitor(painter, rect, color, stroke)
    elif kind == "laptop":
        _laptop(painter, rect, color, stroke)
    elif kind == "check":
        _check(painter, rect, color)
    elif kind == "infoFill":
        _info_fill(painter, rect, color)
    elif kind == "min":
        painter.setPen(_pen(color, stroke))
        y = rect.center().y()
        painter.drawLine(QPointF(rect.left() + rect.width() * 0.2, y), QPointF(rect.right() - rect.width() * 0.2, y))
    elif kind == "max":
        painter.setPen(_pen(color, stroke))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(rect.adjusted(stroke, stroke, -stroke, -stroke), 2, 2)
    elif kind == "restore":
        _restore(painter, rect, color, stroke)
    elif kind == "close":
        painter.setPen(_pen(color, stroke))
        inset = rect.width() * 0.28
        painter.drawLine(QPointF(rect.left() + inset, rect.top() + inset), QPointF(rect.right() - inset, rect.bottom() - inset))
        painter.drawLine(QPointF(rect.right() - inset, rect.top() + inset), QPointF(rect.left() + inset, rect.bottom() - inset))
    painter.restore()


def _swap(painter: QPainter, rect: QRectF, color: QColor, stroke: float) -> None:
    painter.setPen(_pen(color, stroke * 1.15))
    painter.setBrush(Qt.NoBrush)
    y1 = rect.top() + rect.height() * 0.34
    y2 = rect.top() + rect.height() * 0.66
    left = rect.left() + rect.width() * 0.18
    right = rect.right() - rect.width() * 0.18
    head = rect.width() * 0.16
    painter.drawLine(QPointF(right, y1), QPointF(left, y1))
    painter.drawLine(QPointF(left, y1), QPointF(left + head, y1 - head * 0.75))
    painter.drawLine(QPointF(left, y1), QPointF(left + head, y1 + head * 0.75))
    painter.drawLine(QPointF(left, y2), QPointF(right, y2))
    painter.drawLine(QPointF(right, y2), QPointF(right - head, y2 - head * 0.75))
    painter.drawLine(QPointF(right, y2), QPointF(right - head, y2 + head * 0.75))


def _home(painter: QPainter, rect: QRectF, color: QColor, stroke: float) -> None:
    painter.setPen(_pen(color, stroke))
    painter.setBrush(Qt.NoBrush)
    path = QPainterPath()
    cx = rect.center().x()
    top = rect.top() + rect.height() * 0.16
    mid = rect.top() + rect.height() * 0.46
    left = rect.left() + rect.width() * 0.16
    right = rect.right() - rect.width() * 0.16
    bottom = rect.bottom() - rect.height() * 0.12
    path.moveTo(cx, top)
    path.lineTo(right, mid)
    path.lineTo(right - rect.width() * 0.08, mid)
    path.lineTo(right - rect.width() * 0.08, bottom)
    path.lineTo(left + rect.width() * 0.08, bottom)
    path.lineTo(left + rect.width() * 0.08, mid)
    path.lineTo(left, mid)
    path.closeSubpath()
    painter.drawPath(path)
    door_w = rect.width() * 0.16
    door = QRectF(cx - door_w / 2, bottom - rect.height() * 0.28, door_w, rect.height() * 0.28)
    painter.drawRoundedRect(door, 1, 1)


def _gear(painter: QPainter, rect: QRectF, color: QColor, stroke: float) -> None:
    painter.setPen(Qt.NoPen)
    painter.setBrush(color)
    cx = rect.center().x()
    cy = rect.center().y()
    outer = rect.width() * 0.46
    inner = outer * 0.68
    hole = outer * 0.32
    path = QPainterPath()
    teeth = 8
    for index in range(teeth):
        a1 = math.radians(index * 45 - 14)
        a2 = math.radians(index * 45 + 14)
        a3 = math.radians(index * 45 + 24)
        a4 = math.radians((index + 1) * 45 - 24)
        points = (
            (cx + outer * math.cos(a1), cy + outer * math.sin(a1)),
            (cx + outer * math.cos(a2), cy + outer * math.sin(a2)),
            (cx + inner * math.cos(a3), cy + inner * math.sin(a3)),
            (cx + inner * math.cos(a4), cy + inner * math.sin(a4)),
        )
        if index == 0:
            path.moveTo(*points[0])
        else:
            path.lineTo(*points[0])
        for point in points[1:]:
            path.lineTo(*point)
    path.closeSubpath()
    cutout = QPainterPath()
    cutout.addEllipse(QPointF(cx, cy), hole, hole)
    painter.drawPath(path.subtracted(cutout))
    # Keep the stroke argument used so callers can pass a consistent width.
    del stroke


def _info(painter: QPainter, rect: QRectF, color: QColor, stroke: float) -> None:
    painter.setPen(_pen(color, stroke))
    painter.setBrush(Qt.NoBrush)
    bubble = rect.adjusted(stroke, stroke, -stroke, -stroke)
    painter.drawEllipse(bubble)
    cx = bubble.center().x()
    painter.setBrush(color)
    painter.setPen(Qt.NoPen)
    dot_r = max(1.2, stroke * 0.55)
    painter.drawEllipse(QPointF(cx, bubble.top() + bubble.height() * 0.32), dot_r, dot_r)
    painter.setPen(_pen(color, stroke))
    painter.drawLine(
        QPointF(cx, bubble.top() + bubble.height() * 0.46),
        QPointF(cx, bubble.top() + bubble.height() * 0.72),
    )


def _help(painter: QPainter, rect: QRectF, color: QColor, stroke: float) -> None:
    painter.setPen(_pen(color, stroke))
    painter.setBrush(Qt.NoBrush)
    bubble = rect.adjusted(stroke, stroke, -stroke, -stroke)
    painter.drawEllipse(bubble)
    hook = QRectF(
        bubble.left() + bubble.width() * 0.30,
        bubble.top() + bubble.height() * 0.18,
        bubble.width() * 0.40,
        bubble.height() * 0.36,
    )
    painter.drawArc(hook, 40 * 16, 250 * 16)
    cx = bubble.center().x()
    painter.drawLine(
        QPointF(cx, bubble.top() + bubble.height() * 0.56),
        QPointF(cx, bubble.top() + bubble.height() * 0.66),
    )
    painter.setPen(Qt.NoPen)
    painter.setBrush(color)
    painter.drawEllipse(QPointF(cx, bubble.top() + bubble.height() * 0.76), stroke * 0.45, stroke * 0.45)


def _ethernet(painter: QPainter, rect: QRectF, color: QColor, stroke: float) -> None:
    painter.setPen(_pen(color, stroke))
    painter.setBrush(Qt.NoBrush)
    body = QRectF(
        rect.left() + rect.width() * 0.18,
        rect.top() + rect.height() * 0.12,
        rect.width() * 0.64,
        rect.height() * 0.48,
    )
    painter.drawRoundedRect(body, 3, 3)
    opening = QRectF(
        body.left() + body.width() * 0.16,
        body.top() + body.height() * 0.34,
        body.width() * 0.68,
        body.height() * 0.46,
    )
    painter.drawRoundedRect(opening, 1.5, 1.5)
    cx = rect.center().x()
    painter.drawLine(QPointF(cx, body.bottom()), QPointF(cx, rect.bottom() - rect.height() * 0.08))


def _user(painter: QPainter, rect: QRectF, color: QColor, stroke: float) -> None:
    painter.setPen(_pen(color, stroke))
    painter.setBrush(Qt.NoBrush)
    cx = rect.center().x()
    painter.drawEllipse(QPointF(cx, rect.top() + rect.height() * 0.34), rect.width() * 0.16, rect.height() * 0.16)
    shoulders = QRectF(
        rect.left() + rect.width() * 0.16,
        rect.top() + rect.height() * 0.52,
        rect.width() * 0.68,
        rect.height() * 0.62,
    )
    painter.drawArc(shoulders, 0, 180 * 16)


def _refresh(painter: QPainter, rect: QRectF, color: QColor, stroke: float) -> None:
    painter.setPen(_pen(color, stroke))
    painter.setBrush(Qt.NoBrush)
    arc = rect.adjusted(rect.width() * 0.16, rect.height() * 0.16, -rect.width() * 0.16, -rect.height() * 0.16)
    painter.drawArc(arc, 45 * 16, 280 * 16)
    # Arrow head near the end of the arc (about 325 degrees, 0 = east).
    angle = math.radians(325)
    cx = arc.center().x()
    cy = arc.center().y()
    rx = arc.width() / 2
    ry = arc.height() / 2
    tip = QPointF(cx + rx * math.cos(angle), cy - ry * math.sin(angle))
    painter.drawLine(tip, QPointF(tip.x() - rect.width() * 0.16, tip.y() - rect.height() * 0.02))
    painter.drawLine(tip, QPointF(tip.x() + rect.width() * 0.02, tip.y() + rect.height() * 0.16))


def _monitor(painter: QPainter, rect: QRectF, color: QColor, stroke: float) -> None:
    painter.setPen(_pen(color, stroke))
    painter.setBrush(Qt.NoBrush)
    screen = QRectF(
        rect.left() + rect.width() * 0.08,
        rect.top() + rect.height() * 0.10,
        rect.width() * 0.84,
        rect.height() * 0.58,
    )
    painter.drawRoundedRect(screen, 3, 3)
    cx = rect.center().x()
    neck_top = screen.bottom()
    base_y = rect.bottom() - rect.height() * 0.08
    painter.drawLine(QPointF(cx, neck_top), QPointF(cx, base_y))
    painter.drawLine(QPointF(cx - rect.width() * 0.22, base_y), QPointF(cx + rect.width() * 0.22, base_y))


def _laptop(painter: QPainter, rect: QRectF, color: QColor, stroke: float) -> None:
    painter.setPen(_pen(color, stroke))
    painter.setBrush(Qt.NoBrush)
    screen = QRectF(
        rect.left() + rect.width() * 0.16,
        rect.top() + rect.height() * 0.12,
        rect.width() * 0.68,
        rect.height() * 0.52,
    )
    painter.drawRoundedRect(screen, 2, 2)
    base = QRectF(
        rect.left() + rect.width() * 0.06,
        screen.bottom() + rect.height() * 0.04,
        rect.width() * 0.88,
        rect.height() * 0.14,
    )
    painter.drawRoundedRect(base, 2, 2)


def _check(painter: QPainter, rect: QRectF, color: QColor) -> None:
    painter.setPen(Qt.NoPen)
    painter.setBrush(color)
    painter.drawEllipse(rect)
    pen = _pen(QColor("#FFFFFF"), max(1.6, rect.width() * 0.12))
    painter.setPen(pen)
    painter.drawLine(
        QPointF(rect.left() + rect.width() * 0.28, rect.center().y() + rect.height() * 0.02),
        QPointF(rect.left() + rect.width() * 0.44, rect.top() + rect.height() * 0.66),
    )
    painter.drawLine(
        QPointF(rect.left() + rect.width() * 0.44, rect.top() + rect.height() * 0.66),
        QPointF(rect.left() + rect.width() * 0.74, rect.top() + rect.height() * 0.34),
    )


def _info_fill(painter: QPainter, rect: QRectF, color: QColor) -> None:
    painter.setPen(Qt.NoPen)
    painter.setBrush(color)
    painter.drawEllipse(rect)
    pen = _pen(QColor("#FFFFFF"), max(1.5, rect.width() * 0.10))
    painter.setPen(pen)
    cx = rect.center().x()
    painter.setBrush(QColor("#FFFFFF"))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(QPointF(cx, rect.top() + rect.height() * 0.30), rect.width() * 0.07, rect.height() * 0.07)
    painter.setPen(pen)
    painter.drawLine(
        QPointF(cx, rect.top() + rect.height() * 0.44),
        QPointF(cx, rect.top() + rect.height() * 0.72),
    )


def _restore(painter: QPainter, rect: QRectF, color: QColor, stroke: float) -> None:
    painter.setPen(_pen(color, stroke))
    painter.setBrush(Qt.NoBrush)
    back = rect.adjusted(rect.width() * 0.28, stroke, -stroke, -rect.height() * 0.28)
    front = rect.adjusted(stroke, rect.height() * 0.28, -rect.width() * 0.28, -stroke)
    painter.drawRoundedRect(back, 1.5, 1.5)
    painter.setBrush(QColor("#083A29"))
    painter.drawRoundedRect(front, 1.5, 1.5)
    painter.setBrush(Qt.NoBrush)
    painter.drawRoundedRect(front, 1.5, 1.5)


def make_icon(kind: str, size: int, color: str) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    paint_icon(painter, kind, QRectF(0.5, 0.5, size - 1, size - 1), QColor(color))
    painter.end()
    return QIcon(pixmap)


class IconWidget(QWidget):
    def __init__(self, kind: str, size: int = 24, color: str = "#006241", parent=None):
        super().__init__(parent)
        self.kind = kind
        self.color = QColor(color)
        self.setFixedSize(size, size)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    def paintEvent(self, event):
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        paint_icon(painter, self.kind, QRectF(0.5, 0.5, self.width() - 1, self.height() - 1), self.color)
        painter.end()


class CircleIcon(QWidget):
    """Mint disc with a green glyph, used on the Host and Client cards."""

    def __init__(self, kind: str, diameter: int = 64, parent=None):
        super().__init__(parent)
        self.kind = kind
        self.setFixedSize(diameter, diameter)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    def paintEvent(self, event):
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#E5F3EC"))
        painter.drawEllipse(self.rect().adjusted(1, 1, -1, -1))
        margin = self.width() * 0.24
        paint_icon(
            painter,
            self.kind,
            QRectF(margin, margin, self.width() - 2 * margin, self.height() - 2 * margin),
            QColor("#006241"),
        )
        painter.end()


class LogoMark(QWidget):
    def __init__(self, size: int = 72, radius: int = 18, parent=None):
        super().__init__(parent)
        self.radius = radius
        self.setFixedSize(size, size)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    def paintEvent(self, event):
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#00754A"))
        painter.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), self.radius, self.radius)
        inset = self.width() * 0.18
        paint_icon(
            painter,
            "swap",
            QRectF(inset, inset, self.width() - 2 * inset, self.height() - 2 * inset),
            QColor("#FFFFFF"),
        )
        painter.end()


class StatusDot(QWidget):
    def __init__(self, color: str = "#3DDC84", size: int = 9, parent=None):
        super().__init__(parent)
        self.color = QColor(color)
        self.setFixedSize(size, size)

    def paintEvent(self, event):
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(self.color)
        painter.drawEllipse(self.rect().adjusted(0, 0, -1, -1))
        painter.end()
