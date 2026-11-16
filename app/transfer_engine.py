"""
High-Performance Streaming File Transfer Engine for OneClick LAN Transfer.
Supports 100GB+ files, Gigabit Ethernet chunking, resume capability,
real-time statistics (MB/s, ETA, progress), and SHA-256 post-transfer verification.
"""

import os
import time
import socket
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Callable, Optional, Dict, Any, List

from .file_manager import FileManager, FileItem
from .integrity import compute_file_sha256, verify_file_integrity
from .error_handler import AppError, get_error

logger = logging.getLogger("OneClickLAN.TransferEngine")

# 2MB buffer size provides optimal throughput on Windows Gigabit TCP stacks
DEFAULT_BUFFER_SIZE = 2 * 1024 * 1024

@dataclass
class TransferProgress:
    current_file_name: str
    file_index: int
    total_files: int
    file_bytes_transferred: int
    file_total_bytes: int
    total_bytes_transferred: int
    total_batch_bytes: int
    speed_mb_s: float
    eta_seconds: int
    percentage: float
    status: str  # "Transferring", "Verifying SHA-256", "Paused", "Completed", "Failed"

class TransferStatsTracker:
    """Calculates smoothed transfer speed (MB/s) and ETA."""
    def __init__(self, window_seconds: float = 1.5):
        self.window_seconds = window_seconds
        self.history: List[Tuple[float, int]] = []  # (timestamp, cumulative_bytes)
        self.last_speed: float = 0.0

    def update(self, current_bytes: int) -> float:
        now = time.time()
        self.history.append((now, current_bytes))

        # Discard entries older than window
        cutoff = now - self.window_seconds
        self.history = [entry for entry in self.history if entry[0] >= cutoff]

        if len(self.history) >= 2:
            time_delta = self.history[-1][0] - self.history[0][0]
            bytes_delta = self.history[-1][1] - self.history[0][1]
            if time_delta > 0:
                self.last_speed = (bytes_delta / (1024 * 1024)) / time_delta

        return max(0.0, self.last_speed)

    def calculate_eta(self, remaining_bytes: int) -> int:
        if self.last_speed <= 0.01:
            return 0
        speed_bytes_sec = self.last_speed * 1024 * 1024
        return int(remaining_bytes / speed_bytes_sec)


def send_file_stream(
    sock: socket.socket,
    file_path: str,
    offset: int = 0,
    chunk_size: int = DEFAULT_BUFFER_SIZE,
    progress_callback: Optional[Callable[[int], None]] = None,
    pause_flag: Optional[Callable[[], bool]] = None,
    cancel_flag: Optional[Callable[[], bool]] = None
) -> int:
    """
    Streams binary chunks of a file across the TLS socket starting from offset.
    Yields sent bytes through progress_callback.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Source file not found: {file_path}")

    file_size = os.path.getsize(file_path)
    total_sent = 0

    with open(file_path, "rb") as f:
        if offset > 0:
            f.seek(offset)

        while (offset + total_sent) < file_size:
            if cancel_flag and cancel_flag():
                logger.info(f"Send cancelled for {file_path}")
                break

            while pause_flag and pause_flag():
                time.sleep(0.2)
                if cancel_flag and cancel_flag():
                    break

            bytes_to_read = min(chunk_size, file_size - (offset + total_sent))
            data = f.read(bytes_to_read)
            if not data:
                break

            sock.sendall(data)
            sent_len = len(data)
            total_sent += sent_len

            if progress_callback:
                progress_callback(sent_len)

    return total_sent


def receive_file_stream(
    sock: socket.socket,
    part_path: Path,
    expected_bytes: int,
    offset: int = 0,
    chunk_size: int = DEFAULT_BUFFER_SIZE,
    progress_callback: Optional[Callable[[int], None]] = None,
    pause_flag: Optional[Callable[[], bool]] = None,
    cancel_flag: Optional[Callable[[], bool]] = None
) -> int:
    """
    Receives binary stream from TLS socket and appends directly to the .part file.
    """
    part_path.parent.mkdir(parents=True, exist_ok=True)
    mode = "r+b" if part_path.exists() and offset > 0 else "wb"

    total_received = 0
    with open(part_path, mode) as f:
        if offset > 0:
            f.seek(offset)

        while total_received < expected_bytes:
            if cancel_flag and cancel_flag():
                logger.info(f"Receive cancelled for {part_path.name}")
                break

            while pause_flag and pause_flag():
                time.sleep(0.2)
                if cancel_flag and cancel_flag():
                    break

            bytes_to_read = min(chunk_size, expected_bytes - total_received)
            chunk = sock.recv(bytes_to_read)
            if not chunk:
                logger.warning(f"Connection closed by sender after {total_received}/{expected_bytes} bytes.")
                break

            f.write(chunk)
            received_len = len(chunk)
            total_received += received_len

            if progress_callback:
                progress_callback(received_len)

    return total_received
