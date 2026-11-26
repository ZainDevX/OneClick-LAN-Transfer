"""Checks for elevation safety, IP verification, and non-blocking startup."""

import os
import time
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path

from app.adapter_detection import conflict_in_snapshot, wait_for_ipv4
from app.host import format_host_error
from app.network_manager import NetworkApplyResult
from app.permissions import (
    HELPER_FLAG,
    LAUNCHED_ELEVATED_FLAG,
    PrivilegedCommand,
    admin_launch_action,
    command_is_allowed,
    run_command_capturing,
    run_privileged_commands,
)
from ui.adapter_directory import is_cache_fresh


class TestCommandSafety(unittest.TestCase):
    def test_allows_netsh_and_profile_only(self):
        self.assertTrue(command_is_allowed(
            'netsh interface ipv4 set address name="Ethernet" source=static address=192.168.50.1 mask=255.255.255.0 gateway=none'
        ))
        self.assertTrue(command_is_allowed(
            'netsh advfirewall firewall add rule name="OneClickLAN_Direct_Transfer" dir=in action=allow protocol=TCP localport=52428'
        ))
        self.assertTrue(command_is_allowed(
            'powershell -NoProfile -Command "Set-NetConnectionProfile -InterfaceAlias \'Ethernet\' -NetworkCategory Private"'
        ))
        self.assertFalse(command_is_allowed('netsh interface ipv4 set address name="Ethernet" & calc.exe'))
        self.assertFalse(command_is_allowed("cmd /c exit 7"))

    def test_captures_real_exit_code(self):
        ok = run_command_capturing("cmd /c exit 0", label="ok")
        failed = run_command_capturing("cmd /c exit 7", label="fail")
        self.assertTrue(ok.ok)
        self.assertEqual(ok.returncode, 0)
        self.assertFalse(failed.ok)
        self.assertEqual(failed.returncode, 7)


class TestIpVerification(unittest.TestCase):
    def test_conflict_ignores_self_and_down_adapters(self):
        snapshot = [
            ("Ethernet", False, ["192.168.50.1"]),
            ("Wi-Fi", True, ["10.0.0.5"]),
            ("vEthernet", True, ["192.168.50.20"]),
        ]
        self.assertEqual(conflict_in_snapshot("192.168.50.1", "Ethernet", snapshot), "vEthernet")
        self.assertIsNone(conflict_in_snapshot("192.168.50.1", "vEthernet", snapshot))

    def test_wait_returns_as_soon_as_address_appears(self):
        seen = {"calls": 0}

        def reader():
            seen["calls"] += 1
            if seen["calls"] < 3:
                return ["169.254.136.183"]
            return ["192.168.50.1"]

        started = time.perf_counter()
        verified, found = wait_for_ipv4(
            "Ethernet",
            "192.168.50.1",
            timeout=2.0,
            interval=0.01,
            read_addresses=reader,
        )
        elapsed = time.perf_counter() - started
        self.assertTrue(verified)
        self.assertEqual(found, ["192.168.50.1"])
        self.assertLess(elapsed, 1.0)
        self.assertEqual(seen["calls"], 3)

    def test_wait_reports_timeout_without_claiming_success(self):
        verified, found = wait_for_ipv4(
            "Ethernet",
            "192.168.50.1",
            timeout=0.05,
            interval=0.01,
            read_addresses=lambda: ["169.254.136.183"],
        )
        self.assertFalse(verified)
        self.assertEqual(found, ["169.254.136.183"])
        result = NetworkApplyResult(False, False, "not assigned")
        self.assertFalse(result.ok)

    def test_bind_error_explains_missing_address(self):
        try:
            raise OSError(10049, "assigned", None, 10049)
        except OSError as exc:
            exc.winerror = 10049
            text = format_host_error(exc, "192.168.50.1", 52428)
        self.assertIn("10049", text)
        self.assertIn("192.168.50.1", text)


class TestCache(unittest.TestCase):
    def test_ttl_expires(self):
        now = 100.0
        self.assertFalse(is_cache_fresh(0, now, ttl=8))
        self.assertTrue(is_cache_fresh(now - 3, now, ttl=8))
        self.assertFalse(is_cache_fresh(now - 9, now, ttl=8))


