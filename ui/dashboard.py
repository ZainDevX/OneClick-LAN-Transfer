"""
Home screen for OneClick LAN Transfer.

Host and Client are chosen from two cards. Adapter status and the signed-in
Windows role stay visible above them. About and Help live in the sidebar and
are not part of this page.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, QSize, Signal

from app.permissions import is_admin
from ui.icons import CircleIcon, IconWidget, make_icon


def _rule() -> QFrame:
    line = QFrame()
    line.setObjectName("rule")
    line.setFixedHeight(1)
    line.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    return line


def _feature(text: str) -> QHBoxLayout:
    row = QHBoxLayout()
    row.setSpacing(12)
    row.addWidget(IconWidget("check", 22, "#006241"))
    label = QLabel(text)
    label.setObjectName("feature")
    row.addWidget(label, 1)
    return row


class DashboardView(QWidget):
    request_host_mode = Signal()
    request_client_mode = Signal()
    request_restore_network = Signal()
    request_settings = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("canvas")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(36, 28, 32, 22)
        main_layout.setSpacing(16)

        title = QLabel("OneClick LAN Transfer")
        title.setObjectName("heroTitle")
        subtitle = QLabel("Direct high-speed file transfer between Windows PCs without passwords or cloud.")
        subtitle.setObjectName("heroSubtitle")
        subtitle.setWordWrap(True)
        main_layout.addWidget(title)
        main_layout.addWidget(subtitle)
        main_layout.addWidget(_rule())

        self.status_banner = QFrame()
        self.status_banner.setObjectName("statusCard")
        self.status_banner.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        banner = QHBoxLayout(self.status_banner)
        banner.setContentsMargins(18, 14, 16, 14)
        banner.setSpacing(14)

        banner.addWidget(IconWidget("ethernet", 28, "#006241"))
        banner.addWidget(self._vline())

        names = QVBoxLayout()
        names.setSpacing(2)
        self.adapter_status_lbl = QLabel("Detecting Ethernet adapters...")
        self.adapter_status_lbl.setObjectName("statusTitle")
        self.adapter_detail_lbl = QLabel("")
        self.adapter_detail_lbl.setObjectName("statusDetail")
        names.addWidget(self.adapter_status_lbl)
        names.addWidget(self.adapter_detail_lbl)
        banner.addLayout(names, 1)

        banner.addWidget(self._vline())
        banner.addWidget(IconWidget("user", 26, "#006241"))
        self.admin_badge = QLabel("Standard User (Elevation on Demand)")
        self.admin_badge.setObjectName("userStatus")
        banner.addWidget(self.admin_badge)

        self.refresh_adapters_btn = QPushButton("Refresh")
        self.refresh_adapters_btn.setObjectName("outline")
        self.refresh_adapters_btn.setIcon(make_icon("refresh", 16, "#006241"))
        self.refresh_adapters_btn.setIconSize(QSize(16, 16))
        self.refresh_adapters_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_adapters_btn.setFixedHeight(36)
        self.refresh_adapters_btn.clicked.connect(self.request_manual_refresh)
        banner.addWidget(self.refresh_adapters_btn)
        main_layout.addWidget(self.status_banner)

        cards = QHBoxLayout()
        cards.setSpacing(22)
        cards.addWidget(self._mode_card(
            "monitor",
            "Host Mode",
            "Share files or entire folders from this computer.",
            [
                "Automatically sets IP to 192.168.50.1",
                "Generates secure 6-digit pairing code",
                "Direct TLS-encrypted streaming",
                "Saturation for Gigabit Ethernet",
            ],
            "Select HOST Mode",
            "host",
        ))
        cards.addWidget(self._mode_card(
            "laptop",
            "Client Mode",
            "Receive files on this computer from the Host.",
            [
                "Automatically sets IP to 192.168.50.2",
                "Connects securely using the pairing code",
                "Browse and select files to transfer",
                "Resume partial downloads and verify SHA-256",
            ],
            "Select CLIENT Mode",
            "client",
        ))
        main_layout.addLayout(cards, 1)

        info = QFrame()
        info.setObjectName("infoBanner")
        info.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        info_row = QHBoxLayout(info)
        info_row.setContentsMargins(16, 12, 16, 12)
        info_row.setSpacing(10)
        info_row.addWidget(IconWidget("infoFill", 22, "#006241"))
        tip = QLabel("For the best performance, use a wired Ethernet connection.")
        tip.setObjectName("infoText")
        info_row.addWidget(tip, 1)
        main_layout.addWidget(info)

        # Kept so network restore can still be disabled while it runs.
        # The control itself lives on the Settings page, not on this screen.
        self.restore_btn = QPushButton("Restore original network settings")
        self.restore_btn.hide()
        self.restore_btn.clicked.connect(self.request_restore_network.emit)

        self.refresh_admin_badge()

    def _vline(self) -> QFrame:
        line = QFrame()
        line.setFixedWidth(1)
        line.setMinimumHeight(36)
        line.setStyleSheet("background-color: #E6E1DA; border: none;")
        return line

    def _mode_card(self, icon: str, title: str, subtitle: str, features: list[str], button_text: str, mode: str) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 22, 22, 20)
        layout.setSpacing(14)

        header = QHBoxLayout()
        header.setSpacing(14)
        header.addWidget(CircleIcon(icon, 64))
        text = QVBoxLayout()
        text.setSpacing(2)
        heading = QLabel(title)
        heading.setObjectName("cardTitle")
        detail = QLabel(subtitle)
        detail.setObjectName("cardSubtitle")
        detail.setWordWrap(True)
        text.addWidget(heading)
        text.addWidget(detail)
        header.addLayout(text, 1)
        layout.addLayout(header)
        layout.addWidget(_rule())

        for feature in features:
            layout.addLayout(_feature(feature))

        layout.addStretch(1)

        button = QPushButton(button_text)
        button.setObjectName("primary")
        button.setCursor(Qt.PointingHandCursor)
        button.setFixedHeight(52)
        if mode == "host":
            self.host_btn = button
            button.clicked.connect(self.request_host_mode.emit)
        else:
            self.client_btn = button
            button.clicked.connect(self.request_client_mode.emit)
        layout.addWidget(button)
        return card

    def request_manual_refresh(self):
        window = self.window()
        refresher = getattr(window, "refresh_adapters", None)
        if refresher is not None:
            self.adapter_status_lbl.setText("Refreshing Ethernet adapters...")
            self.adapter_detail_lbl.setText("")
            refresher()

    def refresh_admin_badge(self):
        if is_admin():
            self.admin_badge.setText("Administrator")
        else:
            self.admin_badge.setText("Standard User (Elevation on Demand)")

    def apply_adapters(self, adapters, scanning: bool = False):
        """Show the shared cache. This does not start a scan."""
        if adapters is None:
            if scanning:
                self.adapter_status_lbl.setText("Detecting Ethernet adapters...")
                self.adapter_detail_lbl.setText("")
            return
        if not adapters:
            self.adapter_status_lbl.setText("No Ethernet adapter detected")
            self.adapter_detail_lbl.setText("Connect a USB LAN adapter or check the cable.")
            return
        connected = [adapter for adapter in adapters if adapter.is_connected]
        adapter = connected[0] if connected else adapters[0]
        state = "Connected" if adapter.is_connected else "Cable Disconnected"
        self.adapter_status_lbl.setText(f"Detected: {adapter.name}")
        detail = adapter.interface_description or adapter.name
        self.adapter_detail_lbl.setText(f"{detail} [{state}]")

    def show_adapter_error(self, message: str):
        self.adapter_status_lbl.setText("Adapter check error")
        self.adapter_detail_lbl.setText(message)
