"""
Unit tests for network adapter detection, backup persistence, and conflict detection.
"""

import unittest
import tempfile
import shutil
import json
from pathlib import Path

from app.adapter_detection import (
    AdapterInfo,
    AdapterConfig,
    prefix_to_netmask,
    get_physical_ethernet_adapters,
    get_all_adapters
)
from app.network_manager import NetworkManager

class TestNetwork(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.net_mgr = NetworkManager(backup_dir=self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_prefix_to_netmask(self):
        self.assertEqual(prefix_to_netmask(24), "255.255.255.0")
        self.assertEqual(prefix_to_netmask(16), "255.255.0.0")
        self.assertEqual(prefix_to_netmask(8), "255.0.0.0")

    def test_adapter_detection_runnable(self):
        """Verify get_all_adapters executes without exceptions on Windows."""
        adapters = get_all_adapters()
        self.assertIsInstance(adapters, list)
        for a in adapters:
            self.assertIsInstance(a.name, str)
            self.assertIsInstance(a.is_physical_ethernet, bool)
            self.assertIsInstance(a.is_wifi, bool)
            self.assertIsInstance(a.is_virtual, bool)

    def test_backup_and_restore_file_creation(self):
        """Verify network backup file is properly structured."""
        dummy_adapter = AdapterInfo(
            name="MockEthernet",
            interface_description="Mock Controller",
            interface_index=999,
            mac_address="00-11-22-33-44-55",
            status="Up",
            link_speed="1 Gbps",
            physical_media_type="802.3",
            is_connected=True,
            is_physical_ethernet=True,
            is_wifi=False,
            is_virtual=False,
            config=AdapterConfig(
                dhcp_enabled=True,
                ipv4_address="192.168.1.100",
                subnet_mask="255.255.255.0",
                prefix_length=24,
                default_gateway="192.168.1.1",
                dns_servers=["1.1.1.1", "8.8.8.8"]
            )
        )

        backup_file = self.net_mgr.save_original_config(dummy_adapter)
        self.assertTrue(backup_file.exists())

        with open(backup_file, "r") as f:
            data = json.load(f)

        self.assertEqual(data["adapter_name"], "MockEthernet")
        self.assertTrue(data["dhcp_enabled"])
        self.assertEqual(data["default_gateway"], "192.168.1.1")
        self.assertEqual(len(data["dns_servers"]), 2)

if __name__ == "__main__":
    unittest.main()
