"""Checks for elevation safety, IP verification, and non-blocking startup."""

import os
import time
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from app.adapter_detection import conflict_in_snapshot, wait_for_ipv4
from app.host import format_host_error
from app.network_manager import NetworkApplyResult
from app.permissions import command_is_allowed, run_command_capturing
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


if __name__ == "__main__":
    unittest.main()
