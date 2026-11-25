"""
Main Application Window for OneClick LAN Transfer.
Manages application lifecycle, view transitions, dark/light themes,
and safe network restoration on close.
"""

import logging
import sys
from ctypes import wintypes
from pathlib import Path

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QCursor, QFont, QIcon
from PySide6.QtWidgets import (
    QApplication, QHBoxLayout, QMainWindow, QMessageBox, QStackedWidget,
    QVBoxLayout, QWidget
)

from app.network_manager import NetworkManager
from app.settings_manager import SettingsManager
from ui.chrome import BlankPage, Sidebar, TitleBar
from ui.client_view import ClientView
from ui.dashboard import DashboardView
from ui.host_view import HostView
from ui.settings_view import SettingsView
from ui.styles import DARK_THEME, LIGHT_THEME
from ui.adapter_directory import AdapterDirectory
from ui.worker import FunctionThread

logger = logging.getLogger("OneClickLAN.MainWindow")

WM_NCHITTEST = 0x0084
HTLEFT = 10
HTRIGHT = 11
HTTOP = 12
HTTOPLEFT = 13
HTTOPRIGHT = 14
HTBOTTOM = 15
HTBOTTOMLEFT = 16
HTBOTTOMRIGHT = 17


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        app = QApplication.instance()
        if app is not None:
            app.setStyle("Fusion")
            font = QFont("Segoe UI")
            font.setPixelSize(14)
            app.setFont(font)

        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setWindowTitle("OneClick LAN Transfer")
        self.resize(1280, 820)
        self.setMinimumSize(1040, 680)

        icon_path = Path(__file__).parent.parent / "assets" / "app.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self.settings = SettingsManager()
        self.net_mgr = NetworkManager()
        self.adapter_directory = AdapterDirectory(self)
        self._restore_thread = None

        self.init_ui()
        self.apply_theme(self.settings.get("theme", "dark"))

    def init_ui(self):
        root = QWidget()
        root.setObjectName("canvas")
        root.setAttribute(Qt.WA_StyledBackground, True)
        self.setCentralWidget(root)

        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.title_bar = TitleBar(self)
        outer.addWidget(self.title_bar)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        self.sidebar = Sidebar(self)
        self.sidebar.navigate.connect(self._on_sidebar)
        body.addWidget(self.sidebar)

        self.stack = QStackedWidget(self)
        self.stack.setObjectName("canvas")
        self.stack.setAttribute(Qt.WA_StyledBackground, True)
        body.addWidget(self.stack, 1)
        outer.addLayout(body, 1)

        self.dashboard_view = DashboardView(self)
        self.host_view = HostView(self.net_mgr, self)
        self.client_view = ClientView(self.net_mgr, self)
        self.settings_view = SettingsView(self.settings, self.net_mgr, self)
        self.about_view = BlankPage(self)
        self.help_view = BlankPage(self)

        self.stack.addWidget(self.dashboard_view)    # Index 0
        self.stack.addWidget(self.host_view)         # Index 1
        self.stack.addWidget(self.client_view)       # Index 2
        self.stack.addWidget(self.settings_view)     # Index 3
        self.stack.addWidget(self.about_view)        # Index 4
        self.stack.addWidget(self.help_view)         # Index 5

        self.dashboard_view.request_host_mode.connect(lambda: self.switch_page(1))
        self.dashboard_view.request_client_mode.connect(lambda: self.switch_page(2))
        self.dashboard_view.request_settings.connect(lambda: self.switch_page(3))
        self.dashboard_view.request_restore_network.connect(self.handle_manual_network_restore)

        self.host_view.request_back.connect(lambda: self.switch_page(0))
        self.client_view.request_back.connect(lambda: self.switch_page(0))
        self.settings_view.request_back.connect(lambda: self.switch_page(0))
        self.settings_view.theme_changed.connect(self.apply_theme)
        self.sidebar.set_active("home")

    def _on_sidebar(self, key: str) -> None:
        index = {"home": 0, "host": 1, "about": 4, "help": 5}.get(key)
        if index is None:
            return
        current = self.stack.currentIndex()
        if current == index:
            self._sync_nav(index)
            return
        if current == 1 and not self.host_view.can_leave():
            self._sync_nav(current)
            return
        if current == 2 and not self.client_view.can_leave():
            self._sync_nav(current)
            return
        self.switch_page(index)

    def _sync_nav(self, index: int) -> None:
        self.sidebar.set_active({0: "home", 1: "host", 4: "about", 5: "help"}.get(index))

    def start_adapter_detection(self):
        """Called after the window is shown. The scan itself is not on the GUI thread."""
        self.adapter_directory.updated.connect(self._publish_adapters)
        self.adapter_directory.failed.connect(self._on_adapter_scan_failed)
        self._publish_adapters()
        self.adapter_directory.revalidate(force=True)

    def refresh_adapters(self):
        self.dashboard_view.adapter_status_lbl.setText("Refreshing Ethernet adapters...")
        detail = getattr(self.dashboard_view, "adapter_detail_lbl", None)
        if detail is not None:
            detail.setText("")
        self.adapter_directory.revalidate(force=True)

    def invalidate_adapters(self):
        """Drop freshness after a network change and reload in the background."""
        self.adapter_directory.invalidate()
        self.adapter_directory.revalidate(force=True)

    def _publish_adapters(self, adapters=None):
        if adapters is None:
            adapters = self.adapter_directory.current()
        scanning = adapters is None
        self.dashboard_view.apply_adapters(adapters, scanning=scanning)
        self.host_view.apply_adapters(adapters)
        self.client_view.apply_adapters(adapters)

    def _on_adapter_scan_failed(self, message: str):
        self.dashboard_view.show_adapter_error(message)

    def switch_page(self, index: int):
        self.stack.setCurrentIndex(index)
        self._sync_nav(index)
        self.adapter_directory.revalidate()
        self._publish_adapters()

    def apply_theme(self, theme_name: str):
        if theme_name.lower() == "light":
            self.setStyleSheet(LIGHT_THEME)
        else:
            self.setStyleSheet(DARK_THEME)

    def _set_restore_enabled(self, enabled: bool) -> None:
        self.dashboard_view.restore_btn.setEnabled(enabled)
        button = getattr(self.settings_view, "restore_btn", None)
        if button is not None:
            button.setEnabled(enabled)

    def handle_manual_network_restore(self):
        reply = QMessageBox.question(
            self,
            "Restore Original Network Settings?",
            "This will revert the selected Ethernet adapter back to its original DHCP or static IP configuration and remove any temporary firewall rules.\n\nProceed?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        if reply == QMessageBox.Yes:
            self._set_restore_enabled(False)
            self._restore_thread = FunctionThread(self.net_mgr.restore_adapter_configuration, self)
            self._restore_thread.succeeded.connect(self._on_restore_finished)
            self._restore_thread.failed.connect(self._on_restore_failed)
            self._restore_thread.start()

    def _on_restore_finished(self, outcome):
        self._set_restore_enabled(True)
        ok, msg = outcome
        self.invalidate_adapters()
        if ok:
            QMessageBox.information(self, "Network Restored", f"✅ {msg}")
        else:
            QMessageBox.warning(self, "Restoration Result", f"⚠️ {msg}")

    def _on_restore_failed(self, message: str):
        self._set_restore_enabled(True)
        QMessageBox.warning(self, "Restoration Result", f"⚠️ {message}")

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.WindowStateChange and hasattr(self, "title_bar"):
            self.title_bar.sync_max_icon()

    def _resize_hit(self, pos) -> int:
        border = 6
        x, y = pos.x(), pos.y()
        width, height = self.width(), self.height()
        left = x <= border
        right = x >= width - border
        top = y <= border
        bottom = y >= height - border
        if top and left:
            return HTTOPLEFT
        if top and right:
            return HTTOPRIGHT
        if bottom and left:
            return HTBOTTOMLEFT
        if bottom and right:
            return HTBOTTOMRIGHT
        if left:
            return HTLEFT
        if right:
            return HTRIGHT
        if top:
            return HTTOP
        if bottom:
            return HTBOTTOM
        return 0

    def nativeEvent(self, eventType, message):
        if sys.platform == "win32" and eventType == b"windows_generic_MSG":
            try:
                msg = wintypes.MSG.from_address(int(message))
                if msg.message == WM_NCHITTEST and not self.isMaximized():
                    hit = self._resize_hit(self.mapFromGlobal(QCursor.pos()))
                    if hit:
                        return True, hit
            except Exception:
                logger.debug("Window resize hit-test failed", exc_info=True)
        result = super().nativeEvent(eventType, message)
        if isinstance(result, tuple):
            return result
        return False, 0

    def closeEvent(self, event):
        # Stop host service if active
        if self.host_view.host_service:
            self.host_view.stop_host()

        # Stop client if active
        if self.client_view.client_service:
            self.client_view.client_service.disconnect()

        # Auto-restore network if enabled
        if self.settings.get("auto_restore_network", True):
            if self.net_mgr.active_adapter or list(self.net_mgr.backup_dir.glob("backup_*.json")):
                logger.info("Auto-restoring network settings on exit...")
                self.net_mgr.restore_adapter_configuration()

        event.accept()
