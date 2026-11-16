"""
File Integrity and Cryptographic Hashing Engine
Computes and verifies SHA-256 hashes for large files (1GB, 10GB, 100GB+) with minimal RAM footprint.
"""

import hashlib
import os
from typing import Callable, Optional
import logging

logger = logging.getLogger("OneClickLAN.Integrity")

# 4 MB read chunks for hashing provides high throughput without ballooning memory
DEFAULT_HASH_CHUNK_SIZE = 4 * 1024 * 1024  

def compute_file_sha256(
    file_path: str,
    total_bytes: Optional[int] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None,
    cancel_flag: Optional[Callable[[], bool]] = None,
    chunk_size: int = DEFAULT_HASH_CHUNK_SIZE,
    offset: int = 0,
    length: Optional[int] = None
) -> Optional[str]:
    """
    Computes SHA-256 hash of a file or byte range in chunks.
    
    :param file_path: Path to the file.
    :param total_bytes: Optional known size for progress calculation.
    :param progress_callback: Callable(processed_bytes, total_bytes)
    :param cancel_flag: Callable returning True if computation should abort.
    :param chunk_size: Read buffer size in bytes.
    :param offset: Byte offset to start reading from.
    :param length: Total bytes to read from offset (or None for until EOF).
    :return: Hex digest string of SHA-256, or None if cancelled or failed.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found for hash calculation: {file_path}")

    actual_file_size = os.path.getsize(file_path)
    if length is None:
        target_size = max(0, actual_file_size - offset)
    else:
        target_size = min(length, max(0, actual_file_size - offset))

    hasher = hashlib.sha256()
    bytes_read = 0

    try:
        with open(file_path, "rb") as f:
            if offset > 0:
                f.seek(offset)

            while bytes_read < target_size:
                if cancel_flag and cancel_flag():
                    logger.info(f"Hashing cancelled for {file_path}")
                    return None

                bytes_to_read = min(chunk_size, target_size - bytes_read)
                buf = f.read(bytes_to_read)
                if not buf:
                    break

                hasher.update(buf)
                bytes_read += len(buf)

                if progress_callback:
                    progress_callback(bytes_read, target_size)

        return hasher.hexdigest().lower()
    except Exception as e:
        logger.error(f"Error computing hash for {file_path}: {e}")
        raise

def verify_file_integrity(
    file_path: str,
    expected_hash: str,
    progress_callback: Optional[Callable[[int, int], None]] = None,
    cancel_flag: Optional[Callable[[], bool]] = None
) -> bool:
    """
    Verifies that the SHA-256 of the given file matches expected_hash.
    """
    calculated_hash = compute_file_sha256(
        file_path,
        progress_callback=progress_callback,
        cancel_flag=cancel_flag
    )
    if calculated_hash is None:
        return False
    return calculated_hash.lower() == expected_hash.lower().strip()
