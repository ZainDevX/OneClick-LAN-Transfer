"""
Host Mode Interface for OneClick LAN Transfer.
Manages network configuration, pairing code display, file queue selection,
and active client monitoring.
"""

from pathlib import Path
from typing import List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QComboBox, QTableWidget, QTableWidgetItem, QFileDialog, QHeaderView,
    QProgressBar, QMessageBox, QApplication
)
from PySide6.QtCore import Qt, Signal

from app.adapter_detection import AdapterInfo
from app.network_manager import NetworkManager
from app.host import HostService
from app.transfer_engine import TransferProgress
from ui.chrome import apply_role
from ui.worker import FunctionThread, HostBridge

class HostView(QWidget):
    request_back = Signal()
    notify_error = Signal(str, str, str)  # (title, what, how)

    def __init__(self, network_manager: NetworkManager, parent=None):
        super().__init__(parent)
        self.net_mgr = network_manager
        self.host_service: Optional[HostService] = None
        self.adapters: List[AdapterInfo] = []
        self.selected_paths: List[str] = []
        self._net_thread: Optional[FunctionThread] = None
        self.bridge = HostBridge(self)
        self.bridge.client_connected.connect(self._on_client_connected)
        self.bridge.client_disconnected.connect(self._on_client_disconnected)
        self.bridge.progress.connect(self._on_progress_update)
        self.bridge.status.connect(self._on_host_status)
        self.bridge.error.connect(self._on_host_error)
        self.init_ui()

    def init_ui(self):
        self.setObjectName("canvas")
        self.setAttribute(Qt.WA_StyledBackground, True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(14)

        # Header with Back button
        hdr_layout = QHBoxLayout()
        self.back_btn = QPushButton("Back")
        self.back_btn.setObjectName("outline")
        self.back_btn.setCursor(Qt.PointingHandCursor)
        self.back_btn.clicked.connect(self.handle_back)
        hdr_layout.addWidget(self.back_btn)

        title = QLabel("Host Mode")
        title.setObjectName("title")
        hdr_layout.addWidget(title)
        hdr_layout.addStretch(1)

        self.service_pill = QLabel("Service Stopped")
        self.service_pill.setObjectName("pill_warning")
        hdr_layout.addWidget(self.service_pill)
        layout.addLayout(hdr_layout)

        # Step 1 Card: Adapter & Network Configuration
        cfg_card = QFrame()
        cfg_card.setObjectName("card")
        cfg_layout = QVBoxLayout(cfg_card)
        cfg_layout.setSpacing(10)

        lbl_step1 = QLabel("1. Select Ethernet Adapter & Start Service")
        lbl_step1.setObjectName("section")
        cfg_layout.addWidget(lbl_step1)

        adapter_row = QHBoxLayout()
        adapter_row.addWidget(QLabel("Ethernet Adapter:"))
        self.adapter_combo = QComboBox()
        self.adapter_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        adapter_row.addWidget(self.adapter_combo, 1)

        self.refresh_adapters_btn = QPushButton("Refresh")
        self.refresh_adapters_btn.clicked.connect(self._request_refresh)
        adapter_row.addWidget(self.refresh_adapters_btn)

        self.start_host_btn = QPushButton("Start Host (Configure 192.168.50.1)")
        self.start_host_btn.setObjectName("primary")
        self.start_host_btn.clicked.connect(self.toggle_host_service)
        adapter_row.addWidget(self.start_host_btn)

        cfg_layout.addLayout(adapter_row)
        layout.addWidget(cfg_card)

        # Step 2 Card: Pairing Code & Connection Status
        self.pairing_card = QFrame()
        self.pairing_card.setObjectName("card")
        pair_layout = QHBoxLayout(self.pairing_card)
        pair_layout.setContentsMargins(20, 15, 20, 15)

        code_box = QVBoxLayout()
        code_box.addWidget(QLabel("Secure Pairing Code for Client:"))
        self.pairing_code_lbl = QLabel("--- ---")
        self.pairing_code_lbl.setObjectName("pairing_code")
        code_box.addWidget(self.pairing_code_lbl)

        btn_row = QHBoxLayout()
        self.copy_code_btn = QPushButton("Copy Code")
        self.copy_code_btn.clicked.connect(self.copy_pairing_code)
        btn_row.addWidget(self.copy_code_btn)

        self.refresh_code_btn = QPushButton("Refresh Code")
        self.refresh_code_btn.clicked.connect(self.refresh_code)
        btn_row.addWidget(self.refresh_code_btn)
        btn_row.addStretch(1)
        code_box.addLayout(btn_row)
        pair_layout.addLayout(code_box, 1)

        client_box = QVBoxLayout()
        client_box.addWidget(QLabel("Connected Client:"))
        self.client_info_lbl = QLabel("Waiting for client connection over Cat6 cable...")
        self.client_info_lbl.setObjectName("muted")
        client_box.addWidget(self.client_info_lbl)
        client_box.addStretch(1)
        pair_layout.addLayout(client_box, 1)

        layout.addWidget(self.pairing_card)

        # Step 3 Card: File Selection Queue
        files_card = QFrame()
        files_card.setObjectName("card")
        files_layout = QVBoxLayout(files_card)

        files_hdr = QHBoxLayout()
        lbl_step3 = QLabel("2. Shared Files and Folders")
        lbl_step3.setObjectName("section")
        files_hdr.addWidget(lbl_step3)
        files_hdr.addStretch(1)

        self.add_files_btn = QPushButton("Add Files...")
        self.add_files_btn.clicked.connect(self.add_files)
        files_hdr.addWidget(self.add_files_btn)

        self.add_folder_btn = QPushButton("Add Folder...")
        self.add_folder_btn.clicked.connect(self.add_folder)
        files_hdr.addWidget(self.add_folder_btn)

        self.clear_files_btn = QPushButton("Clear All")
        self.clear_files_btn.clicked.connect(self.clear_files)
        files_hdr.addWidget(self.clear_files_btn)
        files_layout.addLayout(files_hdr)

        self.files_table = QTableWidget(0, 3)
        self.files_table.setHorizontalHeaderLabels(["Name / Relative Path", "Size", "Status"])
        self.files_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.files_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.files_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        files_layout.addWidget(self.files_table)

        self.total_size_lbl = QLabel("Total: 0 files (0 MB)")
        self.total_size_lbl.setObjectName("muted")
        files_layout.addWidget(self.total_size_lbl)
        layout.addWidget(files_card)

        # Live Transfer Monitor
        self.monitor_card = QFrame()
        self.monitor_card.setObjectName("card")
        mon_layout = QVBoxLayout(self.monitor_card)

        mon_hdr = QHBoxLayout()
        mon_hdr.addWidget(QLabel("Live Transfer Monitor:"))
        self.transfer_speed_lbl = QLabel("0.0 MB/s")
        self.transfer_speed_lbl.setObjectName("speed")
        mon_hdr.addWidget(self.transfer_speed_lbl)
        mon_hdr.addStretch(1)
        self.eta_lbl = QLabel("ETA: --")
        mon_hdr.addWidget(self.eta_lbl)
        mon_layout.addLayout(mon_hdr)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        mon_layout.addWidget(self.progress_bar)

        self.progress_detail_lbl = QLabel("Idle - Ready to stream")
        self.progress_detail_lbl.setObjectName("muted")
        mon_layout.addWidget(self.progress_detail_lbl)
        layout.addWidget(self.monitor_card)
        self.apply_adapters(None)

    def _request_refresh(self):
        window = self.window()
        refresher = getattr(window, "refresh_adapters", None)
        if refresher is not None:
            refresher()

    def apply_adapters(self, adapters):
        """Fill the combo from the shared cache without scanning."""
        if self.host_service and self.host_service.is_running:
            return
        previous_index = None
        current = self.adapter_combo.currentIndex()
        if 0 <= current < len(self.adapters):
            previous_index = self.adapters[current].interface_index

        self.adapters = list(adapters or [])
        self.adapter_combo.blockSignals(True)
        self.adapter_combo.clear()
        if adapters is None:
            self.adapter_combo.addItem("Detecting Ethernet adapters...")
            self.start_host_btn.setEnabled(False)
        elif not self.adapters:
            self.adapter_combo.addItem("No Physical Ethernet Adapter Found")
            self.start_host_btn.setEnabled(False)
        else:
            restore_at = 0
            for position, adapter in enumerate(self.adapters):
                self.adapter_combo.addItem(adapter.display_name(), adapter)
                if adapter.interface_index == previous_index:
                    restore_at = position
            self.adapter_combo.setCurrentIndex(restore_at)
            self.start_host_btn.setEnabled(self._net_thread is None or not self._net_thread.isRunning())
        self.adapter_combo.blockSignals(False)

    def toggle_host_service(self):
        if self.host_service and self.host_service.is_running:
            # Stop Host
            self.stop_host()
        else:
            # Start Host
            self.start_host()

    def start_host(self):
        idx = self.adapter_combo.currentIndex()
        if idx < 0 or not self.adapters:
            return

        adapter = self.adapters[idx]
        if not adapter.is_connected:
            self.service_pill.setText("Cable unplugged — configuring anyway...")
        else:
            self.service_pill.setText("Configuring IP...")
        self.service_pill.setObjectName("pill_warning")
        self.service_pill.setStyle(self.service_pill.style())
        self.start_host_btn.setEnabled(False)
        self.adapter_combo.setEnabled(False)

        self._net_thread = FunctionThread(lambda: self.net_mgr.configure_host_network(adapter), self)
        self._net_thread.succeeded.connect(self._on_host_net_ready)
        self._net_thread.failed.connect(self._on_host_net_failed)
        self._net_thread.start()

    def _on_host_net_failed(self, message: str):
        self._fail_host_config(message)

    def _on_host_net_ready(self, result):
        self._notify_network_changed()
        if not result.ip_verified:
            self._fail_host_config(result.message)
            return
        if result.firewall_ok is False:
            QMessageBox.warning(self, "Firewall Rule Failed", result.message)
        self._start_listener()

    def _start_listener(self):
        self.host_service = HostService(bind_ip="192.168.50.1", port=52428)
        self.host_service.set_shared_paths(self.selected_paths)
        self.host_service.on_client_connected = self.bridge.client_connected.emit
        self.host_service.on_client_disconnected = self.bridge.client_disconnected.emit
        self.host_service.on_progress_update = self.bridge.progress.emit
        self.host_service.on_status_change = self.bridge.status.emit
        self.host_service.on_error = self.bridge.error.emit
        self.service_pill.setText("Starting host...")
        self.host_service.start()

    def _on_host_status(self, text: str):
        if text.startswith("Ready on") and self.host_service is not None:
            self.pairing_code_lbl.setText(self.host_service.display_code)
            self.start_host_btn.setText("Stop Host Service")
            self.start_host_btn.setObjectName("danger")
            self.start_host_btn.setStyle(self.start_host_btn.style())
            self.start_host_btn.setEnabled(True)
            self.adapter_combo.setEnabled(False)
            self.service_pill.setText(f"Host Active ({self.host_service.bind_ip})")
            self.service_pill.setObjectName("pill_success")
            self.service_pill.setStyle(self.service_pill.style())

    def _on_host_error(self, message: str):
        self._fail_host_config(message)

    def _fail_host_config(self, message: str):
        self._release_host_service()
        self.start_host_btn.setText("Start Host (Configure 192.168.50.1)")
        self.start_host_btn.setObjectName("primary")
        self.start_host_btn.setStyle(self.start_host_btn.style())
        self.start_host_btn.setEnabled(True)
        self.adapter_combo.setEnabled(True)
        self.service_pill.setText("Config Failed")
        self.service_pill.setObjectName("pill_danger")
        self.service_pill.setStyle(self.service_pill.style())
        self.pairing_code_lbl.setText("--- ---")
        QMessageBox.critical(self, "Host Did Not Start", message)

    def _notify_network_changed(self):
        window = self.window()
        invalidate = getattr(window, "invalidate_adapters", None)
        if invalidate is not None:
            invalidate()

    def _release_host_service(self):
        service = self.host_service
        self.host_service = None
        if service is None:
            return
        service.on_client_connected = None
        service.on_client_disconnected = None
        service.on_progress_update = None
        service.on_status_change = None
        service.on_error = None
        service.stop()

    def stop_host(self):
        self._release_host_service()

        self.start_host_btn.setText("Start Host (Configure 192.168.50.1)")
        self.start_host_btn.setObjectName("primary")
        self.start_host_btn.setStyle(self.start_host_btn.style())
        self.start_host_btn.setEnabled(bool(self.adapters))
        self.adapter_combo.setEnabled(True)

        self.service_pill.setText("Service Stopped")
        self.service_pill.setObjectName("pill_warning")
        self.service_pill.setStyle(self.service_pill.style())
        self.client_info_lbl.setText("Waiting for client connection over Cat6 cable...")
        self.pairing_code_lbl.setText("--- ---")

    def _on_client_connected(self, addr: str):
        self.client_info_lbl.setText(f"Client Connected: {addr}")
        apply_role(self.client_info_lbl, "statusGood")

    def _on_client_disconnected(self):
        self.client_info_lbl.setText("Client Disconnected. Waiting for reconnection...")
        apply_role(self.client_info_lbl, "muted")

    def _on_progress_update(self, p: TransferProgress):
        self.progress_bar.setValue(int(p.percentage))
        self.transfer_speed_lbl.setText(f"{p.speed_mb_s:.1f} MB/s")
        self.progress_detail_lbl.setText(
            f"Streaming: {p.current_file_name} ({p.file_bytes_transferred / (1024*1024):.1f} MB / {p.file_total_bytes / (1024*1024):.1f} MB)"
        )
        if p.eta_seconds > 0:
            mins, secs = divmod(p.eta_seconds, 60)
            self.eta_lbl.setText(f"ETA: {mins:02d}:{secs:02d}")
        else:
            self.eta_lbl.setText("ETA: --")

    def copy_pairing_code(self):
        code = self.pairing_code_lbl.text()
        if code and code != "--- ---":
            QApplication.clipboard().setText(code)

    def refresh_code(self):
        if self.host_service:
            new_code = self.host_service.refresh_pairing_code()
            self.pairing_code_lbl.setText(new_code)

    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select Files to Share")
        if files:
            self.selected_paths.extend(files)
            self.update_files_table()

    def add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder to Share")
        if folder:
            self.selected_paths.append(folder)
            self.update_files_table()

    def clear_files(self):
        self.selected_paths.clear()
        self.update_files_table()

    def update_files_table(self):
        self.files_table.setRowCount(0)
        total_bytes = 0

        for p_str in self.selected_paths:
            p = Path(p_str)
            if not p.exists():
                continue

            row = self.files_table.rowCount()
            self.files_table.insertRow(row)

            if p.is_file():
                size = p.stat().st_size
                total_bytes += size
                size_str = f"{size / (1024*1024):.2f} MB" if size < 1024**3 else f"{size / (1024**3):.2f} GB"
                self.files_table.setItem(row, 0, QTableWidgetItem(p.name))
                self.files_table.setItem(row, 1, QTableWidgetItem(size_str))
                self.files_table.setItem(row, 2, QTableWidgetItem("Ready"))
            else:
                self.files_table.setItem(row, 0, QTableWidgetItem(f"{p.name} (Folder)"))
                self.files_table.setItem(row, 1, QTableWidgetItem("Folder"))
                self.files_table.setItem(row, 2, QTableWidgetItem("Ready"))

        total_mb = total_bytes / (1024 * 1024)
        total_gb = total_bytes / (1024 ** 3)
        size_display = f"{total_gb:.2f} GB" if total_gb >= 1.0 else f"{total_mb:.1f} MB"
        self.total_size_lbl.setText(f"Total: {len(self.selected_paths)} items ({size_display})")

        if self.host_service:
            self.host_service.set_shared_paths(self.selected_paths)

    def can_leave(self) -> bool:
        if self.host_service and self.host_service.is_running:
            reply = QMessageBox.question(
                self,
                "Stop Host Service?",
                "Host service is currently active. Do you want to stop it and leave Host Mode?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return False
            self.stop_host()
        return True

    def handle_back(self):
        if self.can_leave():
            self.request_back.emit()
