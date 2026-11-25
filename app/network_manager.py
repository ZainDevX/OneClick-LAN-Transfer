"""
One-Click Network Configuration and Restoration Manager.
Manages automatic static IP configuration (192.168.50.1 / 192.168.50.2),
Private network profile setting, subnet conflict detection, and non-destructive restoration.
"""

import os
import json
import time
import socket
import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Tuple

from .adapter_detection import AdapterInfo, find_subnet_conflict, get_adapter_ip_config, wait_for_ipv4
from .permissions import (
    PrivilegedCommand,
    adapter_name_is_safe,
    command_is_allowed,
    get_hidden_subprocess_kwargs,
    run_privileged_commands,
)
from .firewall_manager import firewall_add_command, firewall_delete_command, rule_exists
from .error_handler import AppError, get_error

logger = logging.getLogger("OneClickLAN.NetworkManager")

HOST_DEFAULT_IP = "192.168.50.1"
CLIENT_DEFAULT_IP = "192.168.50.2"
DEFAULT_NETMASK = "255.255.255.0"
DEFAULT_TRANSFER_PORT = 52428

BACKUP_DIR = Path(os.environ.get("LOCALAPPDATA", ".")) / "OneClickLAN" / "backups"
IP_VERIFY_TIMEOUT_SECONDS = 3.0
IP_VERIFY_INTERVAL_SECONDS = 0.1


@dataclass
class NetworkApplyResult:
    """Outcome of one static-IP action. ip_verified is never implied."""

    ip_verified: bool
    firewall_ok: Optional[bool]
    message: str
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.ip_verified


