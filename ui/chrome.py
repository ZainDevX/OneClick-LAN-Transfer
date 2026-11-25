"""Window chrome for OneClick LAN Transfer.

Dark-green title bar and sidebar stay on screen while the content stack
changes. About and Help are intentionally empty pages.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget
)

from app import __version__
from ui.icons import LogoMark, StatusDot, make_icon


def apply_role(widget, name: str) -> None:
    """Swap a stylesheet object name and repaint the widget."""
    widget.setObjectName(name)
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)


class BlankPage(QWidget):
    """Empty content page. About and Help stay blank until later screens exist."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("canvas")
        self.setAttribute(Qt.WA_StyledBackground, True)


class TitleBar(QFrame):
    def __init__(self, window: QWidget):
        super().__init__(window)
        self.setObjectName("titlebar")
        self.setFixedHeight(44)
        self._drag_origin = None
        self._window_origin = None
        self._build(window)

    def _build(self, window: QWidget) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 0, 0)
        layout.setSpacing(10)

        layout.addWidget(LogoMark(24))
        title = QLabel("OneClick LAN Transfer")
        title.setObjectName("appTitle")
        layout.addWidget(title)
        layout.addStretch(1)

        self.min_btn = self._window_button("min", window.showMinimized)
        self.max_btn = self._window_button("max", self._toggle_max)
        self.close_btn = self._window_button("close", window.close, close=True)
        layout.addWidget(self.min_btn)
        layout.addWidget(self.max_btn)
        layout.addWidget(self.close_btn)

    def _window_button(self, kind: str, handler, close: bool = False) -> QPushButton:
        button = QPushButton()
        button.setObjectName("winClose" if close else "winBtn")
        button.setIcon(make_icon(kind, 16, "#FFFFFF"))
        button.setIconSize(button.iconSize())
        button.setFixedSize(46, 44)
        button.setCursor(Qt.PointingHandCursor)
        button.setFocusPolicy(Qt.NoFocus)
        button.clicked.connect(handler)
        from PySide6.QtCore import QSize
        button.setIconSize(QSize(14, 14))
        return button

    def sync_max_icon(self) -> None:
        kind = "restore" if self.window().isMaximized() else "max"
        self.max_btn.setIcon(make_icon(kind, 16, "#FFFFFF"))

    def _toggle_max(self) -> None:
        window = self.window()
        if window.isMaximized():
            window.showNormal()
        else:
            window.showMaximized()
        self.sync_max_icon()

    def _on_button(self, pos) -> bool:
        widget = self.childAt(pos)
        while widget is not None and widget is not self:
            if isinstance(widget, QPushButton):
                return True
            widget = widget.parentWidget()
        return False

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and not self._on_button(event.position().toPoint()):
            self._drag_origin = event.globalPosition().toPoint()
            self._window_origin = self.window().frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_origin is not None and event.buttons() & Qt.LeftButton:
            window = self.window()
            delta = event.globalPosition().toPoint() - self._drag_origin
            if window.isMaximized():
                window.showNormal()
                self.sync_max_icon()
                self._window_origin = window.frameGeometry().topLeft()
                self._drag_origin = event.globalPosition().toPoint()
            else:
                window.move(self._window_origin + delta)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_origin = None
        self._window_origin = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton and not self._on_button(event.position().toPoint()):
            self._toggle_max()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)


class Sidebar(QFrame):
    navigate = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(216)
        self._buttons = {}
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 26, 16, 20)
        layout.setSpacing(4)

        logo_row = QHBoxLayout()
        logo_row.addStretch(1)
        logo_row.addWidget(LogoMark(78))
        logo_row.addStretch(1)
        layout.addLayout(logo_row)
        layout.addSpacing(8)

        wordmark = QVBoxLayout()
        wordmark.setSpacing(0)
        for text in ("OneClick", "LAN Transfer"):
            label = QLabel(text)
            label.setObjectName("wordmark")
            label.setAlignment(Qt.AlignCenter)
            wordmark.addWidget(label)
        layout.addLayout(wordmark)

        layout.addSpacing(22)

        for key, text, kind in (
            ("home", "Home", "home"),
            ("host", "Host Mode", "stack"),
            ("about", "About", "info"),
            ("help", "Help", "help"),
        ):
            button = QPushButton(text)
            button.setObjectName("nav")
            button.setIcon(make_icon(kind, 20, "#FFFFFF"))
            button.setIconSize(button.iconSize())
            from PySide6.QtCore import QSize
            button.setIconSize(QSize(18, 18))
            button.setCursor(Qt.PointingHandCursor)
            button.setCheckable(True)
            button.setFocusPolicy(Qt.NoFocus)
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            button.setFixedHeight(48)
            button.clicked.connect(lambda _checked=False, name=key: self.navigate.emit(name))
            self._buttons[key] = button
            layout.addWidget(button)
            layout.addSpacing(2)

        layout.addStretch(1)

        rule = QFrame()
        rule.setObjectName("sideRule")
        rule.setFixedHeight(1)
        layout.addWidget(rule)
        layout.addSpacing(12)

        ready_row = QHBoxLayout()
        ready_row.setContentsMargins(18, 0, 0, 0)
        ready_row.setSpacing(8)
        ready_row.addWidget(StatusDot())
        ready = QLabel("Ready")
        ready.setObjectName("readyLabel")
        ready_row.addWidget(ready)
        ready_row.addStretch(1)
        layout.addLayout(ready_row)
        layout.addSpacing(4)

        version = QLabel(f"v{__version__}")
        version.setObjectName("versionLabel")
        version.setContentsMargins(16, 0, 0, 0)
        layout.addWidget(version)

    def set_active(self, key: str | None) -> None:
        for name, button in self._buttons.items():
            button.setChecked(key is not None and name == key)
