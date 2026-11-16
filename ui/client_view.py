"""
Client Mode Interface for OneClick LAN Transfer.
Handles automatic 192.168.50.2 network configuration, Host pairing code authentication,
remote file browsing, destination folder selection, and streaming transfer progress.
"""

from pathlib import Path
import shutil
from typing import List, Optional, Dict, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QComboBox, QLineEdit, QTableWidget, QTableWidgetItem, QFileDialog,
    QHeaderView, QProgressBar, QMessageBox, QApplication
)
from PySide6.QtCore import Qt, Signal

from app.adapter_detection import get_physical_ethernet_adapters, AdapterInfo
from app.network_manager import NetworkManager
from app.client import ClientService
from app.transfer_engine import TransferProgress
from app.error_handler import get_error

class ClientView(QWidget):
    request_back = Signal()
    notify_error = Signal(str, str, str)

    def __init__(self, network_manager: NetworkManager, parent=None):
        super().__init__(parent)
        self.net_mgr = network_manager
        self.client_service: Optional[ClientService] = None
        self.adapters: List[AdapterInfo] = []
        self.remote_files: List[Dict[str, Any]] = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 20, 25, 20)
        layout.setSpacing(14)

        # Header
        hdr_layout = QHBoxLayout()
        self.back_btn = QPushButton("← Back to Menu")
        self.back_btn.clicked.connect(self.handle_back)
        hdr_layout.addWidget(self.back_btn)

        title = QLabel("CLIENT MODE — File Receiver")
        title.setObjectName("title")
        hdr_layout.addWidget(title)
        hdr_layout.addStretch(1)

        self.status_pill = QLabel("Not Connected")
        self.status_pill.setObjectName("pill_warning")
        hdr_layout.addWidget(self.status_pill)
        layout.addLayout(hdr_layout)

        # Step 1: Adapter Selection & Setup
        cfg_card = QFrame()
        cfg_card.setObjectName("card")
        cfg_layout = QVBoxLayout(cfg_card)
        cfg_layout.setSpacing(10)

        lbl_step1 = QLabel("1. Configure Network Adapter")
        lbl_step1.setStyleSheet("font-weight: 600; font-size: 14px; color: #6CCB5F;")
        cfg_layout.addWidget(lbl_step1)

        adapter_row = QHBoxLayout()
        adapter_row.addWidget(QLabel("Ethernet Adapter:"))
        self.adapter_combo = QComboBox()
        adapter_row.addWidget(self.adapter_combo, 1)

        self.refresh_adapters_btn = QPushButton("Refresh")
        self.refresh_adapters_btn.clicked.connect(self.populate_adapters)
        adapter_row.addWidget(self.refresh_adapters_btn)

        self.config_net_btn = QPushButton("Configure Network (192.168.50.2)")
        self.config_net_btn.setObjectName("primary")
        self.config_net_btn.clicked.connect(self.configure_network)
        adapter_row.addWidget(self.config_net_btn)
        cfg_layout.addLayout(adapter_row)
        layout.addWidget(cfg_card)

        # Step 2: Connection & Pairing Code Input
        conn_card = QFrame()
        conn_card.setObjectName("card")
        conn_layout = QVBoxLayout(conn_card)
        conn_layout.setSpacing(10)

        lbl_step2 = QLabel("2. Connect to Host PC")
        lbl_step2.setStyleSheet("font-weight: 600; font-size: 14px; color: #6CCB5F;")
        conn_layout.addWidget(lbl_step2)

        input_row = QHBoxLayout()
        input_row.addWidget(QLabel("Host IP:"))
        self.host_ip_input = QLineEdit("192.168.50.1")
        self.host_ip_input.setFixedWidth(130)
        input_row.addWidget(self.host_ip_input)

        input_row.addWidget(QLabel("Pairing Code:"))
        self.pairing_code_input = QLineEdit()
        self.pairing_code_input.setPlaceholderText("e.g. 748-219")
        self.pairing_code_input.setFixedWidth(140)
        self.pairing_code_input.setStyleSheet("font-family: monospace; font-size: 16px; font-weight: 700; letter-spacing: 2px;")
        input_row.addWidget(self.pairing_code_input)

        self.connect_btn = QPushButton("Connect & Authenticate")
        self.connect_btn.setObjectName("primary")
        self.connect_btn.clicked.connect(self.connect_to_host)
        input_row.addWidget(self.connect_btn)

        self.test_ping_btn = QPushButton("Test Ping")
        self.test_ping_btn.clicked.connect(self.test_connectivity)
        input_row.addWidget(self.test_ping_btn)

        input_row.addStretch(1)
        conn_layout.addLayout(input_row)
        layout.addWidget(conn_card)

        # Step 3: Shared Files & Destination Folder
        files_card = QFrame()
        files_card.setObjectName("card")
        files_layout = QVBoxLayout(files_card)

        files_hdr = QHBoxLayout()
        lbl_step3 = QLabel("3. Available Shared Files on Host")
        lbl_step3.setStyleSheet("font-weight: 600; font-size: 14px; color: #6CCB5F;")
        files_hdr.addWidget(lbl_step3)
        files_hdr.addStretch(1)

        self.fetch_files_btn = QPushButton("🔄 Refresh Files")
        self.fetch_files_btn.clicked.connect(self.fetch_files)
        files_hdr.addWidget(self.fetch_files_btn)
        files_layout.addLayout(files_hdr)

        self.files_table = QTableWidget(0, 3)
        self.files_table.setHorizontalHeaderLabels(["Select", "File Name", "Size"])
        self.files_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.files_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.files_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        files_layout.addWidget(self.files_table)

        # Destination Folder Selector
        dest_row = QHBoxLayout()
        dest_row.addWidget(QLabel("Save To:"))
        default_dl = str(Path.home() / "Downloads" / "OneClickLAN_Transfers")
        self.dest_input = QLineEdit(default_dl)
        dest_row.addWidget(self.dest_input, 1)

        self.browse_dest_btn = QPushButton("Browse...")
        self.browse_dest_btn.clicked.connect(self.browse_destination)
        dest_row.addWidget(self.browse_dest_btn)

        self.disk_space_lbl = QLabel("Free Space: --")
        self.disk_space_lbl.setStyleSheet("font-weight: 500;")
        dest_row.addWidget(self.disk_space_lbl)
        files_layout.addLayout(dest_row)
        layout.addWidget(files_card)

        # Step 4: Transfer Controls & Progress Monitor
        transfer_card = QFrame()
        transfer_card.setObjectName("card")
        trans_layout = QVBoxLayout(transfer_card)

        ctrl_row = QHBoxLayout()
        self.start_transfer_btn = QPushButton("▶️ Start Download")
        self.start_transfer_btn.setObjectName("primary")
        self.start_transfer_btn.setEnabled(False)
        self.start_transfer_btn.clicked.connect(self.start_transfer)
        ctrl_row.addWidget(self.start_transfer_btn)

        self.pause_resume_btn = QPushButton("⏸️ Pause")
        self.pause_resume_btn.setEnabled(False)
        self.pause_resume_btn.clicked.connect(self.toggle_pause)
        ctrl_row.addWidget(self.pause_resume_btn)

        self.cancel_btn = QPushButton("⏹️ Cancel")
        self.cancel_btn.setObjectName("danger")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.cancel_transfer)
        ctrl_row.addWidget(self.cancel_btn)

        ctrl_row.addStretch(1)

        self.speed_lbl = QLabel("0.0 MB/s")
        self.speed_lbl.setStyleSheet("font-weight: 700; font-size: 15px; color: #6CCB5F;")
        ctrl_row.addWidget(self.speed_lbl)

        self.eta_lbl = QLabel("ETA: --")
        ctrl_row.addWidget(self.eta_lbl)
        trans_layout.addLayout(ctrl_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        trans_layout.addWidget(self.progress_bar)

        self.progress_detail_lbl = QLabel("Ready")
        self.progress_detail_lbl.setStyleSheet("color: #888888;")
        trans_layout.addWidget(self.progress_detail_lbl)

        layout.addWidget(transfer_card)

        self.populate_adapters()
        self.update_disk_space()

    def populate_adapters(self):
        self.adapter_combo.clear()
        self.adapters = get_physical_ethernet_adapters()
        if not self.adapters:
            self.adapter_combo.addItem("No Physical Ethernet Adapter Found")
            self.config_net_btn.setEnabled(False)
        else:
            for adp in self.adapters:
                self.adapter_combo.addItem(adp.display_name(), adp)
            self.config_net_btn.setEnabled(True)

    def configure_network(self):
        idx = self.adapter_combo.currentIndex()
        if idx < 0 or not self.adapters:
            return

        adapter = self.adapters[idx]
        try:
            self.status_pill.setText("Configuring...")
            self.status_pill.setObjectName("pill_warning")
            self.status_pill.setStyle(self.status_pill.style())
            QApplication.processEvents()

            ok, msg = self.net_mgr.configure_client_network(adapter)
            QMessageBox.information(self, "Network Configured", f"Client IP configured successfully.\n\n{msg}")
            self.status_pill.setText("Network Configured (192.168.50.2)")
            self.status_pill.setObjectName("pill_success")
            self.status_pill.setStyle(self.status_pill.style())
        except Exception as e:
            QMessageBox.critical(self, "Configuration Error", str(e))
            self.status_pill.setText("Config Error")
            self.status_pill.setObjectName("pill_danger")
            self.status_pill.setStyle(self.status_pill.style())

    def test_connectivity(self):
        target_ip = self.host_ip_input.text().strip()
        ok, msg = self.net_mgr.test_connectivity(target_ip)
        if ok:
            QMessageBox.information(self, "Connectivity Test", f"✅ {msg}")
        else:
            QMessageBox.warning(self, "Connectivity Test Failed", f"⚠️ {msg}")

    def connect_to_host(self):
        host_ip = self.host_ip_input.text().strip()
        pairing_code = self.pairing_code_input.text().strip()

        if not pairing_code:
            QMessageBox.warning(self, "Pairing Code Required", "Please enter the 6-digit pairing code displayed on the Host PC screen.")
            return

        self.client_service = ClientService(
            host_ip=host_ip,
            port=52428,
            destination_dir=self.dest_input.text().strip()
        )

        # Set up callbacks
        self.client_service.on_progress_update = self._on_progress_update
        self.client_service.on_transfer_complete = self._on_transfer_complete
        self.client_service.on_error = self._on_error

        self.status_pill.setText("Authenticating...")
        self.status_pill.setObjectName("pill_warning")
        self.status_pill.setStyle(self.status_pill.style())
        QApplication.processEvents()

        ok, msg = self.client_service.connect_and_authenticate(pairing_code)
        if ok:
            self.status_pill.setText(f"Connected to {host_ip}")
            self.status_pill.setObjectName("pill_success")
            self.status_pill.setStyle(self.status_pill.style())
            self.fetch_files()
        else:
            self.status_pill.setText("Auth Failed")
            self.status_pill.setObjectName("pill_danger")
            self.status_pill.setStyle(self.status_pill.style())
            QMessageBox.critical(self, "Connection / Auth Failed", msg)

    def fetch_files(self):
        if not self.client_service or not self.client_service.is_connected:
            return

        ok, files = self.client_service.fetch_shared_files()
        self.remote_files = files
        self.files_table.setRowCount(0)

        for f in files:
            row = self.files_table.rowCount()
            self.files_table.insertRow(row)

            # Checkbox
            chk_item = QTableWidgetItem()
            chk_item.setCheckState(Qt.Checked)
            self.files_table.setItem(row, 0, chk_item)

            # Name
            self.files_table.setItem(row, 1, QTableWidgetItem(f["relative_path"]))

            # Size
            size = f["size_bytes"]
            size_str = f"{size / (1024*1024):.2f} MB" if size < 1024**3 else f"{size / (1024**3):.2f} GB"
            self.files_table.setItem(row, 2, QTableWidgetItem(size_str))

        if files:
            self.start_transfer_btn.setEnabled(True)

    def browse_destination(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Destination Folder", self.dest_input.text())
        if folder:
            self.dest_input.setText(folder)
            self.update_disk_space()

    def update_disk_space(self):
        p = Path(self.dest_input.text())
        while not p.exists() and p.parent != p:
            p = p.parent
        try:
            usage = shutil.disk_usage(p)
            free_gb = usage.free / (1024 ** 3)
            self.disk_space_lbl.setText(f"Free: {free_gb:.1f} GB")
        except Exception:
            self.disk_space_lbl.setText("Free: --")

    def start_transfer(self):
        if not self.client_service:
            return

        selected = []
        for r in range(self.files_table.rowCount()):
            chk = self.files_table.item(r, 0)
            if chk and chk.checkState() == Qt.Checked:
                rel = self.files_table.item(r, 1).text()
                selected.append(rel)

        if not selected:
            QMessageBox.warning(self, "No Files Selected", "Please select at least one file to transfer.")
            return

        self.client_service.destination_dir = self.dest_input.text().strip()
        self.start_transfer_btn.setEnabled(False)
        self.pause_resume_btn.setEnabled(True)
        self.cancel_btn.setEnabled(True)

        self.client_service.start_transfer_batch(selected)

    def toggle_pause(self):
        if not self.client_service:
            return

        if self.client_service.is_paused:
            self.client_service.resume()
            self.pause_resume_btn.setText("⏸️ Pause")
        else:
            self.client_service.pause()
            self.pause_resume_btn.setText("▶️ Resume")

    def cancel_transfer(self):
        if self.client_service:
            self.client_service.cancel()
        self.start_transfer_btn.setEnabled(True)
        self.pause_resume_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)
        self.progress_detail_lbl.setText("Transfer cancelled.")

    def _on_progress_update(self, p: TransferProgress):
        self.progress_bar.setValue(int(p.percentage))
        self.speed_lbl.setText(f"{p.speed_mb_s:.1f} MB/s")
        self.progress_detail_lbl.setText(
            f"[{p.file_index}/{p.total_files}] {p.current_file_name} — {p.status} ({p.file_bytes_transferred / (1024*1024):.1f} MB / {p.file_total_bytes / (1024*1024):.1f} MB)"
        )
        if p.eta_seconds > 0:
            mins, secs = divmod(p.eta_seconds, 60)
            self.eta_lbl.setText(f"ETA: {mins:02d}:{secs:02d}")
        else:
            self.eta_lbl.setText("ETA: --")

    def _on_transfer_complete(self):
        self.progress_bar.setValue(100)
        self.speed_lbl.setText("0.0 MB/s")
        self.eta_lbl.setText("Completed")
        self.progress_detail_lbl.setText("✅ All files transferred and SHA-256 verified successfully!")
        self.start_transfer_btn.setEnabled(True)
        self.pause_resume_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)
        QMessageBox.information(self, "Transfer Complete", "All files transferred successfully and passed SHA-256 cryptographic integrity verification!")

    def _on_error(self, err_msg: str):
        self.start_transfer_btn.setEnabled(True)
        self.pause_resume_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)
        QMessageBox.critical(self, "Transfer Error", err_msg)

    def handle_back(self):
        if self.client_service and self.client_service.is_transferring:
            reply = QMessageBox.question(
                self,
                "Cancel Transfer?",
                "File transfer is currently in progress. Do you want to cancel and return to menu?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.client_service.disconnect()
                self.request_back.emit()
        else:
            if self.client_service:
                self.client_service.disconnect()
            self.request_back.emit()
