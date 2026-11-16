"""
Unit tests for pairing code generation, HMAC mutual authentication,
and ephemeral TLS certificate generation.
"""

import unittest
import socket
import threading
from pathlib import Path
import tempfile
import shutil

from app.authentication import (
    generate_pairing_code,
    normalize_pairing_code,
    compute_hmac,
    generate_ephemeral_tls_cert,
    create_server_ssl_context,
    create_client_ssl_context,
    server_authenticate_client,
    client_authenticate_host
)

class TestAuthentication(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_pairing_code_format(self):
        display, raw = generate_pairing_code()
        self.assertEqual(len(raw), 6)
        self.assertTrue(raw.isdigit())
        self.assertEqual(len(display), 7)
        self.assertEqual(display[3], "-")
        self.assertEqual(normalize_pairing_code(display), raw)

    def test_ephemeral_cert_generation(self):
        cert_p = self.temp_dir / "test_cert.pem"
        key_p = self.temp_dir / "test_key.pem"
        generate_ephemeral_tls_cert(cert_p, key_p)

        self.assertTrue(cert_p.exists())
        self.assertTrue(key_p.exists())
        self.assertGreater(cert_p.stat().st_size, 100)
        self.assertGreater(key_p.stat().st_size, 100)

    def test_mutual_auth_success(self):
        """Test complete TLS handshake + mutual HMAC authentication."""
        cert_p = self.temp_dir / "host.pem"
        key_p = self.temp_dir / "host.key"
        generate_ephemeral_tls_cert(cert_p, key_p)

        server_ctx = create_server_ssl_context(cert_p, key_p)
        client_ctx = create_client_ssl_context()

        display_code, raw_code = generate_pairing_code()

        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]

        server_result = {}
        client_result = {}

        def server_worker():
            raw_conn, _ = listener.accept()
            tls_conn = server_ctx.wrap_socket(raw_conn, server_side=True)
            success, token = server_authenticate_client(tls_conn, raw_code)
            server_result["success"] = success
            server_result["token"] = token
            tls_conn.close()
            listener.close()

        def client_worker():
            raw_conn = socket.create_connection(("127.0.0.1", port), timeout=3.0)
            tls_conn = client_ctx.wrap_socket(raw_conn)
            success, token = client_authenticate_host(tls_conn, display_code)
            client_result["success"] = success
            client_result["token"] = token
            tls_conn.close()

        t_srv = threading.Thread(target=server_worker)
        t_cli = threading.Thread(target=client_worker)

        t_srv.start()
        t_cli.start()
        t_srv.join(timeout=5.0)
        t_cli.join(timeout=5.0)

        self.assertTrue(server_result.get("success"), f"Server auth failed: {server_result}")
        self.assertTrue(client_result.get("success"), f"Client auth failed: {client_result}")
        # Both must have identical negotiated session token
        self.assertEqual(server_result.get("token"), client_result.get("token"))

    def test_mutual_auth_failure_wrong_code(self):
        """Test rejection when client enters incorrect pairing code."""
        cert_p = self.temp_dir / "host.pem"
        key_p = self.temp_dir / "host.key"
        generate_ephemeral_tls_cert(cert_p, key_p)

        server_ctx = create_server_ssl_context(cert_p, key_p)
        client_ctx = create_client_ssl_context()

        _, correct_code = generate_pairing_code()
        wrong_code = "999-999"

        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]

        server_result = {}
        client_result = {}

        def server_worker():
            raw_conn, _ = listener.accept()
            try:
                tls_conn = server_ctx.wrap_socket(raw_conn, server_side=True)
                success, token = server_authenticate_client(tls_conn, correct_code)
                server_result["success"] = success
                tls_conn.close()
            except Exception:
                server_result["success"] = False
            listener.close()

        def client_worker():
            raw_conn = socket.create_connection(("127.0.0.1", port), timeout=3.0)
            try:
                tls_conn = client_ctx.wrap_socket(raw_conn)
                success, token = client_authenticate_host(tls_conn, wrong_code)
                client_result["success"] = success
                tls_conn.close()
            except Exception:
                client_result["success"] = False

        t_srv = threading.Thread(target=server_worker)
        t_cli = threading.Thread(target=client_worker)

        t_srv.start()
        t_cli.start()
        t_srv.join(timeout=5.0)
        t_cli.join(timeout=5.0)

        self.assertFalse(server_result.get("success", False))
        self.assertFalse(client_result.get("success", False))

if __name__ == "__main__":
    unittest.main()
