"""
Client Service for OneClick LAN Transfer.
Connects to Host over direct Cat6 Ethernet, authenticates via pairing code,
fetches file list, streams chunks with resume support, and verifies SHA-256 integrity.
"""

import os
import json
import time
import socket
import logging
import threading
from pathlib import Path
from typing import List, Dict, Optional, Callable, Any, Tuple

from .file_manager import FileManager
from .authentication import (
    create_client_ssl_context,
    client_authenticate_host
)
from .integrity import verify_file_integrity, compute_file_sha256
from .transfer_engine import receive_file_stream, TransferStatsTracker, TransferProgress
from .error_handler import AppError, get_error

logger = logging.getLogger("OneClickLAN.Client")

class ClientService:
    def __init__(
        self,
        host_ip: str = "192.168.50.1",
        port: int = 52428,
        destination_dir: Optional[str] = None
    ):
        self.host_ip = host_ip
        self.port = port
        self.destination_dir = destination_dir or str(Path.home() / "Downloads" / "OneClickLAN_Transfers")

        # Session state
        self.session_token: Optional[str] = None
        self.remote_files: List[Dict[str, Any]] = []
        self.total_remote_bytes: int = 0
        self.is_connected = False
        self.is_transferring = False
        self.is_paused = False
        self.is_cancelled = False

        # Current socket
        self.tls_conn: Optional[socket.socket] = None

        # Callbacks for UI
        self.on_connected: Optional[Callable[[], None]] = None
        self.on_disconnected: Optional[Callable[[], None]] = None
        self.on_files_received: Optional[Callable[[List[Dict[str, Any]], int], None]] = None
        self.on_progress_update: Optional[Callable[[TransferProgress], None]] = None
        self.on_status_change: Optional[Callable[[str], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        self.on_transfer_complete: Optional[Callable[[], None]] = None

    def connect_and_authenticate(self, pairing_code: str, timeout: float = 5.0) -> Tuple[bool, str]:
        """
        Connects to the Host PC and executes mutual authentication.
        """
        try:
            logger.info(f"Connecting to Host at {self.host_ip}:{self.port}...")
            raw_sock = socket.create_connection((self.host_ip, self.port), timeout=timeout)
            ssl_ctx = create_client_ssl_context()
            self.tls_conn = ssl_ctx.wrap_socket(raw_sock)

            # Authenticate with pairing code
            success, token_or_err = client_authenticate_host(self.tls_conn, pairing_code)
            if not success:
                self.tls_conn.close()
                self.tls_conn = None
                return False, token_or_err

            self.session_token = token_or_err
            self.is_connected = True
            logger.info("Successfully connected and authenticated with Host!")

            if self.on_connected:
                self.on_connected()

            return True, "Connected and Authenticated"

        except ConnectionRefusedError:
            return False, "Connection refused. Host service may not be running or IP is incorrect."
        except socket.timeout:
            return False, "Connection timed out. Check Ethernet cable connection."
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return False, str(e)

    def fetch_shared_files(self) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Retrieve list of shared files from Host.
        """
        if not self.tls_conn or not self.session_token:
            return False, []

        try:
            req = json.dumps({"action": "LIST_FILES", "token": self.session_token}) + "\n"
            self.tls_conn.sendall(req.encode("utf-8"))

            reader = self.tls_conn.makefile("r", encoding="utf-8")
            line = reader.readline()
            if not line:
                return False, []

            data = json.loads(line.strip())
            if data.get("status") == "OK":
                self.remote_files = data.get("files", [])
                self.total_remote_bytes = data.get("total_bytes", 0)
                if self.on_files_received:
                    self.on_files_received(self.remote_files, self.total_remote_bytes)
                return True, self.remote_files
            else:
                return False, []
        except Exception as e:
            logger.error(f"Error fetching file list: {e}")
            return False, []

    def start_transfer_batch(self, selected_files: Optional[List[str]] = None) -> None:
        """Start transfer in background worker thread."""
        if self.is_transferring:
            return

        self.is_transferring = True
        self.is_cancelled = False
        self.is_paused = False

        thread = threading.Thread(
            target=self._run_transfer_batch,
            args=(selected_files,),
            daemon=True
        )
        thread.start()

    def pause(self) -> None:
        self.is_paused = True
        if self.on_status_change:
            self.on_status_change("Transfer Paused")

    def resume(self) -> None:
        self.is_paused = False
        if self.on_status_change:
            self.on_status_change("Transfer Resumed")

    def cancel(self) -> None:
        self.is_cancelled = True
        self.is_transferring = False
        if self.on_status_change:
            self.on_status_change("Transfer Cancelled")

    def disconnect(self) -> None:
        self.cancel()
        if self.tls_conn:
            try:
                self.tls_conn.close()
            except Exception:
                pass
            self.tls_conn = None
        self.is_connected = False
        if self.on_disconnected:
            self.on_disconnected()

    def _run_transfer_batch(self, selected_files: Optional[List[str]]) -> None:
        """Executes the file batch download sequence."""
        try:
            # Filter files to download
            if selected_files is not None:
                targets = [f for f in self.remote_files if f["relative_path"] in selected_files]
            else:
                targets = list(self.remote_files)

            if not targets:
                logger.warning("No files selected for transfer.")
                self.is_transferring = False
                return

            total_batch_bytes = sum(f["size_bytes"] for f in targets)

            # Check disk space
            if not FileManager.check_disk_space(self.destination_dir, total_batch_bytes):
                raise AppError(get_error("INSUFFICIENT_DISK_SPACE"))

            tracker = TransferStatsTracker()
            cumulative_batch_bytes = 0

            for idx, file_info in enumerate(targets, start=1):
                if self.is_cancelled:
                    break

                rel_path = file_info["relative_path"]
                total_file_size = file_info["size_bytes"]
                file_name = Path(rel_path).name

                # Determine destination and partial path
                final_path, part_path = FileManager.get_destination_target(self.destination_dir, rel_path)

                # Check if partial file exists for resume
                offset = 0
                if part_path.exists():
                    current_part_size = part_path.stat().st_size
                    if current_part_size < total_file_size:
                        offset = current_part_size
                        logger.info(f"Resuming {file_name} from byte offset {offset}")
                    elif current_part_size == total_file_size:
                        # Already finished bytes, just verify
                        offset = current_part_size

                # Request file from Host
                if offset < total_file_size:
                    req = json.dumps({
                        "action": "DOWNLOAD_FILE",
                        "relative_path": rel_path,
                        "offset": offset,
                        "token": self.session_token
                    }) + "\n"
                    self.tls_conn.sendall(req.encode("utf-8"))

                    reader = self.tls_conn.makefile("r", encoding="utf-8")
                    line = reader.readline()
                    if not line:
                        raise AppError(get_error("TRANSFER_INTERRUPTED", "Host closed connection before stream."))

                    resp = json.loads(line.strip())
                    if resp.get("status") != "READY":
                        raise AppError(get_error("TRANSFER_INTERRUPTED", resp.get("reason", "Host not ready.")))

                    expected_sha256 = resp.get("expected_sha256")
                    bytes_to_receive = total_file_size - offset

                    file_received = 0

                    def on_chunk(chunk_len: int):
                        nonlocal file_received, cumulative_batch_bytes
                        file_received += chunk_len
                        cumulative_batch_bytes += chunk_len
                        speed = tracker.update(cumulative_batch_bytes)
                        rem_batch = max(0, total_batch_bytes - cumulative_batch_bytes)
                        eta = tracker.calculate_eta(rem_batch)
                        pct = (cumulative_batch_bytes / total_batch_bytes) * 100 if total_batch_bytes > 0 else 100.0

                        if self.on_progress_update:
                            self.on_progress_update(TransferProgress(
                                current_file_name=file_name,
                                file_index=idx,
                                total_files=len(targets),
                                file_bytes_transferred=offset + file_received,
                                file_total_bytes=total_file_size,
                                total_bytes_transferred=cumulative_batch_bytes,
                                total_batch_bytes=total_batch_bytes,
                                speed_mb_s=speed,
                                eta_seconds=eta,
                                percentage=pct,
                                status="Transferring"
                            ))

                    receive_file_stream(
                        sock=self.tls_conn,
                        part_path=part_path,
                        expected_bytes=bytes_to_receive,
                        offset=offset,
                        progress_callback=on_chunk,
                        pause_flag=lambda: self.is_paused,
                        cancel_flag=lambda: self.is_cancelled
                    )
                else:
                    # File was already fully downloaded in .part
                    cumulative_batch_bytes += total_file_size

                if self.is_cancelled:
                    break

                # Post-transfer SHA-256 integrity verification
                if self.on_progress_update:
                    pct = (cumulative_batch_bytes / total_batch_bytes) * 100 if total_batch_bytes > 0 else 100.0
                    self.on_progress_update(TransferProgress(
                        current_file_name=file_name,
                        file_index=idx,
                        total_files=len(targets),
                        file_bytes_transferred=total_file_size,
                        file_total_bytes=total_file_size,
                        total_bytes_transferred=cumulative_batch_bytes,
                        total_batch_bytes=total_batch_bytes,
                        speed_mb_s=0.0,
                        eta_seconds=0,
                        percentage=pct,
                        status="Verifying SHA-256..."
                    ))

                # Query expected hash if not already received
                req_hash = json.dumps({
                    "action": "GET_FILE_HASH",
                    "relative_path": rel_path,
                    "token": self.session_token
                }) + "\n"
                self.tls_conn.sendall(req_hash.encode("utf-8"))
                hash_line = self.tls_conn.makefile("r", encoding="utf-8").readline()
                hash_data = json.loads(hash_line.strip()) if hash_line else {}
                expected_hash = hash_data.get("sha256", "")

                # Verify local file hash
                if expected_hash:
                    if not verify_file_integrity(str(part_path), expected_hash):
                        raise AppError(get_error("HASH_MISMATCH", f"Checksum verification failed for {file_name}"))

                # Rename .part to final destination safely
                conflict_resolved_path = FileManager.resolve_file_conflict(final_path, conflict_strategy="rename")
                if part_path.exists():
                    part_path.replace(conflict_resolved_path)
                    logger.info(f"Verified & saved: {conflict_resolved_path}")

            if not self.is_cancelled:
                logger.info("Batch transfer completed successfully!")
                if self.on_transfer_complete:
                    self.on_transfer_complete()

        except AppError as ae:
            logger.error(f"Application error during transfer: {ae.detail.title}")
            if self.on_error:
                self.on_error(ae.detail.format_user_message())
        except Exception as e:
            logger.error(f"Unexpected error during transfer: {e}")
            if self.on_error:
                err = get_error("TRANSFER_INTERRUPTED", str(e))
                self.on_error(err.format_user_message())
        finally:
            self.is_transferring = False
