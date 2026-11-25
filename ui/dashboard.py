"""
Dashboard Landing View for OneClick LAN Transfer.
Provides selection between HOST MODE and CLIENT MODE, along with adapter status
and one-click network restoration.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QGridLayout, QSpacerItem, QSizePolicy, QMessageBox
)
from PySide6.QtCore import Qt, Signal

from app.permissions import is_admin

class DashboardView(QWidget):
    # Signals to request mode change
    request_host_mode = Signal()
    request_client_mode = Signal()
    request_restore_network = Signal()
    request_settings = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 25, 30, 25)
        main_layout.setSpacing(20)

        # Header Title
        title_box = QVBoxLayout()
        title_lbl = QLabel("OneClick LAN Transfer")
        title_lbl.setObjectName("title")
        subtitle_lbl = QLabel("Direct high-speed Ethernet transfer between Windows PCs without passwords or cloud.")
        subtitle_lbl.setObjectName("subtitle")
        title_box.addWidget(title_lbl)
        title_box.addWidget(subtitle_lbl)
        main_layout.addLayout(title_box)

        # System Status Banner Card
        self.status_banner = QFrame()
        self.status_banner.setObjectName("banner")
        banner_layout = QHBoxLayout(self.status_banner)
        banner_layout.setContentsMargins(15, 12, 15, 12)

        status_icon = QLabel("🔌")
        status_icon.setStyleSheet("font-size: 20px;")
        banner_layout.addWidget(status_icon)

        self.adapter_status_lbl = QLabel("Detecting Ethernet adapters...")
        self.adapter_status_lbl.setStyleSheet("font-weight: 500;")
        banner_layout.addWidget(self.adapter_status_lbl, 1)

        self.admin_badge = QLabel("Admin Check")
        self.admin_badge.setObjectName("pill_warning")
        banner_layout.addWidget(self.admin_badge)

        self.refresh_adapters_btn = QPushButton("Refresh")
        self.refresh_adapters_btn.setFixedWidth(80)
        self.refresh_adapters_btn.clicked.connect(self.request_manual_refresh)
        banner_layout.addWidget(self.refresh_adapters_btn)

        main_layout.addWidget(self.status_banner)

        # Mode Selection Grid (Host vs Client)
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(20)

        # HOST Card
        self.host_card = QFrame()
        self.host_card.setObjectName("card")
        host_layout = QVBoxLayout(self.host_card)
        host_layout.setContentsMargins(20, 20, 20, 20)
        host_layout.setSpacing(14)

        host_icon = QLabel("🖥️")
        host_icon.setStyleSheet("font-size: 36px;")
        host_layout.addWidget(host_icon)

        host_title = QLabel("HOST MODE")
        host_title.setStyleSheet("font-size: 18px; font-weight: 600; color: #60CDFF;")
        host_layout.addWidget(host_title)

        host_desc = QLabel(
            "Share files or entire folders from this computer.\n\n"
            "• Automatically sets IP to 192.168.50.1\n"
            "• Generates secure 6-digit pairing code\n"
            "• Direct TLS-encrypted streaming\n"
            "• Saturation for Gigabit Ethernet"
        )
        host_desc.setWordWrap(True)
        host_layout.addWidget(host_desc)
        host_layout.addStretch(1)

        self.host_btn = QPushButton("Select HOST Mode")
        self.host_btn.setObjectName("primary")
        self.host_btn.setMinimumHeight(40)
        self.host_btn.clicked.connect(self.request_host_mode.emit)
        host_layout.addWidget(self.host_btn)

        cards_layout.addWidget(self.host_card)

        # CLIENT Card
        self.client_card = QFrame()
        self.client_card.setObjectName("card")
        client_layout = QVBoxLayout(self.client_card)
        client_layout.setContentsMargins(20, 20, 20, 20)
        client_layout.setSpacing(14)

        client_icon = QLabel("📥")
        client_icon.setStyleSheet("font-size: 36px;")
        client_layout.addWidget(client_icon)

        client_title = QLabel("CLIENT MODE")
        client_title.setStyleSheet("font-size: 18px; font-weight: 600; color: #6CCB5F;")
        client_layout.addWidget(client_title)

        client_desc = QLabel(
            "Receive files on this computer from the Host.\n\n"
            "• Automatically sets IP to 192.168.50.2\n"
            "• Connects securely using the pairing code\n"
            "• Browse and select files to transfer\n"
            "• Resume partial downloads and verify SHA-256"
        )
        client_desc.setWordWrap(True)
        client_layout.addWidget(client_desc)
        client_layout.addStretch(1)

        self.client_btn = QPushButton("Select CLIENT Mode")
        self.client_btn.setObjectName("primary")
        self.client_btn.setMinimumHeight(40)
        self.client_btn.clicked.connect(self.request_client_mode.emit)
        client_layout.addWidget(self.client_btn)

        cards_layout.addWidget(self.client_card)
        main_layout.addLayout(cards_layout)

        # Bottom Utilities Bar
        bottom_bar = QHBoxLayout()
        self.restore_btn = QPushButton("🔄 Restore Original Network Settings")
        self.restore_btn.setObjectName("danger")
        self.restore_btn.clicked.connect(self.request_restore_network.emit)
        bottom_bar.addWidget(self.restore_btn)

        bottom_bar.addStretch(1)

        self.settings_btn = QPushButton("⚙️ Settings")
        self.settings_btn.clicked.connect(self.request_settings.emit)
        bottom_bar.addWidget(self.settings_btn)

        main_layout.addLayout(bottom_bar)
        self.refresh_admin_badge()

    def request_manual_refresh(self):
        window = self.window()
        refresher = getattr(window, "refresh_adapters", None)
        if refresher is not None:
            self.adapter_status_lbl.setText("Refreshing Ethernet adapters...")
            refresher()

    def refresh_admin_badge(self):
        admin = is_admin()
        if admin:
            self.admin_badge.setText("Administrator")
            self.admin_badge.setObjectName("pill_success")
        else:
            self.admin_badge.setText("Standard User (Elevation on Demand)")
            self.admin_badge.setObjectName("pill_warning")
        self.admin_badge.setStyle(self.admin_badge.style())

    def apply_adapters(self, adapters, scanning: bool = False):
        """Show the shared cache. This does not start a scan."""
        if adapters is None:
            if scanning:
                self.adapter_status_lbl.setText("Detecting Ethernet adapters...")
            return
        if not adapters:
            self.adapter_status_lbl.setText(
                "No physical Ethernet adapter detected. Please connect a USB LAN dongle or check hardware."
            )
            return
        connected = [adapter for adapter in adapters if adapter.is_connected]
        if connected:
            self.adapter_status_lbl.setText(f"Active Adapter: {connected[0].display_name()}")
        else:
            self.adapter_status_lbl.setText(
                f"Detected: {adapters[0].display_name()} (Plug Cat6 cable to both PCs)"
            )

    def show_adapter_error(self, message: str):
        self.adapter_status_lbl.setText(f"Adapter check error: {message}")
