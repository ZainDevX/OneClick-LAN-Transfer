"""
Main Application Window for OneClick LAN Transfer.
Manages application lifecycle, view transitions, dark/light themes,
and safe network restoration on close.
"""

import logging
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QStackedWidget, QMessageBox
)
from PySide6.QtGui import QIcon

from app.settings_manager import SettingsManager
from app.network_manager import NetworkManager
from ui.styles import DARK_THEME, LIGHT_THEME
from ui.dashboard import DashboardView
from ui.host_view import HostView
from ui.client_view import ClientView
from ui.settings_view import SettingsView
from ui.adapter_directory import AdapterDirectory
from ui.worker import FunctionThread

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
        self.adapter_directory = AdapterDirectory(self)
        self._restore_thread = None

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

    def start_adapter_detection(self):
        """Called after the window is shown. The scan itself is not on the GUI thread."""
        self.adapter_directory.updated.connect(self._publish_adapters)
        self.adapter_directory.failed.connect(self._on_adapter_scan_failed)
        self._publish_adapters()
        self.adapter_directory.revalidate(force=True)

    def refresh_adapters(self):
        self.dashboard_view.adapter_status_lbl.setText("Refreshing Ethernet adapters...")
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
        self.adapter_directory.revalidate()
        self._publish_adapters()

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
            self.dashboard_view.restore_btn.setEnabled(False)
            self._restore_thread = FunctionThread(self.net_mgr.restore_adapter_configuration, self)
            self._restore_thread.succeeded.connect(self._on_restore_finished)
            self._restore_thread.failed.connect(self._on_restore_failed)
            self._restore_thread.start()

    def _on_restore_finished(self, outcome):
        self.dashboard_view.restore_btn.setEnabled(True)
        ok, msg = outcome
        self.invalidate_adapters()
        if ok:
            QMessageBox.information(self, "Network Restored", f"✅ {msg}")
        else:
            QMessageBox.warning(self, "Restoration Result", f"⚠️ {msg}")

    def _on_restore_failed(self, message: str):
        self.dashboard_view.restore_btn.setEnabled(True)
        QMessageBox.warning(self, "Restoration Result", f"⚠️ {message}")

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
