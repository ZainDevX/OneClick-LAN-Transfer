"""
Host Mode Interface for OneClick LAN Transfer.
Manages network configuration, pairing code display, file queue selection,
and active client monitoring.

The screen follows the Starbucks-inspired host mock: cream canvas, white
cards, and the same controls the transfer service already uses.
"""

from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import QEvent, QSize, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPainter
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QFrame, QHBoxLayout, QHeaderView,
    QLabel, QMessageBox, QProgressBar, QPushButton, QScrollArea, QSizePolicy,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget
)

from app.adapter_detection import AdapterInfo
from app.host import HostService
from app.network_manager import NetworkManager
from app.transfer_engine import TransferProgress
from ui.chrome import apply_role
from ui.icons import CircleIcon, IconWidget, StatusDot, make_icon
from ui.worker import FunctionThread, HostBridge


def _adapter_label(adapter: AdapterInfo) -> str:
    state = "Cable Connected" if adapter.is_connected else "Cable Disconnected"
    description = adapter.interface_description or adapter.name
    return f"{adapter.name} - {description} ({state})"


def _spaced_code(code: str) -> str:
    """Show a 6-digit code as grouped, tracked digits. The clipboard keeps the original."""
    digits = [character for character in code if character.isdigit()]
    if len(digits) < 6:
        return "–    –    –     –     –    –    –"
    left = "   ".join(digits[:3])
    right = "   ".join(digits[3:6])
    return f"{left}     –     {right}"


class StepBadge(QWidget):
    def __init__(self, number: str, parent=None):
        super().__init__(parent)
        self.number = number
        self.setFixedSize(26, 26)

    def paintEvent(self, event):
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#006241"))
        painter.drawEllipse(self.rect().adjusted(0, 0, -1, -1))
        painter.setPen(QColor("#FFFFFF"))
        font = painter.font()
        font.setPixelSize(13)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignCenter, self.number)
        painter.end()


