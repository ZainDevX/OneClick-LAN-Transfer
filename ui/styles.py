"""
Windows 11 Fluent Design Modern Stylesheets for PySide6.
Provides consistent Dark and Light themes with rounded cards, modern typography,
and high-contrast status accents.
"""

DARK_THEME = """
QMainWindow, QDialog {
    background-color: #202020;
    color: #FFFFFF;
    font-family: 'Segoe UI Variable Display', 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}

QWidget {
    color: #FFFFFF;
    font-family: 'Segoe UI Variable Display', 'Segoe UI', Arial, sans-serif;
}

/* Card panels */
QFrame#card {
    background-color: #2B2B2B;
    border: 1px solid #383838;
    border-radius: 10px;
    padding: 16px;
}

QFrame#banner {
    background-color: #1F3A52;
    border: 1px solid #2B577E;
    border-radius: 8px;
    padding: 12px;
}

QLabel {
    color: #E0E0E0;
    font-size: 13px;
}

QLabel#title {
    font-size: 22px;
    font-weight: 600;
    color: #FFFFFF;
}

QLabel#subtitle {
    font-size: 13px;
    color: #A0A0A0;
}

QLabel#pairing_code {
    font-family: 'Consolas', 'Cascadia Code', monospace;
    font-size: 32px;
    font-weight: 700;
    color: #60CDFF;
    letter-spacing: 4px;
    padding: 12px;
    background-color: #1A1A1A;
    border: 1px solid #333333;
    border-radius: 8px;
}

/* PushButtons */
QPushButton {
    background-color: #383838;
    color: #FFFFFF;
    border: 1px solid #484848;
    border-radius: 6px;
    padding: 8px 18px;
    font-size: 13px;
    font-weight: 500;
    min-height: 20px;
}

QPushButton:hover {
    background-color: #444444;
    border-color: #555555;
}

QPushButton:pressed {
    background-color: #2D2D2D;
}

QPushButton:disabled {
    background-color: #262626;
    color: #666666;
    border-color: #333333;
}

/* Primary Accent Button */
QPushButton#primary {
    background-color: #0078D4;
    color: #FFFFFF;
    border: 1px solid #0086F0;
    font-weight: 600;
}

QPushButton#primary:hover {
    background-color: #1084D8;
    border-color: #2B95E0;
}

QPushButton#primary:pressed {
    background-color: #006CBE;
}

QPushButton#danger {
    background-color: #C42B1C;
    color: #FFFFFF;
    border: 1px solid #D83B2C;
}

QPushButton#danger:hover {
    background-color: #D83B2C;
}

QPushButton#success {
    background-color: #0E7A0D;
    color: #FFFFFF;
    border: 1px solid #108910;
}

/* Input Fields */
QLineEdit, QSpinBox, QComboBox {
    background-color: #2D2D2D;
    color: #FFFFFF;
    border: 1px solid #454545;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 13px;
}

QLineEdit:focus, QComboBox:focus {
    border: 2px solid #60CDFF;
    background-color: #323232;
}

QComboBox::drop-down {
    border: none;
    padding-right: 10px;
}

QComboBox QAbstractItemView {
    background-color: #2B2B2B;
    color: #FFFFFF;
    selection-background-color: #0078D4;
    selection-color: #FFFFFF;
    border: 1px solid #454545;
    border-radius: 6px;
    padding: 4px;
}

/* Progress Bar */
QProgressBar {
    background-color: #2E2E2E;
    border: 1px solid #3E3E3E;
    border-radius: 6px;
    text-align: center;
    color: #FFFFFF;
    font-weight: 600;
    height: 22px;
}

QProgressBar::chunk {
    background-color: #0078D4;
    border-radius: 5px;
}

/* Tables & Lists */
QTableWidget, QListWidget {
    background-color: #262626;
    border: 1px solid #383838;
    border-radius: 8px;
    gridline-color: #333333;
    color: #FFFFFF;
}

QTableWidget::item, QListWidget::item {
    padding: 6px 10px;
    border-bottom: 1px solid #2E2E2E;
}

QTableWidget::item:selected, QListWidget::item:selected {
    background-color: #0078D4;
    color: #FFFFFF;
}

QHeaderView::section {
    background-color: #2D2D2D;
    color: #BBBBBB;
    padding: 6px 10px;
    border: none;
    border-bottom: 1px solid #3E3E3E;
    font-weight: 600;
}

/* Status Pill */
QLabel#pill_success {
    background-color: #12381B;
    color: #6CCB5F;
    border: 1px solid #1D5C2B;
    border-radius: 12px;
    padding: 4px 12px;
    font-size: 11px;
    font-weight: 600;
}

QLabel#pill_warning {
    background-color: #382D12;
    color: #FCE100;
    border: 1px solid #5C4A1D;
    border-radius: 12px;
    padding: 4px 12px;
    font-size: 11px;
    font-weight: 600;
}

QLabel#pill_danger {
    background-color: #381212;
    color: #FF99A4;
    border: 1px solid #5C1D1D;
    border-radius: 12px;
    padding: 4px 12px;
    font-size: 11px;
    font-weight: 600;
}

QScrollBar:vertical {
    border: none;
    background: #202020;
    width: 10px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #444444;
    min-height: 20px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background: #60CDFF;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""

LIGHT_THEME = """
QMainWindow, QDialog {
    background-color: #F3F3F3;
    color: #1E1E1E;
    font-family: 'Segoe UI Variable Display', 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}

