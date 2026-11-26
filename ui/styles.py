"""Starbucks-inspired theme for OneClick LAN Transfer.

The light theme matches the home-screen design: warm cream canvas, house-green
chrome, and green accent actions. The dark theme keeps the same chrome and
shifts the content surfaces darker.
"""

_CHROME = """
QMainWindow {
    background-color: #1E3932;
}

QFrame#sidebar, QFrame#titlebar {
    background-color: #1E3932;
    border: none;
}

QFrame#sidebar QLabel, QFrame#titlebar QLabel {
    color: #FFFFFF;
    background: transparent;
}

QFrame#titlebar QLabel#appTitle {
    font-size: 14px;
    font-weight: 600;
    color: #FFFFFF;
}

QFrame#sidebar QLabel#wordmark {
    font-size: 16px;
    font-weight: 700;
    color: #FFFFFF;
}

QFrame#sidebar QLabel#readyLabel {
    font-size: 13px;
    font-weight: 600;
    color: #FFFFFF;
}

QFrame#sidebar QLabel#versionLabel {
    font-size: 12px;
    font-weight: 500;
    color: rgba(255, 255, 255, 0.62);
}

QPushButton#nav {
    background: transparent;
    color: #FFFFFF;
    border: none;
    border-radius: 12px;
    text-align: left;
    padding: 0 12px 0 14px;
    font-size: 15px;
    font-weight: 600;
    min-height: 48px;
}

QPushButton#nav:hover {
    background: rgba(255, 255, 255, 0.07);
}

QPushButton#nav:checked, QPushButton#nav:checked:hover {
    background: #2C6A56;
    color: #FFFFFF;
}

QFrame#sideRule {
    background-color: rgba(255, 255, 255, 0.16);
    border: none;
    max-height: 1px;
    min-height: 1px;
}

QPushButton#winBtn, QPushButton#winClose {
    background: transparent;
    border: none;
    border-radius: 6px;
    padding: 0px;
    min-width: 46px;
    max-width: 46px;
    min-height: 36px;
    max-height: 36px;
}

QPushButton#winBtn:hover {
    background: rgba(255, 255, 255, 0.12);
}

QPushButton#winBtn:pressed {
    background: rgba(255, 255, 255, 0.20);
}

QPushButton#winClose:hover {
    background: #E81123;
}

QPushButton#winClose:pressed {
    background: #C42B1C;
}
"""


