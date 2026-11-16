"""
Unit tests for chunked SHA-256 hashing and integrity verification.
"""

import os
import unittest
import tempfile
import hashlib
from pathlib import Path

from app.integrity import compute_file_sha256, verify_file_integrity

class TestIntegrity(unittest.TestCase):
    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(delete=False)
        # Create test data (10MB of pseudo-random bytes)
        self.data = os.urandom(10 * 1024 * 1024)
        self.temp_file.write(self.data)
        self.temp_file.close()
        self.expected_hash = hashlib.sha256(self.data).hexdigest()

    def tearDown(self):
        try:
            os.unlink(self.temp_file.name)
        except Exception:
            pass

    def test_compute_sha256(self):
        calc_hash = compute_file_sha256(self.temp_file.name)
        self.assertEqual(calc_hash, self.expected_hash)

    def test_verify_integrity_success(self):
        self.assertTrue(verify_file_integrity(self.temp_file.name, self.expected_hash))

    def test_verify_integrity_failure_corrupted(self):
        wrong_hash = "0000000000000000000000000000000000000000000000000000000000000000"
        self.assertFalse(verify_file_integrity(self.temp_file.name, wrong_hash))

    def test_offset_hashing(self):
        offset = 5 * 1024 * 1024
        expected_slice_hash = hashlib.sha256(self.data[offset:]).hexdigest()
        calc_slice_hash = compute_file_sha256(self.temp_file.name, offset=offset)
        self.assertEqual(calc_slice_hash, expected_slice_hash)

if __name__ == "__main__":
    unittest.main()
