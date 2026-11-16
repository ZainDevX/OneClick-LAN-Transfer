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
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List

from .adapter_detection import AdapterInfo, get_adapter_ip_config, get_all_adapters
from .permissions import run_elevated_command, get_hidden_subprocess_kwargs
from .firewall_manager import add_firewall_rule, remove_firewall_rule
from .error_handler import AppError, get_error

logger = logging.getLogger("OneClickLAN.NetworkManager")

HOST_DEFAULT_IP = "192.168.50.1"
CLIENT_DEFAULT_IP = "192.168.50.2"
DEFAULT_NETMASK = "255.255.255.0"
DEFAULT_TRANSFER_PORT = 52428

BACKUP_DIR = Path(os.environ.get("LOCALAPPDATA", ".")) / "OneClickLAN" / "backups"

class NetworkManager:
    """Handles static IP configuration, connection testing, and network restoration."""

    def __init__(self, backup_dir: Optional[Path] = None):
        self.backup_dir = backup_dir or BACKUP_DIR
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.active_adapter: Optional[AdapterInfo] = None
        self.original_backup_file: Optional[Path] = None

    def detect_ip_conflict(self, target_ip: str, adapter_index_to_ignore: int) -> bool:
        """
        Check if any active adapter on the machine (other than the selected Ethernet)
        is already assigned to the target IP or in the target subnet.
        """
        all_adapters = get_all_adapters()
        target_prefix = ".".join(target_ip.split(".")[:3])  # e.g. "192.168.50"

        for adapter in all_adapters:
            if adapter.interface_index == adapter_index_to_ignore:
                continue
            if not adapter.is_connected:
                continue
            ip = adapter.config.ipv4_address
            if ip:
                if ip == target_ip or ip.startswith(target_prefix + "."):
                    logger.warning(f"IP conflict detected on adapter {adapter.name}: {ip}")
                    return True
        return False

    def save_original_config(self, adapter: AdapterInfo) -> Path:
        """
        Save the complete original network configuration to disk before making any changes.
        """
        # Refresh current config to be 100% accurate right before changes
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
        set_private_profile: bool = True
    ) -> Tuple[bool, str]:
        """
        Safely configures the specified adapter with a static IP and Private network profile.
        Never modifies Wi-Fi adapters.
        """
        # Safety checks
        if adapter.is_wifi:
            raise AppError(get_error("NO_ETHERNET_ADAPTER", "Refusing to modify a Wi-Fi adapter for security."))

        # Detect IP conflict
        if self.detect_ip_conflict(ip_address, adapter.interface_index):
            raise AppError(get_error("IP_CONFLICT", f"Subnet conflict with IP {ip_address} on another interface."))

        # 1. Save original configuration
        self.save_original_config(adapter)
        self.active_adapter = adapter

        # 2. Apply static IP via netsh
        cmd_ip = (
            f'netsh interface ipv4 set address '
            f'name="{adapter.name}" '
            f'source=static '
            f'address={ip_address} '
            f'mask={subnet_mask} '
            f'gateway=none'
        )

        logger.info(f"Configuring static IP: {cmd_ip}")
        success, out = run_elevated_command(cmd_ip)
        if not success:
            logger.error(f"Failed to set static IP: {out}")
            raise AppError(get_error("STATIC_IP_FAILED", out))

        # 3. Clear DNS servers on direct cable adapter
        cmd_dns = f'netsh interface ipv4 delete dnsservers name="{adapter.name}" all'
        run_elevated_command(cmd_dns)

        # 4. Set Private Network Profile in Windows
        if set_private_profile:
            cmd_profile = (
                f"powershell -NoProfile -Command "
                f"\"Set-NetConnectionProfile -InterfaceAlias '{adapter.name}' -NetworkCategory Private -ErrorAction SilentlyContinue\""
            )
            run_elevated_command(cmd_profile)

        # 5. Verify configuration
        time.sleep(1.0)
        verify_config = get_adapter_ip_config(adapter.interface_index)
        if verify_config.ipv4_address == ip_address:
            logger.info(f"Verified static IP {ip_address} on {adapter.name}")
            return True, f"Configured {adapter.name} with IP {ip_address}"
        else:
            logger.warning(f"Verification mismatch: expected {ip_address}, got {verify_config.ipv4_address}")
            return True, f"Configured {adapter.name} with IP {ip_address} (pending adapter update)"

    def configure_host_network(self, adapter: AdapterInfo, port: int = DEFAULT_TRANSFER_PORT) -> Tuple[bool, str]:
        """One-click configuration for HOST mode."""
        res, msg = self.configure_adapter_static_ip(adapter, HOST_DEFAULT_IP, DEFAULT_NETMASK)
        add_firewall_rule(port)
        return res, msg

    def configure_client_network(self, adapter: AdapterInfo) -> Tuple[bool, str]:
        """One-click configuration for CLIENT mode."""
        return self.configure_adapter_static_ip(adapter, CLIENT_DEFAULT_IP, DEFAULT_NETMASK)

    def restore_adapter_configuration(self, adapter: Optional[AdapterInfo] = None) -> Tuple[bool, str]:
        """
        Restores the network adapter back to its original configuration (DHCP or original static IP)
        from the saved backup file.
        """
        target = adapter or self.active_adapter
        if not target:
            # Look for any recent backup file in backup_dir
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
            with open(backup_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            adapter_name = data.get("adapter_name")
            dhcp_enabled = data.get("dhcp_enabled", True)

            logger.info(f"Restoring adapter '{adapter_name}' (DHCP: {dhcp_enabled})...")

            if dhcp_enabled:
                cmd_dhcp = f'netsh interface ipv4 set address name="{adapter_name}" source=dhcp'
                success, out = run_elevated_command(cmd_dhcp)
                cmd_dns_dhcp = f'netsh interface ipv4 set dnsservers name="{adapter_name}" source=dhcp'
                run_elevated_command(cmd_dns_dhcp)
            else:
                orig_ip = data.get("ipv4_address")
                orig_mask = data.get("subnet_mask", DEFAULT_NETMASK)
                orig_gw = data.get("default_gateway")
                gw_str = f"gateway={orig_gw}" if orig_gw else "gateway=none"
                cmd_static = (
                    f'netsh interface ipv4 set address '
                    f'name="{adapter_name}" '
                    f'source=static '
                    f'address={orig_ip} '
                    f'mask={orig_mask} '
                    f'{gw_str}'
                )
                success, out = run_elevated_command(cmd_static)

                # Restore DNS if static
                dns_list = data.get("dns_servers", [])
                if dns_list:
                    cmd_dns = f'netsh interface ipv4 set dnsservers name="{adapter_name}" source=static address={dns_list[0]} validate=no'
                    run_elevated_command(cmd_dns)
                    for dns in dns_list[1:]:
                        run_elevated_command(f'netsh interface ipv4 add dnsservers name="{adapter_name}" address={dns} validate=no')

            # Clean up firewall rule
            remove_firewall_rule()

            # Remove backup file once successfully restored
            try:
                backup_file.unlink(missing_ok=True)
            except Exception:
                pass

            self.active_adapter = None
            return True, f"Successfully restored {adapter_name} to original settings."
        except Exception as e:
            logger.error(f"Restoration error: {e}")
            return False, f"Restoration failed: {str(e)}"

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
