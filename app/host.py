"""
Host Service for OneClick LAN Transfer.
Runs an encrypted TLS server, serves shared files, authenticates clients,
and streams file data over direct Gigabit Ethernet.
"""

import os
import json
import socket
import select
import logging
import threading
from pathlib import Path
from typing import List, Dict, Optional, Callable, Any

from .file_manager import FileManager, FileItem
from .authentication import (
    generate_pairing_code,
    generate_ephemeral_tls_cert,
    create_server_ssl_context,
    server_authenticate_client
)
from .integrity import compute_file_sha256
from .transfer_engine import send_file_stream, TransferStatsTracker, TransferProgress
from .error_handler import AppError, get_error

logger = logging.getLogger("OneClickLAN.Host")


def format_host_error(exc: Exception, bind_ip: str, port: int) -> str:
    """User-facing text for a host socket failure."""
    winerror = getattr(exc, "winerror", None)
    if isinstance(exc, OSError) and winerror == 10049:
        return (
            f"The host could not listen on {bind_ip}:{port}. "
            "That address is not assigned to this computer, so Windows refused the socket "
            "(WinError 10049). The network change did not stick. "
            "Approve the administrator prompt and try again."
        )
    if isinstance(exc, OSError) and winerror == 10048:
        return (
            f"Port {port} is already in use. Close the other OneClick LAN window "
            "or change the transfer port in Settings."
        )
    return f"Host error: {exc}"


