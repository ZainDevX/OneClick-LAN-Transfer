"""
File and Directory Management for OneClick LAN Transfer.
Handles file scanning, recursive folder flattening, path sanitization,
disk space verification, and safe temporary file writing (.part).
"""

import os
import shutil
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional, Tuple
from .error_handler import AppError, get_error

logger = logging.getLogger("OneClickLAN.FileManager")

@dataclass
class FileItem:
    relative_path: str       # e.g. "GameData/archive.iso" or "setup.exe"
    absolute_path: str       # local full path on Host
    size_bytes: int          # file size in bytes
    modified_time: float     # mtime timestamp
    is_directory: bool = False

class FileManager:
    @staticmethod
    def sanitize_relative_path(rel_path: str) -> str:
        """
        Sanitize relative path to strictly prevent directory traversal (e.g. ../../)
        """
        # Normalize separators
        clean = rel_path.replace("\\", "/").strip()
        parts = [p for p in clean.split("/") if p and p not in [".", ".."]]
        return "/".join(parts)

    @staticmethod
    def scan_paths(paths: List[str]) -> Tuple[List[FileItem], int]:
        """
        Scan list of file or folder paths and produce a flat list of FileItem entries.
        Returns (items, total_size_bytes).
        """
        items: List[FileItem] = []
        total_size = 0

        for p_str in paths:
            p = Path(p_str)
            if not p.exists():
                logger.warning(f"File or directory does not exist: {p}")
                continue

            if p.is_file():
                try:
                    stat = p.stat()
                    items.append(FileItem(
                        relative_path=p.name,
                        absolute_path=str(p.resolve()),
                        size_bytes=stat.st_size,
                        modified_time=stat.st_mtime,
                        is_directory=False
                    ))
                    total_size += stat.st_size
                except Exception as e:
                    logger.error(f"Cannot read file stat for {p}: {e}")

            elif p.is_dir():
                parent_dir = p.parent
                for root, dirs, files in os.walk(p):
                    root_path = Path(root)
                    for file_name in files:
                        full_path = root_path / file_name
                        try:
                            rel_path = full_path.relative_to(parent_dir).as_posix()
                            stat = full_path.stat()
                            items.append(FileItem(
                                relative_path=rel_path,
                                absolute_path=str(full_path.resolve()),
                                size_bytes=stat.st_size,
                                modified_time=stat.st_mtime,
                                is_directory=False
                            ))
                            total_size += stat.st_size
                        except Exception as e:
                            logger.error(f"Error scanning {full_path}: {e}")

        return items, total_size

    @staticmethod
    def check_disk_space(dest_dir: str, required_bytes: int) -> bool:
        """
        Verifies that the target volume has sufficient free space.
        Adds a 100MB safety margin.
        """
        try:
            path = Path(dest_dir).resolve()
            # If path doesn't exist yet, check its nearest existing parent
            while not path.exists() and path.parent != path:
                path = path.parent

            usage = shutil.disk_usage(path)
            # Require required_bytes + 100MB safety buffer
            safety_margin = 100 * 1024 * 1024
            if usage.free < (required_bytes + safety_margin):
                return False
            return True
        except Exception as e:
            logger.warning(f"Could not check disk space on {dest_dir}: {e}")
            return True  # Fallback to allow attempt if unable to query

    @staticmethod
    def get_destination_target(dest_dir: str, rel_path: str) -> Tuple[Path, Path]:
        """
        Determines target final path and temporary partial file (.part) path.
        Ensures destination subdirectories are created.
        Returns (final_path, part_path).
        """
        safe_rel = FileManager.sanitize_relative_path(rel_path)
        base = Path(dest_dir).resolve()
        final_path = (base / safe_rel).resolve()

        # Enforce destination sandbox
        if not str(final_path).startswith(str(base)):
            raise AppError(get_error("FILE_ACCESS_DENIED", "Path traversal detected in file item."))

        final_path.parent.mkdir(parents=True, exist_ok=True)
        part_path = final_path.with_name(final_path.name + ".oneclick.part")

        return final_path, part_path

    @staticmethod
    def resolve_file_conflict(final_path: Path, conflict_strategy: str = "rename") -> Path:
        """
        Handles collision if destination file already exists:
        - 'rename': Setup.exe -> Setup (1).exe
        - 'overwrite': returns final_path directly
        """
        if not final_path.exists() or conflict_strategy == "overwrite":
            return final_path

        stem = final_path.stem
        suffix = final_path.suffix
        parent = final_path.parent
        counter = 1

        while True:
            candidate = parent / f"{stem} ({counter}){suffix}"
            if not candidate.exists():
                return candidate
            counter += 1