def _theme(canvas, card, text, text_soft, heading, line, input_bg, header_bg) -> str:
    return _CHROME + f"""
QWidget#canvas, QStackedWidget#canvas {{
    background-color: {canvas};
}}

QWidget {{
    color: {text};
    font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
}}

QLabel {{
    color: {text};
    background: transparent;
}}

QLabel#heroTitle {{
    font-size: 40px;
    font-weight: 700;
    color: {heading};
}}

QLabel#heroSubtitle {{
    font-size: 15px;
    color: {text_soft};
}}

QLabel#title {{
    font-size: 28px;
    font-weight: 700;
    color: {heading};
}}

QLabel#cardTitle {{
    font-size: 26px;
    font-weight: 700;
    color: {heading};
}}

QLabel#cardSubtitle, QLabel#statusDetail, QLabel#muted {{
    font-size: 13px;
    color: {text_soft};
}}

QLabel#statusTitle, QLabel#userStatus {{
    font-size: 14px;
    font-weight: 600;
    color: {text};
}}

QLabel#userStatus {{
    font-weight: 500;
}}

QLabel#feature {{
    font-size: 14px;
    color: {text};
}}

QLabel#infoText {{
    font-size: 14px;
    font-weight: 500;
    color: #1A3C30;
}}

QLabel#section {{
    font-size: 15px;
    font-weight: 700;
    color: #006241;
}}

QLabel#speed, QLabel#statusGood {{
    color: #006241;
    font-weight: 700;
    font-size: 15px;
}}

QLabel#pairing_code {{
    font-family: Consolas, "Cascadia Mono", monospace;
    font-size: 32px;
    font-weight: 700;
    color: #006241;
    padding: 10px 16px;
    background-color: {input_bg};
    border: 1px solid {line};
    border-radius: 12px;
}}

QFrame#card, QFrame#statusCard {{
    background-color: {card};
    border: 1px solid {line};
    border-radius: 16px;
}}

QFrame#infoBanner {{
    background-color: #E5F2EA;
    border: none;
    border-radius: 12px;
}}

QFrame#rule {{
    background-color: {line};
    border: none;
    max-height: 1px;
}}

QPushButton {{
    background-color: {card};
    color: {text};
    border: 1px solid {line};
    border-radius: 18px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 600;
}}

QPushButton:hover {{
    background-color: {header_bg};
}}

QPushButton:pressed {{
    background-color: {line};
}}

QPushButton:disabled {{
    background-color: {header_bg};
    color: {text_soft};
    border-color: {line};
}}

QPushButton#primary {{
    background-color: #006241;
    color: #FFFFFF;
    border: 1px solid #006241;
    border-radius: 26px;
    font-size: 16px;
    font-weight: 700;
    padding: 12px 22px;
}}

QPushButton#primary:hover {{
    background-color: #00754A;
    border-color: #00754A;
}}

QPushButton#primary:pressed {{
    background-color: #004E34;
}}

QPushButton#primary:disabled {{
    background-color: #9BB8AD;
    color: #FFFFFF;
    border-color: #9BB8AD;
}}

QPushButton#homeCta {{
    background-color: #006241;
    color: #FFFFFF;
    border: none;
    border-radius: 20px;
    font-size: 15px;
    font-weight: 700;
    padding: 0 16px;
    min-height: 40px;
    max-height: 40px;
}}

QPushButton#homeCta:hover {{
    background-color: #00754A;
}}

QPushButton#homeCta:pressed {{
    background-color: #004E34;
}}

QPushButton#outline {{
    background-color: transparent;
    color: #006241;
    border: 1.5px solid #006241;
    border-radius: 18px;
    font-weight: 600;
    padding: 6px 16px;
}}

QPushButton#outline:hover {{
    background-color: #E5F3EC;
}}

QPushButton#danger {{
    background-color: #C82014;
    color: #FFFFFF;
    border: 1px solid #C82014;
    border-radius: 18px;
    font-weight: 700;
}}

QPushButton#danger:hover {{
    background-color: #A81B12;
    border-color: #A81B12;
}}

QLineEdit, QSpinBox, QComboBox {{
    background-color: {input_bg};
    color: {text};
    border: 1px solid {line};
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
    min-height: 18px;
}}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QLineEdit#pairingInput:focus {{
    border: 1.5px solid #00754A;
}}

QLineEdit#pairingInput {{
    font-family: Consolas, "Cascadia Mono", monospace;
    font-size: 18px;
    font-weight: 700;
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}

QComboBox QAbstractItemView {{
    background-color: {card};
    color: {text};
    selection-background-color: #D4E9E2;
    selection-color: #12382C;
    border: 1px solid {line};
    border-radius: 8px;
    padding: 4px;
}}

QCheckBox {{
    spacing: 8px;
    color: {text};
    font-size: 13px;
}}

QProgressBar {{
    background-color: {header_bg};
    border: none;
    border-radius: 8px;
    text-align: center;
    color: {text};
    font-weight: 600;
    min-height: 18px;
}}

QProgressBar::chunk {{
    background-color: #006241;
    border-radius: 8px;
}}

QTableWidget, QListWidget {{
    background-color: {card};
    alternate-background-color: {header_bg};
    border: 1px solid {line};
    border-radius: 10px;
    gridline-color: {line};
    color: {text};
}}

QTableWidget::item, QListWidget::item {{
    padding: 6px 8px;
}}

QTableWidget::item:selected, QListWidget::item:selected {{
    background-color: #D4E9E2;
    color: #12382C;
}}

QHeaderView::section {{
    background-color: {header_bg};
    color: {text_soft};
    padding: 8px 10px;
    border: none;
    border-bottom: 1px solid {line};
    font-weight: 700;
}}

QLabel#pill_success {{
    background-color: #D4E9E2;
    color: #006241;
    border: 1px solid #B7D8CC;
    border-radius: 11px;
    padding: 4px 10px;
    font-size: 12px;
    font-weight: 700;
}}

QLabel#pill_warning {{
    background-color: #F8EFD6;
    color: #7A5B12;
    border: 1px solid #E6D3A1;
    border-radius: 11px;
    padding: 4px 10px;
    font-size: 12px;
    font-weight: 700;
}}

QLabel#pill_danger {{
    background-color: #F8D7D4;
    color: #A32016;
    border: 1px solid #E7B4B0;
    border-radius: 11px;
    padding: 4px 10px;
    font-size: 12px;
    font-weight: 700;
}}

QMessageBox {{
    background-color: {card};
}}

QMessageBox QLabel {{
    color: {text};
    background: transparent;
}}

QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 4px;
}}

QScrollBar::handle:vertical {{
    background: #C9C2B8;
    min-height: 24px;
    border-radius: 5px;
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
""" + _HOST