class NetworkManager:
    """Handles static IP configuration, connection testing, and network restoration."""

    def __init__(self, backup_dir: Optional[Path] = None):
        self.backup_dir = backup_dir or BACKUP_DIR
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.active_adapter: Optional[AdapterInfo] = None
        self.original_backup_file: Optional[Path] = None

    def detect_ip_conflict(self, target_ip: str, adapter_name_to_ignore: str) -> bool:
        """
        True when another adapter that is up already uses target_ip or its /24.
        Uses the current address table. It does not start PowerShell.
        """
        other = find_subnet_conflict(target_ip, adapter_name_to_ignore)
        if other:
            logger.warning(f"IP conflict detected on adapter {other} for {target_ip}")
            return True
        return False

    def save_original_config(self, adapter: AdapterInfo) -> Path:
        """
        Save the complete original network configuration to disk before making any changes.
        """
        # Read this adapter only. Keep the supplied config when Windows returns nothing.
        fresh_config = get_adapter_ip_config(adapter.interface_index)
        if fresh_config.ipv4_address is not None or fresh_config.dns_servers:
            adapter.config = fresh_config

        backup_data = {
            "timestamp": time.time(),
            "adapter_name": adapter.name,
            "interface_description": adapter.interface_description,
            "interface_index": adapter.interface_index,
            "mac_address": adapter.mac_address,
            "dhcp_enabled": adapter.config.dhcp_enabled,
            "ipv4_address": adapter.config.ipv4_address,
            "subnet_mask": adapter.config.subnet_mask,
            "prefix_length": adapter.config.prefix_length,
            "default_gateway": adapter.config.default_gateway,
            "dns_servers": adapter.config.dns_servers,
        }

        # Safe filename
        safe_name = "".join([c if c.isalnum() else "_" for c in adapter.name])
        backup_file = self.backup_dir / f"backup_{safe_name}_{adapter.interface_index}.json"

        # If backup file already exists and we are not restored yet, do NOT overwrite it
        # with our own static IP! Only write if not already backed up or if DHCP.
        if backup_file.exists():
            try:
                with open(backup_file, "r") as f:
                    existing = json.load(f)
                # If existing is already a static 192.168.50.x from an earlier run, don't overwrite
                if existing.get("ipv4_address") in [HOST_DEFAULT_IP, CLIENT_DEFAULT_IP]:
                    logger.info("Retaining previous original backup before static assignment.")
                    self.original_backup_file = backup_file
                    return backup_file
            except Exception:
                pass

        with open(backup_file, "w", encoding="utf-8") as f:
            json.dump(backup_data, f, indent=4)

        logger.info(f"Saved original network configuration to {backup_file}")
        self.original_backup_file = backup_file
        return backup_file

    def configure_adapter_static_ip(
        self,
        adapter: AdapterInfo,
        ip_address: str,
        subnet_mask: str = DEFAULT_NETMASK,
        set_private_profile: bool = True,
        extra_commands: Optional[list[PrivilegedCommand]] = None,
        expect_firewall: bool = False,
    ) -> NetworkApplyResult:
        """
        Configure one Ethernet adapter and verify the address is actually present.
        Every privileged command for this action runs inside one elevation.
        """
        if adapter.is_wifi:
            raise AppError(get_error("NO_ETHERNET_ADAPTER", "Refusing to modify a Wi-Fi adapter for security."))
        if not adapter_name_is_safe(adapter.name):
            raise AppError(get_error(
                "STATIC_IP_FAILED",
                f"Adapter name {adapter.name!r} cannot be configured safely.",
            ))
        if self.detect_ip_conflict(ip_address, adapter.name):
            raise AppError(get_error("IP_CONFLICT", f"Subnet conflict with IP {ip_address} on another interface."))

        self.save_original_config(adapter)
        self.active_adapter = adapter

        commands = [
            PrivilegedCommand(_static_ip_command(adapter.name, ip_address, subnet_mask), True, "Set static IP"),
            PrivilegedCommand(
                f'netsh interface ipv4 delete dnsservers name="{adapter.name}" all',
                False,
                "Clear DNS",
            ),
        ]
        if set_private_profile:
            profile_command = _private_profile_command(adapter.name)
            if command_is_allowed(profile_command):
                commands.append(PrivilegedCommand(profile_command, False, "Private network profile"))
        if extra_commands:
            commands.extend(extra_commands)

        logger.info("Applying network commands for %s -> %s", adapter.name, ip_address)
        batch = run_privileged_commands(commands)
        if batch.cancelled:
            raise AppError(get_error("ELEVATION_CANCELLED"))
        if batch.launch_error:
            raise AppError(get_error("STATIC_IP_FAILED", batch.launch_error))

        ip_result = _labeled(batch.results, "Set static IP")
        if ip_result is None or not ip_result.ok:
            detail = _command_output(ip_result) or "The static IP command did not run."
            logger.error("Static IP command failed: %s", detail)
            raise AppError(get_error("STATIC_IP_FAILED", detail))

        verified, found = wait_for_ipv4(
            adapter.name,
            ip_address,
            timeout=IP_VERIFY_TIMEOUT_SECONDS,
            interval=IP_VERIFY_INTERVAL_SECONDS,
        )
        warnings = _optional_warnings(batch.results)
        firewall_ok = _firewall_status(batch.results, expect_firewall)
        if not verified:
            found_text = ", ".join(found) if found else "no IPv4 address"
            cable = " The Ethernet cable looks disconnected." if not adapter.is_connected else ""
            detail = (
                f"Expected {ip_address} on {adapter.name}, found {found_text}.{cable}"
            )
            logger.error("Verification mismatch: %s", detail)
            return NetworkApplyResult(
                ip_verified=False,
                firewall_ok=firewall_ok,
                message=get_error("IP_NOT_ASSIGNED", detail).format_user_message(),
                warnings=warnings,
            )

        logger.info("Verified static IP %s on %s", ip_address, adapter.name)
        message = f"Configured {adapter.name} with IP {ip_address}."
        if firewall_ok is False:
            firewall_result = _labeled(batch.results, "Firewall rule")
            firewall_detail = _command_output(firewall_result) or "The firewall command failed."
            message = (
                f"{adapter.name} is using {ip_address}, but the firewall rule was not added. "
                f"{firewall_detail}"
            )
        if warnings:
            message += "\n\nNotes:\n" + "\n".join(warnings)
        return NetworkApplyResult(
            ip_verified=True,
            firewall_ok=firewall_ok,
            message=message,
            warnings=warnings,
        )

    def configure_host_network(self, adapter: AdapterInfo, port: int = DEFAULT_TRANSFER_PORT) -> NetworkApplyResult:
        """Set the host address and firewall rule in one administrator prompt."""
        extras = []
        firewall_expected = True
        if rule_exists():
            firewall_expected = True
        else:
            extras.append(PrivilegedCommand(firewall_add_command(port), True, "Firewall rule"))
        result = self.configure_adapter_static_ip(
            adapter,
            HOST_DEFAULT_IP,
            DEFAULT_NETMASK,
            extra_commands=extras,
            expect_firewall=firewall_expected,
        )
        if not extras and result.ip_verified and result.firewall_ok is None:
            result.firewall_ok = True
        return result

    def configure_client_network(self, adapter: AdapterInfo) -> NetworkApplyResult:
        """Set the client address. No firewall change is required on the client."""
        return self.configure_adapter_static_ip(adapter, CLIENT_DEFAULT_IP, DEFAULT_NETMASK)

    def restore_adapter_configuration(self, adapter: Optional[AdapterInfo] = None) -> Tuple[bool, str]:
        """
        Restore the saved DHCP or static configuration.
        Required address commands share one elevation with the optional firewall cleanup.
        """
        target = adapter or self.active_adapter
        if not target:
            backups = list(self.backup_dir.glob("backup_*.json"))
            if not backups:
                return False, "No previous network backup found to restore."
            backup_file = sorted(backups, key=os.path.getmtime, reverse=True)[0]
        else:
            safe_name = "".join([c if c.isalnum() else "_" for c in target.name])
            backup_file = self.backup_dir / f"backup_{safe_name}_{target.interface_index}.json"

        if not backup_file.exists():
            return False, f"Backup file not found: {backup_file}"

        try:
            with open(backup_file, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except Exception as exc:
            logger.error(f"Restoration error: {exc}")
            return False, f"Restoration failed: {exc}"

        adapter_name = data.get("adapter_name") or ""
        if not adapter_name_is_safe(adapter_name):
            return False, f"Cannot restore adapter name {adapter_name!r}."

        try:
            commands = _restore_commands(adapter_name, data)
        except AppError as exc:
            return False, exc.detail.format_user_message()
        if rule_exists():
            commands.append(PrivilegedCommand(firewall_delete_command(), False, "Remove firewall"))

        logger.info("Restoring adapter '%s' (DHCP: %s)...", adapter_name, data.get("dhcp_enabled", True))
        batch = run_privileged_commands(commands)
        if batch.cancelled:
            return False, "Administrator permission was cancelled. The adapter was not restored."
        if batch.launch_error:
            return False, f"Restoration failed: {batch.launch_error}"

        address_result = _labeled(batch.results, "Restore address")
        if address_result is None or not address_result.ok:
            detail = _command_output(address_result) or "The restore command did not run."
            logger.error("Restore address command failed: %s", detail)
            return False, f"Restoration failed: {detail}"

        try:
            backup_file.unlink(missing_ok=True)
        except Exception:
            pass
        self.active_adapter = None
        message = f"Successfully restored {adapter_name} to original settings."
        warnings = _optional_warnings(batch.results)
        if warnings:
            message += "\n\nNotes:\n" + "\n".join(warnings)
        return True, message

    def test_connectivity(self, target_ip: str = HOST_DEFAULT_IP, port: int = DEFAULT_TRANSFER_PORT, timeout: float = 3.0) -> Tuple[bool, str]:
        """
        Test reachability of target IP and application transfer port.
        """
        # First test TCP socket connection directly to application port
        try:
            with socket.create_connection((target_ip, port), timeout=timeout):
                return True, f"Connected to {target_ip}:{port} (Application service responding)"
        except ConnectionRefusedError:
            # IP is reachable, but service isn't listening
            return False, f"Host IP ({target_ip}) is reachable, but transfer service is not active on port {port}."
        except socket.timeout:
            pass
        except OSError:
            pass

        # Socket failed, check ping silently without console popup
        ping_cmd = f"ping -n 1 -w 1500 {target_ip}"
        res = subprocess.run(
            ping_cmd,
            shell=True,
            capture_output=True,
            text=True,
            check=False,
            **get_hidden_subprocess_kwargs()
        )
        if res.returncode == 0 and "Reply from" in res.stdout and "unreachable" not in res.stdout:
            return False, f"Host IP ({target_ip}) responded to ping, but transfer port {port} is not responding (Check Firewall or Host Service)."
        else:
            return False, f"Host ({target_ip}) is completely unreachable. Check Ethernet cable connection."


def _static_ip_command(adapter_name: str, ip_address: str, subnet_mask: str) -> str:
    return (
        f'netsh interface ipv4 set address '
        f'name="{adapter_name}" '
        f'source=static '
        f'address={ip_address} '
        f'mask={subnet_mask} '
        f'gateway=none'
    )


def _private_profile_command(adapter_name: str) -> str:
    return (
        "powershell -NoProfile -Command "
        f"\"Set-NetConnectionProfile -InterfaceAlias '{adapter_name}' "
        "-NetworkCategory Private -ErrorAction SilentlyContinue\""
    )


def _is_ipv4(value: Optional[str]) -> bool:
    if not value:
        return False
    parts = value.split(".")
    if len(parts) != 4:
        return False
    try:
        return all(part.isdigit() and 0 <= int(part) <= 255 for part in parts)
    except ValueError:
        return False


def _restore_commands(adapter_name: str, data: dict) -> list[PrivilegedCommand]:
    commands: list[PrivilegedCommand] = []
    if data.get("dhcp_enabled", True):
        commands.append(PrivilegedCommand(
            f'netsh interface ipv4 set address name="{adapter_name}" source=dhcp',
            True,
            "Restore address",
        ))
        commands.append(PrivilegedCommand(
            f'netsh interface ipv4 set dnsservers name="{adapter_name}" source=dhcp',
            False,
            "Restore DNS",
        ))
        return commands

    orig_ip = data.get("ipv4_address")
    orig_mask = data.get("subnet_mask") or DEFAULT_NETMASK
    orig_gw = data.get("default_gateway")
    if not _is_ipv4(orig_ip) or not _is_ipv4(orig_mask):
        raise AppError(get_error("STATIC_IP_FAILED", "The saved address is not a valid IPv4 configuration."))
    gateway = f"gateway={orig_gw}" if _is_ipv4(orig_gw) else "gateway=none"
    commands.append(PrivilegedCommand(
        (
            f'netsh interface ipv4 set address '
            f'name="{adapter_name}" source=static '
            f'address={orig_ip} mask={orig_mask} {gateway}'
        ),
        True,
        "Restore address",
    ))
    dns_list = [item for item in data.get("dns_servers", []) if _is_ipv4(item)]
    if dns_list:
        commands.append(PrivilegedCommand(
            f'netsh interface ipv4 set dnsservers name="{adapter_name}" source=static address={dns_list[0]} validate=no',
            False,
            "Restore DNS",
        ))
        for dns in dns_list[1:]:
            commands.append(PrivilegedCommand(
                f'netsh interface ipv4 add dnsservers name="{adapter_name}" address={dns} validate=no',
                False,
                "Restore DNS",
            ))
    return commands


def _labeled(results, label: str):
    for item in results:
        if item.label == label:
            return item
    return None


def _command_output(result) -> str:
    if result is None:
        return ""
    return (result.stderr or result.stdout or "").strip()


def _optional_warnings(results) -> list[str]:
    notes = []
    for item in results:
        if item.required or item.ok:
            continue
        detail = _command_output(item) or f"exit {item.returncode}"
        if item.label == "Private network profile":
            notes.append("Windows did not mark the adapter Private. This is normal when the cable is unplugged.")
        elif item.label == "Clear DNS":
            notes.append(f"DNS servers were not cleared: {detail}")
        elif item.label == "Restore DNS":
            notes.append(f"DNS settings were not fully restored: {detail}")
        elif item.label == "Remove firewall":
            notes.append(f"The firewall rule was not removed: {detail}")
        else:
            notes.append(f"{item.label or 'A step'} failed: {detail}")
    return notes


def _firewall_status(results, expect_firewall: bool) -> Optional[bool]:
    if not expect_firewall:
        return None
    found = _labeled(results, "Firewall rule")
    if found is None:
        return True
    return found.ok
