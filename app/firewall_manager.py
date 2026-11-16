"""
Windows Defender Firewall Management for OneClick LAN Transfer.
Configures and removes strictly necessary firewall rules for direct LAN file transfer.
"""

import subprocess
import logging
from typing import Optional, List
from .permissions import is_admin, run_elevated_command, get_hidden_subprocess_kwargs

logger = logging.getLogger("OneClickLAN.Firewall")

RULE_NAME = "OneClickLAN_Direct_Transfer"

def rule_exists(rule_name: str = RULE_NAME) -> bool:
    """Check if the firewall rule already exists in Windows Firewall without flashing console windows."""
    cmd = f'netsh advfirewall firewall show rule name="{rule_name}"'
    try:
        res = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            check=False,
            **get_hidden_subprocess_kwargs()
        )
        return res.returncode == 0 and "No rules match" not in res.stdout
    except Exception as e:
        logger.warning(f"Failed to check firewall rule status: {e}")
        return False

def add_firewall_rule(port: int = 52428, rule_name: str = RULE_NAME) -> tuple[bool, str]:
    """
    Add an inbound firewall rule allowing TCP traffic on the application port.
    Applies only to Private and Domain network profiles for security.
    """
    if rule_exists(rule_name):
        logger.info(f"Firewall rule '{rule_name}' already exists.")
        return True, "Firewall rule already active."

    cmd = (
        f'netsh advfirewall firewall add rule '
        f'name="{rule_name}" '
        f'dir=in '
        f'action=allow '
        f'protocol=TCP '
        f'localport={port} '
        f'profile=private '
        f'description="Allow inbound high-speed direct Ethernet file transfers for OneClick LAN Transfer."'
    )

    logger.info(f"Adding firewall rule: {cmd}")
    success, output = run_elevated_command(cmd)
    if success:
        logger.info(f"Successfully added firewall rule '{rule_name}' for port {port}")
        return True, "Firewall rule configured successfully."
    else:
        logger.error(f"Failed to add firewall rule: {output}")
        return False, output

def remove_firewall_rule(rule_name: str = RULE_NAME) -> tuple[bool, str]:
    """
    Safely delete ONLY the firewall rule created by OneClick LAN Transfer.
    """
    if not rule_exists(rule_name):
        logger.info(f"Firewall rule '{rule_name}' does not exist, nothing to clean up.")
        return True, "Rule not present."

    cmd = f'netsh advfirewall firewall delete rule name="{rule_name}"'
    logger.info(f"Removing firewall rule: {cmd}")
    success, output = run_elevated_command(cmd)
    if success:
        logger.info(f"Successfully deleted firewall rule '{rule_name}'")
        return True, "Firewall rule removed successfully."
    else:
        logger.error(f"Failed to remove firewall rule: {output}")
        return False, output
