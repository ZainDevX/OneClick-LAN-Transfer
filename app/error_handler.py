"""
Centralized Error Handling System for OneClick LAN Transfer.
Provides structured error representations explaining:
1. What happened.
2. Why it may have happened.
3. How the user can fix it.
"""

from dataclasses import dataclass
from typing import Optional

@dataclass
class ErrorDetail:
    code: str
    title: str
    what: str
    why: str
    how: str

    def format_user_message(self) -> str:
        return (
            f"❌ **{self.title}**\n\n"
            f"**What happened:**\n{self.what}\n\n"
            f"**Why it may have happened:**\n{self.why}\n\n"
            f"**How to fix it:**\n{self.how}"
        )

class AppError(Exception):
    """Base application exception holding structured user guidance."""
    def __init__(self, error_detail: ErrorDetail, raw_exception: Optional[Exception] = None):
        super().__init__(error_detail.title)
        self.detail = error_detail
        self.raw_exception = raw_exception

# Catalog of known errors
ERROR_CATALOG = {
    "CABLE_DISCONNECTED": ErrorDetail(
        code="CABLE_DISCONNECTED",
        title="Ethernet Cable Disconnected",
        what="The physical network cable is unplugged or no link signal was detected on the selected adapter.",
        why="The Ethernet Cat6 cable is not firmly plugged in on either this computer or the remote computer, or the network port is powered off.",
        how="1. Plug the Cat6 cable firmly into the Ethernet ports of both computers.\n2. Ensure the link lights (green/orange) on the ports are blinking or lit.\n3. Try unplugging and re-inserting both ends."
    ),
    "NO_ETHERNET_ADAPTER": ErrorDetail(
        code="NO_ETHERNET_ADAPTER",
        title="No Physical Ethernet Adapter Found",
        what="The application could not detect any active physical Ethernet network interface.",
        why="Your computer might only have Wi-Fi, the Ethernet hardware driver may be missing, or the adapter is disabled in Windows Settings.",
        how="1. If using a USB-to-Ethernet adapter, ensure it is plugged in and recognized.\n2. Open Device Manager and check Network Adapters.\n3. Enable the adapter in Windows 'Network Connections' (ncpa.cpl)."
    ),
    "MULTIPLE_ETHERNET_ADAPTERS": ErrorDetail(
        code="MULTIPLE_ETHERNET_ADAPTERS",
        title="Multiple Ethernet Adapters Detected",
        what="More than one physical Ethernet adapter was found on this system.",
        why="This computer has multiple NICs (e.g. onboard LAN + USB-Ethernet dongle or dock).",
        how="Please choose the adapter connected to the direct Cat6 transfer cable from the dropdown menu before proceeding."
    ),
    "IP_CONFLICT": ErrorDetail(
        code="IP_CONFLICT",
        title="IP Address Conflict Detected",
        what="Another active network adapter or device is already using the 192.168.50.x subnet.",
        why="A virtual switch (Hyper-V / VMware / WSL) or secondary router is already assigned to this IP subnet.",
        how="1. Disconnect or disable conflicting virtual networks or VPNs.\n2. In Settings, change the transfer subnet in OneClick LAN to an alternative range (e.g. 192.168.70.x)."
    ),
    "STATIC_IP_FAILED": ErrorDetail(
        code="STATIC_IP_FAILED",
        title="Static IP Configuration Failed",
        what="The application was unable to set the static IP address on the selected network adapter.",
        why="Windows Netsh was denied, the adapter name was rejected, or the adapter was busy.",
        how="1. Approve the administrator prompt for OneClick LAN.\n2. Confirm the Ethernet adapter is enabled in Windows Network Connections.\n3. Try again. If it still fails, use Restore Original Network Settings."
    ),
    "IP_NOT_ASSIGNED": ErrorDetail(
        code="IP_NOT_ASSIGNED",
        title="Static IP Was Not Assigned",
        what="Windows did not put the requested address on the selected Ethernet adapter.",
        why="The address command did not stick. A disconnected cable, a cancelled administrator prompt, or another program changing the adapter can cause this.",
        how="1. Plug the Ethernet cable into this computer.\n2. Approve the single administrator prompt.\n3. Click Start Host again. Do not continue until this computer actually shows the new address."
    ),
    "ELEVATION_CANCELLED": ErrorDetail(
        code="ELEVATION_CANCELLED",
        title="Administrator Permission Cancelled",
        what="The network change was not applied because the administrator prompt was cancelled.",
        why="Setting a static IP and a firewall rule requires administrator permission on Windows.",
        how="Click the action again and choose Yes on the single Windows permission prompt."
    ),
    "HOST_UNREACHABLE": ErrorDetail(
        code="HOST_UNREACHABLE",
        title="Host Unreachable",
        what="The client computer could not establish a connection to the Host PC at the specified IP.",
        why="The Host application may not be running, the Host static IP may not be configured yet, or the Ethernet cable is disconnected.",
        how="1. Ensure the Host PC has 'Host Mode' active and shows 'Ready for Connections'.\n2. Verify both PCs are connected with the Cat6 cable.\n3. Verify the Host IP matches (default: 192.168.50.1)."
    ),
    "FIREWALL_BLOCKED": ErrorDetail(
        code="FIREWALL_BLOCKED",
        title="Windows Firewall Blocked Connection",
        what="The network connection was refused or dropped by Windows Defender Firewall.",
        why="Windows network profile was set to 'Public' or firewall inbound rules are blocking the application port.",
        how="1. Allow OneClick LAN through Windows Firewall when prompted.\n2. In the app settings, click 'Configure Firewall Rules' (requires Admin).\n3. Ensure the direct Ethernet profile is set to Private."
    ),
    "AUTH_FAILED": ErrorDetail(
        code="AUTH_FAILED",
        title="Authentication Failed",
        what="The pairing authentication between the Client and Host was rejected.",
        why="The pairing code was entered incorrectly, expired, or a security session token mismatch occurred.",
        how="1. Check the 6-digit pairing code displayed on the Host PC screen.\n2. Re-enter the exact pairing code on the Client PC.\n3. If renewed, click Refresh on the Host to generate a fresh pairing code."
    ),
    "INVALID_PAIRING_CODE": ErrorDetail(
        code="INVALID_PAIRING_CODE",
        title="Invalid Pairing Code Format",
        what="The entered pairing code is invalid or empty.",
        why="Pairing codes are 6-character secure codes (e.g. 748-291).",
        how="Look at the Host PC screen and copy or type the 6 digits shown."
    ),
    "TLS_FAILED": ErrorDetail(
        code="TLS_FAILED",
        title="TLS Encryption Handshake Failed",
        what="Unable to establish a secure encrypted TLS channel between Host and Client.",
        why="SSL/TLS certificate negotiation failed, network packet corruption occurred, or security policies interfered.",
        how="1. Restart the Host and Client services in the application.\n2. Check for third-party antivirus SSL-intercept tools (e.g. Kaspersky/Avast web shield).\n3. Re-try the connection."
    ),
    "INSUFFICIENT_DISK_SPACE": ErrorDetail(
        code="INSUFFICIENT_DISK_SPACE",
        title="Insufficient Disk Space",
        what="The destination drive does not have enough free space to receive the selected files.",
        why="The total incoming file size exceeds available disk space on the target partition.",
        how="1. Select a different drive or folder with enough free storage.\n2. Free up space on the destination drive before restarting the transfer."
    ),
    "FILE_ACCESS_DENIED": ErrorDetail(
        code="FILE_ACCESS_DENIED",
        title="File Access Denied / Permission Error",
        what="The application could not open or read the source file, or could not write to the destination folder.",
        why="The file may be in use by another program (e.g. Word, ISO mounter), or Windows file permissions restrict access.",
        how="1. Close any application that currently has the file open.\n2. Run OneClick LAN as Administrator if accessing protected system directories.\n3. Select a destination folder with normal user write permissions (e.g., Downloads, Documents, or external drive)."
    ),
    "DESTINATION_UNAVAILABLE": ErrorDetail(
        code="DESTINATION_UNAVAILABLE",
        title="Destination Path Unavailable",
        what="The selected destination directory cannot be found or is no longer accessible.",
        why="The target external drive might have been disconnected or the directory was moved/deleted.",
        how="1. Check that the destination drive is plugged in.\n2. Re-select an active local folder on the Client."
    ),
    "TRANSFER_INTERRUPTED": ErrorDetail(
        code="TRANSFER_INTERRUPTED",
        title="Transfer Interrupted",
        what="The file transfer stream was disconnected before completion.",
        why="The Ethernet cable was unplugged, the remote application was closed, or network timeout occurred.",
        how="1. Check physical cable connection.\n2. Reconnect the Client to Host.\n3. Click 'Resume Transfer' to pick up exactly where it left off without re-downloading."
    ),
    "HASH_MISMATCH": ErrorDetail(
        code="HASH_MISMATCH",
        title="File Integrity Verification (SHA-256) Failed",
        what="The received file's SHA-256 cryptographic checksum does not match the source file on the Host.",
        why="Data corruption occurred during transmission, bad memory (RAM), or faulty drive sector.",
        how="1. OneClick LAN automatically rejects corrupt files.\n2. Click 'Retry Transfer' to re-verify and re-download the affected file chunks."
    ),
    "PORT_IN_USE": ErrorDetail(
        code="PORT_IN_USE",
        title="Network Port Already in Use",
        what="The application transfer port (default 52428) is already bound by another process.",
        why="Another instance of OneClick LAN is already running, or another service is using this TCP port.",
        how="1. Check Task Manager and close any running instance of OneClick LAN.\n2. In Settings, change the Transfer Port number."
    ),
    "PERMISSION_DENIED": ErrorDetail(
        code="PERMISSION_DENIED",
        title="Administrator Privileges Required",
        what="An operation requiring Windows administrative privileges was rejected.",
        why="Configuring IP addresses and Windows Firewall rules requires elevated rights on Windows.",
        how="Right-click OneClickLAN.exe and choose 'Run as Administrator', or click 'Elevate' when prompted."
    ),
    "UNSUPPORTED_WINDOWS": ErrorDetail(
        code="UNSUPPORTED_WINDOWS",
        title="Unsupported Windows Version",
        what="The operating system is not supported by OneClick LAN.",
        why="OneClick LAN requires Windows 10 or Windows 11 with modern PowerShell and Netsh networking APIs.",
        how="Please upgrade your operating system to Windows 10 (version 1809+) or Windows 11."
    )
}

def get_error(code: str, custom_message: Optional[str] = None) -> ErrorDetail:
    """Retrieve error detail by code, optionally appending custom context."""
    if code in ERROR_CATALOG:
        base = ERROR_CATALOG[code]
        if custom_message:
            return ErrorDetail(
                code=base.code,
                title=base.title,
                what=f"{base.what}\n\n*Details: {custom_message}*",
                why=base.why,
                how=base.how
            )
        return base
    return ErrorDetail(
        code="UNKNOWN_ERROR",
        title="Unexpected Error Occurred",
        what=f"An unexpected error occurred: {custom_message or 'Unknown'}",
        why="An unhandled system exception or runtime failure took place.",
        how="Check application logs in the 'logs/' folder or restart the application."
    )