QWidget {
    color: #1E1E1E;
    font-family: 'Segoe UI Variable Display', 'Segoe UI', Arial, sans-serif;
}

QFrame#card {
    background-color: #FFFFFF;
    border: 1px solid #E5E5E5;
    border-radius: 10px;
    padding: 16px;
}

QFrame#banner {
    background-color: #E8F3FD;
    border: 1px solid #B7DAF8;
    border-radius: 8px;
    padding: 12px;
}

QLabel {
    color: #2D2D2D;
    font-size: 13px;
}

QLabel#title {
    font-size: 22px;
    font-weight: 600;
    color: #111111;
}

QLabel#subtitle {
    font-size: 13px;
    color: #606060;
}

QLabel#pairing_code {
    font-family: 'Consolas', 'Cascadia Code', monospace;
    font-size: 32px;
    font-weight: 700;
    color: #0067C0;
    letter-spacing: 4px;
    padding: 12px;
    background-color: #F8F9FA;
    border: 1px solid #D0D0D0;
    border-radius: 8px;
}

QPushButton {
    background-color: #FAFAFA;
    color: #1E1E1E;
    border: 1px solid #D1D1D1;
    border-radius: 6px;
    padding: 8px 18px;
    font-size: 13px;
    font-weight: 500;
    min-height: 20px;
}

QPushButton:hover {
    background-color: #F0F0F0;
    border-color: #C0C0C0;
}

QPushButton:pressed {
    background-color: #E5E5E5;
}

QPushButton#primary {
    background-color: #0067C0;
    color: #FFFFFF;
    border: 1px solid #005A9E;
    font-weight: 600;
}

QPushButton#primary:hover {
    background-color: #1070C5;
}

QPushButton#danger {
    background-color: #C42B1C;
    color: #FFFFFF;
    border: 1px solid #B02012;
}

QLineEdit, QComboBox {
    background-color: #FFFFFF;
    color: #1E1E1E;
    border: 1px solid #D1D1D1;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 13px;
}

QLineEdit:focus, QComboBox:focus {
    border: 2px solid #0067C0;
}

QProgressBar {
    background-color: #E5E5E5;
    border: 1px solid #D0D0D0;
    border-radius: 6px;
    text-align: center;
    color: #1E1E1E;
    font-weight: 600;
    height: 22px;
}

QProgressBar::chunk {
    background-color: #0067C0;
    border-radius: 5px;
}

QTableWidget, QListWidget {
    background-color: #FFFFFF;
    border: 1px solid #E0E0E0;
    border-radius: 8px;
    gridline-color: #ECECEC;
    color: #1E1E1E;
}

QTableWidget::item:selected, QListWidget::item:selected {
    background-color: #0067C0;
    color: #FFFFFF;
}

QHeaderView::section {
    background-color: #F8F8F8;
    color: #555555;
    padding: 6px 10px;
    border: none;
    border-bottom: 1px solid #E0E0E0;
    font-weight: 600;
}
"""
