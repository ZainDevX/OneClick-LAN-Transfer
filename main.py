"""
OneClick LAN Transfer — Main Application Entry Point
Direct Gigabit Ethernet File Transfer for Windows 10 & 11.

The elevated helper must run before Qt is imported. An elevated process
that reaches QApplication would open a second window.
"""

import sys
import os


def main():
    if "--elevated-helper" in sys.argv:
        from app.permissions import elevated_helper_main
        sys.exit(elevated_helper_main(sys.argv))

    import logging
    from pathlib import Path

    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication

    from app.main_window import MainWindow

    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s",
        handlers=[
            logging.FileHandler(str(log_dir / "oneclicklan.log"), encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    logging.info("==========================================")
    logging.info("Starting OneClick LAN Transfer Application")
    logging.info("==========================================")

    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    app = QApplication(sys.argv)
    app.setApplicationName("OneClick LAN Transfer")
    app.setApplicationDisplayName("OneClick LAN Transfer")
    app.setOrganizationName("OneClickLAN")

    window = MainWindow()
    window.show()
    # Let the first paint happen, then scan adapters off the GUI thread.
    QTimer.singleShot(0, window.start_adapter_detection)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
