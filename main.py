"""
OneClick LAN Transfer — Main Application Entry Point
Direct Gigabit Ethernet File Transfer for Windows 10 & 11.
"""

import sys
import os
import logging
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from app.main_window import MainWindow

def setup_logging():
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "oneclicklan.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s",
        handlers=[
            logging.FileHandler(str(log_file), encoding="utf-8"),
            logging.StreamHandler(sys.stdout)
        ]
    )
    logging.info("==========================================")
    logging.info("Starting OneClick LAN Transfer Application")
    logging.info("==========================================")

def main():
    setup_logging()

    # Set DPI awareness for crisp Windows 11 rendering
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

    app = QApplication(sys.argv)
    app.setApplicationName("OneClick LAN Transfer")
    app.setApplicationDisplayName("OneClick LAN Transfer")
    app.setOrganizationName("OneClickLAN")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