class HostService:
    def __init__(
        self,
        bind_ip: str = "192.168.50.1",
        port: int = 52428,
        cert_dir: Optional[Path] = None
    ):
        self.bind_ip = bind_ip
        self.port = port
        self.cert_dir = cert_dir or (Path(os.environ.get("TEMP", ".")) / "OneClickLAN_Certs")

        self.display_code, self.raw_pairing_code = generate_pairing_code()
        self.shared_items: List[FileItem] = []
        self.total_shared_bytes: int = 0

        # State flags
        self.is_running = False
        self.is_paused = False
        self.is_cancelled = False
        self.current_client_addr: Optional[str] = None
        self.active_session_token: Optional[str] = None

        # Threading
        self.server_thread: Optional[threading.Thread] = None
        self.server_sock: Optional[socket.socket] = None
        self.ready_event = threading.Event()
        self.start_error: Optional[str] = None

        # Callbacks for UI updates
        self.on_client_connected: Optional[Callable[[str], None]] = None
        self.on_client_disconnected: Optional[Callable[[], None]] = None
        self.on_progress_update: Optional[Callable[[TransferProgress], None]] = None
        self.on_status_change: Optional[Callable[[str], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None

    def set_shared_paths(self, paths: List[str]) -> None:
        """Scan and set files and folders to share."""
        items, total_size = FileManager.scan_paths(paths)
        self.shared_items = items
        self.total_shared_bytes = total_size
        logger.info(f"Host shared {len(items)} files ({total_size} bytes).")

    def refresh_pairing_code(self) -> str:
        """Regenerate pairing code."""
        self.display_code, self.raw_pairing_code = generate_pairing_code()
        logger.info(f"Refreshed pairing code: {self.display_code}")
        return self.display_code

    def start(self) -> None:
        """Start host service on background thread."""
        if self.is_running:
            return

        self.is_running = True
        self.is_cancelled = False
        self.is_paused = False
        self.start_error = None
        self.ready_event.clear()

        self.server_thread = threading.Thread(target=self._run_server, daemon=True)
        self.server_thread.start()

    def stop(self) -> None:
        """Gracefully stop host service and close sockets."""
        self.is_running = False
        self.is_cancelled = True

        if self.server_sock:
            try:
                self.server_sock.close()
            except Exception:
                pass
            self.server_sock = None

        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=2.0)

        if self.on_status_change:
            self.on_status_change("Stopped")

        logger.info("Host service stopped.")

    def pause(self) -> None:
        self.is_paused = True
        if self.on_status_change:
            self.on_status_change("Paused")

    def resume(self) -> None:
        self.is_paused = False
        if self.on_status_change:
            self.on_status_change("Running")

    def _run_server(self) -> None:
        """Main listening loop."""
        try:
            # 1. Ephemeral TLS certificate
            cert_file = self.cert_dir / "host_cert.pem"
            key_file = self.cert_dir / "host_key.pem"
            generate_ephemeral_tls_cert(cert_file, key_file)
            ssl_ctx = create_server_ssl_context(cert_file, key_file)

            # 2. Bind raw socket
            raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            raw_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            raw_sock.bind((self.bind_ip, self.port))
            raw_sock.listen(5)
            self.server_sock = raw_sock
            self.ready_event.set()

            if self.on_status_change:
                self.on_status_change(f"Ready on {self.bind_ip}:{self.port}")

            logger.info(f"Host listening on {self.bind_ip}:{self.port}")

            while self.is_running:
                try:
                    # Select with timeout so we can exit cleanly
                    rlist, _, _ = select.select([self.server_sock], [], [], 1.0)
                    if not rlist or not self.is_running:
                        continue

                    client_raw, client_addr = self.server_sock.accept()
                    logger.info(f"Incoming connection from {client_addr}")

                    # TLS wrap
                    try:
                        tls_conn = ssl_ctx.wrap_socket(client_raw, server_side=True)
                    except Exception as e:
                        logger.error(f"TLS handshake failed from {client_addr}: {e}")
                        client_raw.close()
                        continue

                    # Authenticate client
                    success, token_or_err = server_authenticate_client(tls_conn, self.raw_pairing_code)
                    if not success:
                        logger.warning(f"Client authentication rejected: {token_or_err}")
                        tls_conn.close()
                        continue

                    self.active_session_token = token_or_err
                    self.current_client_addr = f"{client_addr[0]}:{client_addr[1]}"

                    if self.on_client_connected:
                        self.on_client_connected(self.current_client_addr)

                    # Handle authenticated client session
                    self._handle_client_session(tls_conn)

                    if self.on_client_disconnected:
                        self.on_client_disconnected()
                    self.current_client_addr = None

                except Exception as e:
                    if self.is_running:
                        logger.error(f"Error accepting connection: {e}")

        except Exception as e:
            message = format_host_error(e, self.bind_ip, self.port)
            logger.error(f"Host server error: {message}")
            if not self.ready_event.is_set():
                self.start_error = message
                self.ready_event.set()
            if self.on_error:
                self.on_error(message)
        finally:
            self.is_running = False

    def _handle_client_session(self, conn: socket.socket) -> None:
        """Process commands from authenticated client."""
        reader = conn.makefile("r", encoding="utf-8")
        tracker = TransferStatsTracker()

        try:
            while self.is_running and not self.is_cancelled:
                line = reader.readline()
                if not line:
                    break

                req = json.loads(line.strip())
                action = req.get("action")
                token = req.get("token")

                if token != self.active_session_token:
                    conn.sendall((json.dumps({"status": "ERROR", "reason": "Invalid session token."}) + "\n").encode("utf-8"))
                    break

                if action == "LIST_FILES":
                    # Send list of shared items
                    items_data = [
                        {
                            "relative_path": item.relative_path,
                            "size_bytes": item.size_bytes,
                            "modified_time": item.modified_time
                        }
                        for item in self.shared_items
                    ]
                    resp = json.dumps({"status": "OK", "files": items_data, "total_bytes": self.total_shared_bytes}) + "\n"
                    conn.sendall(resp.encode("utf-8"))

                elif action == "GET_FILE_HASH":
                    rel_path = req.get("relative_path")
                    target = next((item for item in self.shared_items if item.relative_path == rel_path), None)
                    if not target:
                        conn.sendall((json.dumps({"status": "ERROR", "reason": "File not found."}) + "\n").encode("utf-8"))
                        continue

                    sha256_hash = compute_file_sha256(target.absolute_path)
                    resp = json.dumps({"status": "OK", "sha256": sha256_hash}) + "\n"
                    conn.sendall(resp.encode("utf-8"))

                elif action == "DOWNLOAD_FILE":
                    rel_path = req.get("relative_path")
                    offset = int(req.get("offset", 0))

                    target = next((item for item in self.shared_items if item.relative_path == rel_path), None)
                    if not target:
                        conn.sendall((json.dumps({"status": "ERROR", "reason": "File not found."}) + "\n").encode("utf-8"))
                        continue

                    # Compute expected hash if needed
                    expected_hash = compute_file_sha256(target.absolute_path)

                    ready_resp = json.dumps({
                        "status": "READY",
                        "relative_path": target.relative_path,
                        "size_bytes": target.size_bytes,
                        "offset": offset,
                        "expected_sha256": expected_hash
                    }) + "\n"
                    conn.sendall(ready_resp.encode("utf-8"))

                    # Stream binary chunks
                    logger.info(f"Streaming {target.relative_path} from offset {offset}")
                    file_sent = 0

                    def on_chunk_sent(chunk_bytes: int):
                        nonlocal file_sent
                        file_sent += chunk_bytes
                        speed = tracker.update(file_sent)
                        rem_bytes = max(0, target.size_bytes - (offset + file_sent))
                        eta = tracker.calculate_eta(rem_bytes)
                        pct = ((offset + file_sent) / target.size_bytes) * 100 if target.size_bytes > 0 else 100.0

                        if self.on_progress_update:
                            self.on_progress_update(TransferProgress(
                                current_file_name=Path(target.relative_path).name,
                                file_index=1,
                                total_files=len(self.shared_items),
                                file_bytes_transferred=offset + file_sent,
                                file_total_bytes=target.size_bytes,
                                total_bytes_transferred=offset + file_sent,
                                total_batch_bytes=self.total_shared_bytes,
                                speed_mb_s=speed,
                                eta_seconds=eta,
                                percentage=pct,
                                status="Transferring"
                            ))

                    send_file_stream(
                        sock=conn,
                        file_path=target.absolute_path,
                        offset=offset,
                        progress_callback=on_chunk_sent,
                        pause_flag=lambda: self.is_paused,
                        cancel_flag=lambda: self.is_cancelled
                    )

                elif action == "DISCONNECT":
                    break

        except Exception as e:
            logger.error(f"Error handling client connection: {e}")
        finally:
            try:
                conn.close()
            except Exception:
                pass