class TestAdminLaunch(unittest.TestCase):
    def test_packaged_exe_relaunches_until_it_is_admin(self):
        self.assertEqual(admin_launch_action(True, False, ["OneClickLAN.exe"]), "relaunch")
        self.assertEqual(admin_launch_action(True, True, ["OneClickLAN.exe"]), "continue")
        self.assertEqual(
            admin_launch_action(True, False, ["OneClickLAN.exe", LAUNCHED_ELEVATED_FLAG]),
            "abort",
        )

    def test_helper_and_development_runs_stay_put(self):
        self.assertEqual(
            admin_launch_action(True, False, ["OneClickLAN.exe", HELPER_FLAG, "job", "result"]),
            "continue",
        )
        self.assertEqual(admin_launch_action(False, False, ["main.py"]), "continue")

    def test_admin_process_does_not_open_another_prompt(self):
        with patch("app.permissions.is_admin", return_value=True), \
                patch("app.permissions.execute_commands", return_value=[]) as execute, \
                patch("app.permissions._launch_elevated_helper") as launch:
            run_privileged_commands([
                PrivilegedCommand(command="netsh interface ipv4 show interfaces", required=True, label="show"),
            ])
        launch.assert_not_called()
        execute.assert_called_once()

    def test_packaged_spec_requests_administrator(self):
        spec = Path(__file__).resolve().parents[1].joinpath("OneClickLAN.spec").read_text(encoding="utf-8")
        self.assertIn("uac_admin=True", spec)


class TestStartupDoesNotScan(unittest.TestCase):
    def test_window_constructs_without_adapter_scan(self):
        from PySide6.QtWidgets import QApplication
        from app.main_window import MainWindow

        app = QApplication.instance() or QApplication([])
        with patch("ui.adapter_directory.get_physical_ethernet_adapters", return_value=[]) as scan:
            started = time.perf_counter()
            window = MainWindow()
            window.show()
            app.processEvents()
            construct_seconds = time.perf_counter() - started
            self.assertEqual(scan.call_count, 0)
            self.assertLess(construct_seconds, 2.0)

            window.start_adapter_detection()
            thread = window.adapter_directory._thread
            self.assertIsNotNone(thread)
            self.assertTrue(thread.wait(5000))
            app.processEvents()
            self.assertEqual(scan.call_count, 1)

            window.switch_page(1)
            window.switch_page(2)
            window.switch_page(0)
            app.processEvents()
            self.assertEqual(scan.call_count, 1)
            window.close()

    def test_window_is_fixed_and_home_matches_the_shell(self):
        from PySide6.QtWidgets import QApplication
        from app.main_window import WINDOW_HEIGHT, WINDOW_WIDTH, MainWindow

        app = QApplication.instance() or QApplication([])
        window = MainWindow()
        window.show()
        app.processEvents()
        try:
            self.assertEqual(window.width(), WINDOW_WIDTH)
            self.assertEqual(window.height(), WINDOW_HEIGHT)
            self.assertEqual(window.minimumSize(), window.maximumSize())
            self.assertFalse(hasattr(window.title_bar, "max_btn"))
            self.assertEqual(window.title_bar.close_btn.objectName(), "winClose")
            self.assertEqual(window.title_bar.min_btn.objectName(), "winBtn")
            self.assertEqual(window.title_bar.close_btn.width(), 46)
            self.assertEqual(window.title_bar.close_btn.height(), 36)
            self.assertEqual(window.title_bar.min_btn.width(), 46)
            self.assertEqual(window.title_bar.min_btn.height(), 36)
            labels = [button.text() for button in window.sidebar._buttons.values()]
            self.assertEqual(labels, ["Home", "Settings", "About", "Help"])
            self.assertFalse(hasattr(window.dashboard_view, "settings_btn"))
            self.assertEqual(window.dashboard_view.host_btn.text(), "Sender")
            self.assertEqual(window.dashboard_view.client_btn.text(), "Receiver")
            self.assertEqual(window.dashboard_view.host_btn.height(), 40)
            self.assertFalse(window.dashboard_view.host_btn.icon().isNull())
            self.assertFalse(window.dashboard_view.client_btn.icon().isNull())
            window.sidebar.navigate.emit("settings")
            app.processEvents()
            self.assertEqual(window.stack.currentIndex(), 3)
            self.assertTrue(window.sidebar._buttons["settings"].isChecked())
            self.assertIn("#E81123", window.styleSheet())
        finally:
            window.close()


if __name__ == "__main__":
    unittest.main()