class StatusMark(QWidget):
    """Small status glyph for the adapter banner: check, wait, or alert."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._state = "wait"
        self.setFixedSize(18, 18)

    def set_state(self, state: str) -> None:
        self._state = state
        self.update()

    def paintEvent(self, event):
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        colors = {"ok": "#00754A", "wait": "#8A9690", "bad": "#C82014"}
        painter.setBrush(QColor(colors.get(self._state, "#C4A35A")))
        painter.drawEllipse(self.rect().adjusted(0, 0, -1, -1))
        if self._state == "ok":
            pen_color = QColor("#FFFFFF")
            pen = painter.pen()
            pen.setColor(pen_color)
            pen.setWidthF(1.8)
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(pen)
            rect = self.rect()
            painter.drawLine(
                int(rect.left() + rect.width() * 0.28),
                int(rect.center().y() + 1),
                int(rect.left() + rect.width() * 0.44),
                int(rect.top() + rect.height() * 0.66),
            )
            painter.drawLine(
                int(rect.left() + rect.width() * 0.44),
                int(rect.top() + rect.height() * 0.66),
                int(rect.left() + rect.width() * 0.74),
                int(rect.top() + rect.height() * 0.34),
            )
        painter.end()


class _EmptyFiles(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("emptyState")
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(4)
        layout.addStretch(1)
        layout.addWidget(IconWidget("folder", 34, "#A39E96"), 0, Qt.AlignCenter)
        title = QLabel("No files shared yet.")
        title.setObjectName("emptyTitle")
        title.setAlignment(Qt.AlignCenter)
        hint = QLabel("Add files or folders to start sharing.")
        hint.setObjectName("emptyHint")
        hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        layout.addWidget(hint)
        layout.addStretch(1)


def _card() -> tuple[QFrame, QVBoxLayout]:
    card = QFrame()
    card.setObjectName("hostCard")
    card.setAttribute(Qt.WA_StyledBackground, True)
    layout = QVBoxLayout(card)
    layout.setContentsMargins(16, 12, 16, 12)
    layout.setSpacing(10)
    return card, layout


def _section_row(number: str, text: str) -> QHBoxLayout:
    row = QHBoxLayout()
    row.setSpacing(10)
    row.addWidget(StepBadge(number))
    label = QLabel(text)
    label.setObjectName("hostSection")
    row.addWidget(label)
    row.addStretch(1)
    return row


def _pill(text: str, icon: str, handler, primary: bool = False) -> QPushButton:
    button = QPushButton(text)
    if primary:
        button.setObjectName("primary")
        color = "#FFFFFF"
    else:
        color = "#1A1A1A"
    button.setIcon(make_icon(icon, 16, color))
    button.setIconSize(QSize(16, 16))
    button.setCursor(Qt.PointingHandCursor)
    button.setFocusPolicy(Qt.NoFocus)
    button.clicked.connect(handler)
    return button


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
        self._pairing_plain = "--- ---"
        self.bridge = HostBridge(self)
        self.bridge.client_connected.connect(self._on_client_connected)
        self.bridge.client_disconnected.connect(self._on_client_disconnected)
        self.bridge.progress.connect(self._on_progress_update)
        self.bridge.status.connect(self._on_host_status)
        self.bridge.error.connect(self._on_host_error)
        self.init_ui()

    def init_ui(self):
        self.setObjectName("hostCanvas")
        self.setAttribute(Qt.WA_StyledBackground, True)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setObjectName("hostScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.viewport().setObjectName("hostCanvas")
        scroll.viewport().setAttribute(Qt.WA_StyledBackground, True)
        outer.addWidget(scroll)

        page = QWidget()
        page.setObjectName("hostCanvas")
        page.setAttribute(Qt.WA_StyledBackground, True)
        scroll.setWidget(page)

        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 16, 24, 14)
        layout.setSpacing(10)

        header = QHBoxLayout()
        header.setSpacing(14)
        header.addWidget(CircleIcon("stack", 52))
        titles = QVBoxLayout()
        titles.setSpacing(2)
        title = QLabel("HOST MODE — File Sharing Server")
        title.setObjectName("hostTitle")
        subtitle = QLabel("Share files and folders with other PCs over your local network.")
        subtitle.setObjectName("hostSubtitle")
        subtitle.setWordWrap(True)
        titles.addWidget(title)
        titles.addWidget(subtitle)
        header.addLayout(titles, 1)
        layout.addLayout(header)

        layout.addWidget(self._adapter_card())
        layout.addWidget(self._pairing_card())
        layout.addWidget(self._files_card())
        layout.addWidget(self._monitor_card())
        layout.addStretch(1)
        self.apply_adapters(None)

    def _adapter_card(self) -> QFrame:
        card, layout = _card()
        layout.addLayout(_section_row("1", "Select Ethernet Adapter & Start Service"))

        adapter_row = QHBoxLayout()
        adapter_row.setSpacing(10)
        adapter_label = QLabel("Ethernet Adapter:")
        adapter_label.setObjectName("fieldLabel")
        adapter_row.addWidget(adapter_label)

        self.adapter_combo = QComboBox()
        self.adapter_combo.setIconSize(QSize(16, 16))
        self.adapter_combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.adapter_combo.setMinimumContentsLength(18)
        self.adapter_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.adapter_combo.currentIndexChanged.connect(self._on_adapter_changed)
        adapter_row.addWidget(self.adapter_combo, 1)

        self.refresh_adapters_btn = _pill("Refresh", "refresh", self._request_refresh)
        adapter_row.addWidget(self.refresh_adapters_btn)

        self.start_host_btn = _pill("Start Host (Configure 192.168.50.1)", "play", self.toggle_host_service, primary=True)
        adapter_row.addWidget(self.start_host_btn)
        layout.addLayout(adapter_row)

        self.link_banner = QFrame()
        self.link_banner.setObjectName("linkWait")
        self.link_banner.setAttribute(Qt.WA_StyledBackground, True)
        banner = QHBoxLayout(self.link_banner)
        banner.setContentsMargins(14, 10, 14, 10)
        banner.setSpacing(10)
        self.status_mark = StatusMark()
        banner.addWidget(self.status_mark)
        self.service_pill = QLabel("Detecting adapter…")
        self.service_pill.setObjectName("statusWait")
        banner.addWidget(self.service_pill)
        divider = QFrame()
        divider.setObjectName("vrule")
        divider.setFixedSize(1, 16)
        banner.addWidget(divider)
        ip_prefix = QLabel("IP Address:")
        ip_prefix.setObjectName("fieldLabel")
        banner.addWidget(ip_prefix)
        self.ip_value = QLabel("—")
        self.ip_value.setObjectName("ipValue")
        banner.addWidget(self.ip_value)
        banner.addStretch(1)
        layout.addWidget(self.link_banner)
        return card

    def _pairing_card(self) -> QFrame:
        card, layout = _card()
        body = QHBoxLayout()
        body.setSpacing(18)

        left = QVBoxLayout()
        left.setSpacing(12)
        left.addLayout(_section_row("2", "Secure Pairing Code for Client"))

        code_row = QHBoxLayout()
        code_row.setSpacing(10)
        code_box = QFrame()
        code_box.setObjectName("codeBox")
        code_box.setAttribute(Qt.WA_StyledBackground, True)
        code_layout = QHBoxLayout(code_box)
        code_layout.setContentsMargins(16, 8, 16, 8)
        self.pairing_code_lbl = QLabel(_spaced_code(self._pairing_plain))
        self.pairing_code_lbl.setObjectName("pairing_code")
        self.pairing_code_lbl.setAlignment(Qt.AlignCenter)
        code_layout.addWidget(self.pairing_code_lbl)
        code_row.addWidget(code_box)

        self.copy_code_btn = _pill("Copy Code", "copy", self.copy_pairing_code)
        code_row.addWidget(self.copy_code_btn)
        self.refresh_code_btn = _pill("Refresh Code", "refresh", self.refresh_code)
        code_row.addWidget(self.refresh_code_btn)
        code_row.addStretch(1)
        left.addLayout(code_row)
        body.addLayout(left, 3)

        rule = QFrame()
        rule.setObjectName("vrule")
        rule.setFixedWidth(1)
        rule.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        body.addWidget(rule)

        client_col = QVBoxLayout()
        client_col.setSpacing(6)
        client_head = QHBoxLayout()
        client_head.setSpacing(8)
        client_head.addWidget(StatusDot("#00754A", 10))
        client_title = QLabel("Connected Client:")
        client_title.setObjectName("clientTitle")
        client_head.addWidget(client_title)
        client_head.addStretch(1)
        client_col.addLayout(client_head)
        self.client_info_lbl = QLabel("Waiting for client connection over Cat6 cable...")
        self.client_info_lbl.setObjectName("muted")
        self.client_info_lbl.setWordWrap(True)
        client_col.addWidget(self.client_info_lbl)
        client_col.addStretch(1)
        body.addLayout(client_col, 2)
        layout.addLayout(body)
        return card

    def _files_card(self) -> QFrame:
        card, layout = _card()
        files_hdr = _section_row("3", "Shared Files and Folders")
        self.add_files_btn = _pill("Add Files...", "plus", self.add_files)
        self.add_folder_btn = _pill("Add Folder...", "folder", self.add_folder)
        self.clear_files_btn = _pill("Clear All", "trash", self.clear_files)
        files_hdr.addWidget(self.add_files_btn)
        files_hdr.addWidget(self.add_folder_btn)
        files_hdr.addWidget(self.clear_files_btn)
        layout.addLayout(files_hdr)

        self.files_table = QTableWidget(0, 3)
        self.files_table.setHorizontalHeaderLabels(["Name / Relative Path", "Size", "Status"])
        header = self.files_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setStretchLastSection(False)
        header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.files_table.horizontalHeaderItem(1).setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.files_table.horizontalHeaderItem(2).setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.files_table.verticalHeader().setVisible(False)
        self.files_table.verticalHeader().setDefaultSectionSize(36)
        self.files_table.setShowGrid(False)
        self.files_table.setAlternatingRowColors(True)
        self.files_table.setSelectionMode(QTableWidget.NoSelection)
        self.files_table.setFocusPolicy(Qt.NoFocus)
        self.files_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.files_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.files_table.setFixedHeight(148)
        self._empty = _EmptyFiles(self.files_table.viewport())
        self.files_table.viewport().installEventFilter(self)
        layout.addWidget(self.files_table)

        self.total_size_lbl = QLabel("Total: 0 files (0 MB)")
        self.total_size_lbl.setObjectName("muted")
        self.total_size_lbl.hide()
        layout.addWidget(self.total_size_lbl)
        return card

    def _monitor_card(self) -> QFrame:
        card, layout = _card()
        layout.setSpacing(10)
        mon_hdr = QHBoxLayout()
        mon_hdr.setSpacing(8)
        mon_hdr.addWidget(IconWidget("monitor", 18, "#006241"))
        monitor_title = QLabel("Live Transfer Monitor:")
        monitor_title.setObjectName("speed")
        mon_hdr.addWidget(monitor_title)
        self.transfer_speed_lbl = QLabel("0.0 MB/s")
        self.transfer_speed_lbl.setObjectName("speed")
        mon_hdr.addWidget(self.transfer_speed_lbl)
        mon_hdr.addStretch(1)
        self.eta_lbl = QLabel("ETA: --")
        self.eta_lbl.setObjectName("hostEta")
        mon_hdr.addWidget(self.eta_lbl)
        layout.addLayout(mon_hdr)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)

        detail_row = QHBoxLayout()
        detail_row.setSpacing(8)
        detail_row.addWidget(StatusDot("#2EAE70", 10))
        self.progress_detail_lbl = QLabel("Idle - Ready to stream")
        self.progress_detail_lbl.setObjectName("muted")
        detail_row.addWidget(self.progress_detail_lbl)
        detail_row.addStretch(1)
        layout.addLayout(detail_row)
        return card

    def eventFilter(self, obj, event):
        if obj is self.files_table.viewport() and event.type() == QEvent.Resize:
            self._empty.setGeometry(obj.rect())
        return super().eventFilter(obj, event)

    def _show_code(self, code: str) -> None:
        self._pairing_plain = code
        self.pairing_code_lbl.setText(_spaced_code(code))

    def _set_start_button(self, running: bool) -> None:
        if running:
            self.start_host_btn.setText("Stop Host Service")
            self.start_host_btn.setIcon(make_icon("stop", 16, "#FFFFFF"))
            apply_role(self.start_host_btn, "danger")
        else:
            self.start_host_btn.setText("Start Host (Configure 192.168.50.1)")
            self.start_host_btn.setIcon(make_icon("play", 16, "#FFFFFF"))
            apply_role(self.start_host_btn, "primary")

    def _set_service_status(self, text: str, kind: str, ip: str) -> None:
        roles = {"ok": "statusOk", "wait": "statusWait", "bad": "statusBad"}
        banners = {"ok": "linkOk", "wait": "linkWait", "bad": "linkBad"}
        self.service_pill.setText(text)
        apply_role(self.service_pill, roles[kind])
        apply_role(self.link_banner, banners[kind])
        self.ip_value.setText(ip)
        self.status_mark.set_state(kind)

    def _show_idle_link(self) -> None:
        if self.host_service and self.host_service.is_running:
            return
        if not self.adapters:
            detecting = (
                self.adapter_combo.count() == 1
                and self.adapter_combo.itemText(0).startswith("Detecting")
            )
            if detecting:
                self._set_service_status("Detecting adapter…", "wait", "—")
            else:
                self._set_service_status("No adapter found", "bad", "—")
            return
        index = self.adapter_combo.currentIndex()
        adapter = self.adapters[index] if 0 <= index < len(self.adapters) else None
        if adapter is not None and adapter.is_connected:
            ip = adapter.config.ipv4_address or "—"
            self._set_service_status("Connected", "ok", ip)
        else:
            self._set_service_status("Cable disconnected", "wait", "—")

    def _on_adapter_changed(self, _index: int) -> None:
        self._show_idle_link()

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
            icon = make_icon("ethernet", 16, "#006241")
            for position, adapter in enumerate(self.adapters):
                self.adapter_combo.addItem(icon, _adapter_label(adapter), adapter)
                if adapter.interface_index == previous_index:
                    restore_at = position
            self.adapter_combo.setCurrentIndex(restore_at)
            self.start_host_btn.setEnabled(self._net_thread is None or not self._net_thread.isRunning())
        self.adapter_combo.blockSignals(False)
        self._show_idle_link()

    def toggle_host_service(self):
        if self.host_service and self.host_service.is_running:
            self.stop_host()
        else:
            self.start_host()

    def start_host(self):
        idx = self.adapter_combo.currentIndex()
        if idx < 0 or not self.adapters:
            return

        adapter = self.adapters[idx]
        if not adapter.is_connected:
            self._set_service_status("Cable unplugged — configuring anyway…", "wait", "—")
        else:
            self._set_service_status("Configuring network…", "wait", "—")
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
        self._set_service_status("Starting host…", "wait", "—")
        self.host_service.start()

    def _on_host_status(self, text: str):
        if text.startswith("Ready on") and self.host_service is not None:
            self._show_code(self.host_service.display_code)
            self._set_start_button(True)
            self.start_host_btn.setEnabled(True)
            self.adapter_combo.setEnabled(False)
            self._set_service_status("Connected", "ok", self.host_service.bind_ip)

    def _on_host_error(self, message: str):
        self._fail_host_config(message)

    def _fail_host_config(self, message: str):
        self._release_host_service()
        self._set_start_button(False)
        self.start_host_btn.setEnabled(True)
        self.adapter_combo.setEnabled(True)
        self._set_service_status("Configuration failed", "bad", "—")
        self._show_code("--- ---")
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
        self._set_start_button(False)
        self.start_host_btn.setEnabled(bool(self.adapters))
        self.adapter_combo.setEnabled(True)
        self.client_info_lbl.setText("Waiting for client connection over Cat6 cable...")
        apply_role(self.client_info_lbl, "muted")
        self._show_code("--- ---")
        self._show_idle_link()

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
        code = self._pairing_plain
        digits = "".join(character for character in code if character.isdigit())
        if len(digits) == 6:
            QApplication.clipboard().setText(code)

    def refresh_code(self):
        if self.host_service:
            self._show_code(self.host_service.refresh_pairing_code())

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
                self.files_table.setItem(row, 0, self._cell(p.name))
                self.files_table.setItem(row, 1, self._cell(size_str, Qt.AlignRight | Qt.AlignVCenter))
                self.files_table.setItem(row, 2, self._cell("Ready", Qt.AlignRight | Qt.AlignVCenter, "#006241"))
            else:
                self.files_table.setItem(row, 0, self._cell(f"{p.name} (Folder)"))
                self.files_table.setItem(row, 1, self._cell("Folder", Qt.AlignRight | Qt.AlignVCenter))
                self.files_table.setItem(row, 2, self._cell("Ready", Qt.AlignRight | Qt.AlignVCenter, "#006241"))

        total_mb = total_bytes / (1024 * 1024)
        total_gb = total_bytes / (1024 ** 3)
        size_display = f"{total_gb:.2f} GB" if total_gb >= 1.0 else f"{total_mb:.1f} MB"
        self.total_size_lbl.setText(f"Total: {len(self.selected_paths)} items ({size_display})")
        self.total_size_lbl.setVisible(bool(self.selected_paths))
        self._empty.setVisible(self.files_table.rowCount() == 0)
        self._empty.setGeometry(self.files_table.viewport().rect())

        if self.host_service:
            self.host_service.set_shared_paths(self.selected_paths)

    def _cell(self, text: str, alignment=Qt.AlignLeft | Qt.AlignVCenter, color: str | None = None) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        item.setTextAlignment(alignment)
        item.setFlags(Qt.ItemIsEnabled)
        if color:
            item.setForeground(QBrush(QColor(color)))
        return item

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
