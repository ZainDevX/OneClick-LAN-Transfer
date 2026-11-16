"""
Main Application Window for OneClick LAN Transfer.
Manages application lifecycle, view transitions, dark/light themes,
and safe network restoration on close.
"""

import sys
import logging
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QStackedWidget, QMessageBox, QWidget, QVBoxLayout
)
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt

from app.settings_manager import SettingsManager
from app.network_manager import NetworkManager
from ui.styles import DARK_THEME, LIGHT_THEME
from ui.dashboard import DashboardView
from ui.host_view import HostView
from ui.client_view import ClientView
from ui.settings_view import SettingsView

logger = logging.getLogger("OneClickLAN.MainWindow")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OneClick LAN Transfer — High-Speed Direct Ethernet")
        self.resize(880, 680)
        self.setMinimumSize(800, 600)

        # Set App Icon if present
        icon_path = Path(__file__).parent.parent / "assets" / "app.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self.settings = SettingsManager()
        self.net_mgr = NetworkManager()

        self.init_ui()
        self.apply_theme(self.settings.get("theme", "dark"))

    def init_ui(self):
        self.stack = QStackedWidget(self)
        self.setCentralWidget(self.stack)

        # Create Views
        self.dashboard_view = DashboardView(self)
        self.host_view = HostView(self.net_mgr, self)
        self.client_view = ClientView(self.net_mgr, self)
        self.settings_view = SettingsView(self.settings, self.net_mgr, self)

        # Add to stack
        self.stack.addWidget(self.dashboard_view)    # Index 0
        self.stack.addWidget(self.host_view)         # Index 1
        self.stack.addWidget(self.client_view)       # Index 2
        self.stack.addWidget(self.settings_view)     # Index 3

        # Connect Navigation Signals
        self.dashboard_view.request_host_mode.connect(lambda: self.switch_page(1))
        self.dashboard_view.request_client_mode.connect(lambda: self.switch_page(2))
        self.dashboard_view.request_settings.connect(lambda: self.switch_page(3))
        self.dashboard_view.request_restore_network.connect(self.handle_manual_network_restore)

        self.host_view.request_back.connect(lambda: self.switch_page(0))
        self.client_view.request_back.connect(lambda: self.switch_page(0))
        self.settings_view.request_back.connect(lambda: self.switch_page(0))
        self.settings_view.theme_changed.connect(self.apply_theme)

    def switch_page(self, index: int):
        self.stack.setCurrentIndex(index)
        if index == 0:
            self.dashboard_view.refresh_system_status()
        elif index == 1:
            self.host_view.populate_adapters()
        elif index == 2:
            self.client_view.populate_adapters()

    def apply_theme(self, theme_name: str):
        if theme_name.lower() == "light":
            self.setStyleSheet(LIGHT_THEME)
        else:
            self.setStyleSheet(DARK_THEME)

    def handle_manual_network_restore(self):
        reply = QMessageBox.question(
            self,
            "Restore Original Network Settings?",
            "This will revert the selected Ethernet adapter back to its original DHCP or static IP configuration and remove any temporary firewall rules.\n\nProceed?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        if reply == QMessageBox.Yes:
            ok, msg = self.net_mgr.restore_adapter_configuration()
            if ok:
                QMessageBox.information(self, "Network Restored", f"✅ {msg}")
            else:
                QMessageBox.warning(self, "Restoration Result", f"⚠️ {msg}")
            self.dashboard_view.refresh_system_status()

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