# Host Mode is painted with the Starbucks light tokens even when the rest of
# the app is in the dark theme, so this screen stays on the warm cream canvas.
_HOST = """
QWidget#hostCanvas, QScrollArea#hostScroll {
    background-color: #F2F0EB;
    color: rgba(0, 0, 0, 0.87);
    border: none;
}

QWidget#hostCanvas QLabel {
    color: rgba(0, 0, 0, 0.87);
    background: transparent;
    font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
}

QWidget#hostCanvas QLabel#hostTitle {
    color: #006241;
    font-size: 22px;
    font-weight: 700;
}

QWidget#hostCanvas QLabel#hostSubtitle,
QWidget#hostCanvas QLabel#muted,
QWidget#hostCanvas QLabel#emptyHint {
    color: rgba(0, 0, 0, 0.58);
    font-size: 13px;
    font-weight: 400;
}

QWidget#hostCanvas QLabel#hostSection {
    color: #006241;
    font-size: 16px;
    font-weight: 700;
}

QWidget#hostCanvas QLabel#fieldLabel,
QWidget#hostCanvas QLabel#clientTitle,
QWidget#hostCanvas QLabel#ipValue,
QWidget#hostCanvas QLabel#hostEta {
    color: rgba(0, 0, 0, 0.87);
    font-size: 14px;
    font-weight: 600;
}

QWidget#hostCanvas QLabel#statusOk,
QWidget#hostCanvas QLabel#speed,
QWidget#hostCanvas QLabel#statusGood {
    color: #006241;
    font-size: 14px;
    font-weight: 700;
}

QWidget#hostCanvas QLabel#statusWait {
    color: rgba(0, 0, 0, 0.87);
    font-size: 14px;
    font-weight: 700;
}

QWidget#hostCanvas QLabel#statusBad {
    color: #C82014;
    font-size: 14px;
    font-weight: 700;
}

QWidget#hostCanvas QLabel#pairing_code {
    color: #006241;
    background: transparent;
    border: none;
    border-radius: 0px;
    padding: 0px;
    font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    font-size: 22px;
    font-weight: 700;
}

QWidget#hostCanvas QLabel#emptyTitle {
    color: rgba(0, 0, 0, 0.58);
    font-size: 14px;
    font-weight: 600;
}

QFrame#hostCard {
    background-color: #FFFFFF;
    border: 1px solid rgba(0, 0, 0, 0.08);
    border-radius: 12px;
}

QFrame#codeBox {
    background-color: #FFFFFF;
    border: 1px solid #E0DCD4;
    border-radius: 12px;
}

QFrame#linkOk {
    background-color: #E7F3EC;
    border: none;
    border-radius: 10px;
}

QFrame#linkWait {
    background-color: #F4F1EB;
    border: none;
    border-radius: 10px;
}

QFrame#linkBad {
    background-color: #F8E8E6;
    border: none;
    border-radius: 10px;
}

QFrame#vrule {
    background-color: #E4E0DA;
    border: none;
    max-width: 1px;
}

QWidget#emptyState {
    background: transparent;
}

QWidget#hostCanvas QPushButton {
    background-color: #FFFFFF;
    color: rgba(0, 0, 0, 0.87);
    border: 1px solid #D5D1CA;
    border-radius: 20px;
    padding: 6px 14px;
    font-size: 13px;
    font-weight: 600;
    min-height: 36px;
}

QWidget#hostCanvas QPushButton:hover {
    background-color: #F7F4EF;
}

QWidget#hostCanvas QPushButton:pressed {
    background-color: #EFEBE4;
    margin: 1px 2px;
}

QWidget#hostCanvas QPushButton:disabled {
    background-color: #F6F3EE;
    color: rgba(0, 0, 0, 0.38);
    border-color: #E4E0DA;
}

QWidget#hostCanvas QPushButton#primary {
    background-color: #00754A;
    color: #FFFFFF;
    border: 1px solid #00754A;
    border-radius: 22px;
    font-size: 14px;
    font-weight: 600;
    padding: 8px 18px;
    min-height: 40px;
}

QWidget#hostCanvas QPushButton#primary:hover {
    background-color: #006241;
    border-color: #006241;
}

QWidget#hostCanvas QPushButton#primary:pressed {
    background-color: #00543A;
    border-color: #00543A;
}

QWidget#hostCanvas QPushButton#primary:disabled {
    background-color: #9BB8AD;
    color: #FFFFFF;
    border-color: #9BB8AD;
}

QWidget#hostCanvas QPushButton#danger {
    background-color: #C82014;
    color: #FFFFFF;
    border: 1px solid #C82014;
    border-radius: 22px;
    font-size: 14px;
    font-weight: 600;
    padding: 8px 18px;
    min-height: 40px;
}

QWidget#hostCanvas QPushButton#danger:hover {
    background-color: #A81B12;
    border-color: #A81B12;
}

QWidget#hostCanvas QPushButton#danger:pressed {
    background-color: #8E170F;
    border-color: #8E170F;
}

QWidget#hostCanvas QComboBox {
    background-color: #FFFFFF;
    color: rgba(0, 0, 0, 0.87);
    border: 1px solid #E0DCD4;
    border-radius: 20px;
    padding: 6px 12px;
    font-size: 13px;
    min-height: 34px;
}

QWidget#hostCanvas QComboBox:hover, QWidget#hostCanvas QComboBox:focus {
    border: 1px solid #00754A;
}

QWidget#hostCanvas QComboBox::drop-down {
    border: none;
    width: 28px;
}

QWidget#hostCanvas QComboBox QAbstractItemView {
    background-color: #FFFFFF;
    color: rgba(0, 0, 0, 0.87);
    selection-background-color: #D4E9E2;
    selection-color: #12382C;
    border: 1px solid #E0DCD4;
    border-radius: 8px;
    outline: none;
    padding: 4px;
}

QWidget#hostCanvas QProgressBar {
    background-color: #E4E0D8;
    border: none;
    border-radius: 10px;
    text-align: center;
    color: rgba(0, 0, 0, 0.87);
    font-weight: 700;
    font-size: 12px;
    min-height: 20px;
    max-height: 20px;
}

QWidget#hostCanvas QProgressBar::chunk {
    background-color: #00754A;
    border-radius: 10px;
}

QWidget#hostCanvas QTableWidget {
    background-color: #FFFFFF;
    alternate-background-color: #FBF9F6;
    border: 1px solid #E7E3DC;
    border-radius: 10px;
    gridline-color: transparent;
    color: rgba(0, 0, 0, 0.87);
    font-size: 13px;
}

QWidget#hostCanvas QTableWidget::item {
    padding: 6px 10px;
    border: none;
}

QWidget#hostCanvas QTableWidget::item:selected {
    background-color: #D4E9E2;
    color: #12382C;
}

QWidget#hostCanvas QHeaderView::section {
    background-color: #F4F1EB;
    color: rgba(0, 0, 0, 0.58);
    padding: 8px 12px;
    border: none;
    border-bottom: 1px solid #E7E3DC;
    font-size: 13px;
    font-weight: 600;
}

QScrollArea#hostScroll QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 4px;
}

QScrollArea#hostScroll QScrollBar::handle:vertical {
    background: #C9C2B8;
    min-height: 24px;
    border-radius: 5px;
}

QScrollArea#hostScroll QScrollBar::add-line:vertical,
QScrollArea#hostScroll QScrollBar::sub-line:vertical {
    height: 0px;
}
"""

LIGHT_THEME = _theme(
    canvas="#F2EDE6",
    card="#FFFFFF",
    text="rgba(0, 0, 0, 0.87)",
    text_soft="rgba(0, 0, 0, 0.58)",
    heading="#12382C",
    line="#E6E1DA",
    input_bg="#FFFFFF",
    header_bg="#F7F4EF",
)

DARK_THEME = _theme(
    canvas="#10241F",
    card="#17332C",
    text="rgba(255, 255, 255, 0.92)",
    text_soft="rgba(255, 255, 255, 0.65)",
    heading="#E7F4EE",
    line="#2C4A42",
    input_bg="#10241F",
    header_bg="#1E3B33",
)
