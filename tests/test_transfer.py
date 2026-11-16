"""
Integration tests for End-to-End File Transfer Engine and Resume Capability.
"""

import os
import time
import shutil
import unittest
import tempfile
from pathlib import Path

from app.host import HostService
from app.client import ClientService
from app.integrity import compute_file_sha256
from app.file_manager import FileManager

class TestTransfer(unittest.TestCase):
    def setUp(self):
        self.temp_host_dir = Path(tempfile.mkdtemp(prefix="host_test_"))
        self.temp_client_dir = Path(tempfile.mkdtemp(prefix="client_test_"))

        # Create a test file of 15MB
        self.test_file_path = self.temp_host_dir / "sample_video.iso"
        self.file_size = 15 * 1024 * 1024
        with open(self.test_file_path, "wb") as f:
            f.write(os.urandom(self.file_size))

        self.source_hash = compute_file_sha256(str(self.test_file_path))

        # Setup Host on localhost with ephemeral port
        self.port = 52439
        self.host = HostService(bind_ip="127.0.0.1", port=self.port, cert_dir=self.temp_host_dir / "certs")
        self.host.set_shared_paths([str(self.test_file_path)])
        self.host.start()
        time.sleep(0.5)

    def tearDown(self):
        self.host.stop()
        shutil.rmtree(self.temp_host_dir, ignore_errors=True)
        shutil.rmtree(self.temp_client_dir, ignore_errors=True)

    def test_complete_file_transfer(self):
        """Test complete transfer of 15MB file over TLS and SHA-256 validation."""
        client = ClientService(
            host_ip="127.0.0.1",
            port=self.port,
            destination_dir=str(self.temp_client_dir)
        )

        ok, msg = client.connect_and_authenticate(self.host.display_code)
        self.assertTrue(ok, f"Connection failed: {msg}")

        ok, files = client.fetch_shared_files()
        self.assertTrue(ok)
        self.assertEqual(len(files), 1)

        transfer_done = False
        def on_complete():
            nonlocal transfer_done
            transfer_done = True

        client.on_transfer_complete = on_complete
        client.start_transfer_batch()

        # Wait for completion
        for _ in range(50):
            if transfer_done:
                break
            time.sleep(0.2)

        self.assertTrue(transfer_done, "Transfer did not complete in time.")

        dest_file = self.temp_client_dir / "sample_video.iso"
        self.assertTrue(dest_file.exists(), "Transferred file does not exist at destination.")
        self.assertEqual(dest_file.stat().st_size, self.file_size)

        dest_hash = compute_file_sha256(str(dest_file))
        self.assertEqual(dest_hash, self.source_hash, "SHA-256 hash does not match source file!")
        client.disconnect()

    def test_transfer_resume_from_part(self):
        """Test resuming when a partial file exists on client."""
        # Pre-create a .part file with first 5MB
        final_path, part_path = FileManager.get_destination_target(str(self.temp_client_dir), "sample_video.iso")
        part_size = 5 * 1024 * 1024
        with open(self.test_file_path, "rb") as src, open(part_path, "wb") as dst:
            dst.write(src.read(part_size))

        self.assertEqual(part_path.stat().st_size, part_size)

        client = ClientService(
            host_ip="127.0.0.1",
            port=self.port,
            destination_dir=str(self.temp_client_dir)
        )

        ok, _ = client.connect_and_authenticate(self.host.display_code)
        self.assertTrue(ok)
        client.fetch_shared_files()

        transfer_done = False
        def on_complete():
            nonlocal transfer_done
            transfer_done = True

        client.on_transfer_complete = on_complete
        client.start_transfer_batch()

        for _ in range(50):
            if transfer_done:
                break
            time.sleep(0.2)

        self.assertTrue(transfer_done)

        dest_file = self.temp_client_dir / "sample_video.iso"
        self.assertTrue(dest_file.exists())
        self.assertEqual(dest_file.stat().st_size, self.file_size)

        dest_hash = compute_file_sha256(str(dest_file))
        self.assertEqual(dest_hash, self.source_hash)
        client.disconnect()

if __name__ == "__main__":
    unittest.main()
