"""
Settings and Configuration View for OneClick LAN Transfer.
Allows user to adjust themes, transfer port, chunk size, default download path,
and manually manage Windows Firewall rules.
"""

from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QLineEdit, QComboBox, QCheckBox, QFileDialog, QMessageBox, QSpacerItem, QSizePolicy
)
from PySide6.QtCore import Qt, Signal

from app.settings_manager import SettingsManager
from app.network_manager import NetworkManager
from app.firewall_manager import add_firewall_rule, remove_firewall_rule
from ui.worker import FunctionThread

class SettingsView(QWidget):
    request_back = Signal()
    theme_changed = Signal(str)

    def __init__(self, settings_mgr: SettingsManager, network_mgr: NetworkManager, parent=None):
        super().__init__(parent)
        self.settings = settings_mgr
        self.net_mgr = network_mgr
        self._fw_thread = None
        self.init_ui()

    def init_ui(self):
        self.setObjectName("canvas")
        self.setAttribute(Qt.WA_StyledBackground, True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)

        # Header
        hdr = QHBoxLayout()
        self.back_btn = QPushButton("Back")
        self.back_btn.setObjectName("outline")
        self.back_btn.setCursor(Qt.PointingHandCursor)
        self.back_btn.clicked.connect(self.request_back.emit)
        hdr.addWidget(self.back_btn)

        title = QLabel("Settings")
        title.setObjectName("title")
        hdr.addWidget(title)
        hdr.addStretch(1)
        layout.addLayout(hdr)

        # Settings Card
        card = QFrame()
        card.setObjectName("card")
        c_layout = QVBoxLayout(card)
        c_layout.setSpacing(16)

        # Theme
        theme_row = QHBoxLayout()
        theme_row.addWidget(QLabel("UI Color Theme:"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light"])
        cur_theme = self.settings.get("theme", "dark")
        self.theme_combo.setCurrentIndex(0 if cur_theme == "dark" else 1)
        self.theme_combo.currentIndexChanged.connect(self.handle_theme_change)
        theme_row.addWidget(self.theme_combo, 1)
        c_layout.addLayout(theme_row)

        # Transfer Port
        port_row = QHBoxLayout()
        port_row.addWidget(QLabel("Transfer Port (TCP):"))
        self.port_input = QLineEdit(str(self.settings.get("port", 52428)))
        self.port_input.setFixedWidth(100)
        port_row.addWidget(self.port_input)
        port_row.addStretch(1)
        c_layout.addLayout(port_row)

        # Chunk Buffer Size
        chunk_row = QHBoxLayout()
        chunk_row.addWidget(QLabel("Streaming Buffer Size:"))
        self.chunk_combo = QComboBox()
        self.chunk_combo.addItems(["1 MB (Low Memory)", "2 MB (Optimal Gigabit)", "4 MB (High Performance)", "8 MB (Max Throughput)"])
        chunk_row.addWidget(self.chunk_combo, 1)
        c_layout.addLayout(chunk_row)

        # Default Save Directory
        dir_row = QHBoxLayout()
        dir_row.addWidget(QLabel("Default Save Folder:"))
        self.save_dir_input = QLineEdit(self.settings.get("default_save_dir", ""))
        dir_row.addWidget(self.save_dir_input, 1)
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self.browse_save_dir)
        dir_row.addWidget(self.browse_btn)
        c_layout.addLayout(dir_row)

        # Auto Restore Network
        self.auto_restore_chk = QCheckBox("Automatically restore DHCP / original network settings on application exit")
        self.auto_restore_chk.setChecked(bool(self.settings.get("auto_restore_network", True)))
        c_layout.addWidget(self.auto_restore_chk)

        # Checksum
        self.verify_chk = QCheckBox("Enforce cryptographic SHA-256 verification after every transfer")
        self.verify_chk.setChecked(bool(self.settings.get("verify_sha256", True)))
        c_layout.addWidget(self.verify_chk)

        # Firewall Management
        fw_box = QVBoxLayout()
        fw_lbl = QLabel("Windows Defender Firewall")
        fw_lbl.setObjectName("section")
        fw_box.addWidget(fw_lbl)

        fw_btn_row = QHBoxLayout()
        self.add_fw_btn = QPushButton("Allow Port in Firewall (Inbound Rule)")
        self.add_fw_btn.clicked.connect(self.handle_add_firewall)
        fw_btn_row.addWidget(self.add_fw_btn)

        self.del_fw_btn = QPushButton("Remove Application Firewall Rule")
        self.del_fw_btn.setObjectName("danger")
        self.del_fw_btn.clicked.connect(self.handle_remove_firewall)
        fw_btn_row.addWidget(self.del_fw_btn)

        self.restore_btn = QPushButton("Restore original network settings")
        self.restore_btn.setObjectName("danger")
        self.restore_btn.setCursor(Qt.PointingHandCursor)
        self.restore_btn.clicked.connect(self._request_restore)
        fw_btn_row.addWidget(self.restore_btn)
        fw_btn_row.addStretch(1)
        fw_box.addLayout(fw_btn_row)
        c_layout.addLayout(fw_box)

        layout.addWidget(card)

        # Save Button
        save_row = QHBoxLayout()
        self.save_btn = QPushButton("Save Settings")
        self.save_btn.setObjectName("primary")
        self.save_btn.setFixedHeight(44)
        self.save_btn.setCursor(Qt.PointingHandCursor)
        self.save_btn.clicked.connect(self.save_settings)
        save_row.addWidget(self.save_btn)
        save_row.addStretch(1)
        layout.addLayout(save_row)

        layout.addStretch(1)

    def _request_restore(self):
        window = self.window()
        handler = getattr(window, "handle_manual_network_restore", None)
        if handler is not None:
            handler()

    def browse_save_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Save Directory", self.save_dir_input.text())
        if folder:
            self.save_dir_input.setText(folder)

    def handle_theme_change(self, idx: int):
        theme_name = "dark" if idx == 0 else "light"
        self.settings.set("theme", theme_name)
        self.theme_changed.emit(theme_name)

    def handle_add_firewall(self):
        try:
            port = int(self.port_input.text().strip())
        except ValueError:
            port = 52428
        if self._fw_thread is not None and self._fw_thread.isRunning():
            return
        self._fw_thread = FunctionThread(lambda: add_firewall_rule(port), self)
        self._fw_thread.succeeded.connect(self._on_firewall_finished)
        self._fw_thread.failed.connect(self._on_firewall_failed)
        self._fw_thread.start()

    def handle_remove_firewall(self):
        if self._fw_thread is not None and self._fw_thread.isRunning():
            return
        self._fw_thread = FunctionThread(remove_firewall_rule, self)
        self._fw_thread.succeeded.connect(self._on_firewall_finished)
        self._fw_thread.failed.connect(self._on_firewall_failed)
        self._fw_thread.start()

    def _on_firewall_finished(self, outcome):
        ok, msg = outcome
        if ok:
            QMessageBox.information(self, "Firewall", msg or "Firewall change completed.")
        else:
            QMessageBox.warning(self, "Firewall Error", msg or "The firewall command failed.")

    def _on_firewall_failed(self, message: str):
        QMessageBox.warning(self, "Firewall Error", message)

    def save_settings(self):
        try:
            port = int(self.port_input.text().strip())
        except ValueError:
            port = 52428

        self.settings.set("port", port)
        self.settings.set("default_save_dir", self.save_dir_input.text().strip())
        self.settings.set("auto_restore_network", self.auto_restore_chk.isChecked())
        self.settings.set("verify_sha256", self.verify_chk.isChecked())

        QMessageBox.information(self, "Settings Saved", "Your preferences have been saved successfully.")
        self.request_back.emit()
