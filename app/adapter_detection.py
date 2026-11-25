"""
Network Adapter Detection for Windows 10 and Windows 11.
Identifies physical Ethernet adapters, filters Wi-Fi and virtual interfaces,
and extracts IP, DHCP, gateway, and DNS configurations.
"""

import subprocess
import json
import logging
import socket
import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Dict, Any

logger = logging.getLogger("OneClickLAN.AdapterDetection")

VIRTUAL_KEYWORDS = [
    "hyper-v", "virtual", "vmware", "virtualbox", "wsl", "vethernet",
    "tap", "npcap", "pcap", "loopback", "tunnel", "tailscale", "zerotier",
    "wireguard", "openvpn", "cisco", "fortinet", "nordlynx", "bluetooth"
]

WIFI_KEYWORDS = [
    "wi-fi", "wifi", "wireless", "802.11", "wlan"
]

@dataclass
class AdapterConfig:
    dhcp_enabled: bool = True
    ipv4_address: Optional[str] = None
    subnet_mask: Optional[str] = None
    prefix_length: Optional[int] = None
    default_gateway: Optional[str] = None
    dns_servers: List[str] = field(default_factory=list)

@dataclass
class AdapterInfo:
    name: str
    interface_description: str
    interface_index: int
    mac_address: str
    status: str
    link_speed: str
    physical_media_type: str
    is_connected: bool
    is_physical_ethernet: bool
    is_wifi: bool
    is_virtual: bool
    config: AdapterConfig = field(default_factory=AdapterConfig)

    def display_name(self) -> str:
        state = "Connected" if self.is_connected else "Cable Disconnected"
        speed = f" ({self.link_speed})" if self.is_connected and self.link_speed != "0 bps" else ""
        return f"{self.name} - {self.interface_description} [{state}{speed}]"


def run_powershell_json(ps_command: str) -> Optional[Any]:
    """Execute a PowerShell command and parse JSON output without flashing console windows."""
    from .permissions import get_hidden_subprocess_kwargs
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden", "-Command", ps_command],
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
            **get_hidden_subprocess_kwargs()
        )
        if proc.returncode != 0 or not proc.stdout.strip():
            return None
        return json.loads(proc.stdout)
    except Exception as e:
        logger.warning(f"PowerShell JSON execution failed: {e}")
        return None


def get_all_adapters() -> List[AdapterInfo]:
    """
    Detect all network adapters on the system using PowerShell NetAdapter cmdlets.
    """
    ps_cmd = (
        "Get-NetAdapter -IncludeHidden:$false | "
        "Select-Object Name, InterfaceDescription, InterfaceIndex, Status, LinkSpeed, "
        "PhysicalMediaType, MediaType, MacAddress | "
        "ConvertTo-Json -Compress"
    )

    data = run_powershell_json(ps_cmd)
    if not data:
        # Fallback if single adapter returned or empty
        return []

    if isinstance(data, dict):
        raw_list = [data]
    elif isinstance(data, list):
        raw_list = data
    else:
        raw_list = []

    adapters = []
    for item in raw_list:
        name = str(item.get("Name", "")).strip()
        desc = str(item.get("InterfaceDescription", "")).strip()
        idx = int(item.get("InterfaceIndex", 0))
        status = str(item.get("Status", "Unknown")).strip()
        speed = str(item.get("LinkSpeed", "0 bps")).strip()
        p_type = str(item.get("PhysicalMediaType", "")).strip()
        m_type = str(item.get("MediaType", "")).strip()
        mac = str(item.get("MacAddress", "")).strip()

        desc_lower = desc.lower()
        name_lower = name.lower()
        ptype_lower = p_type.lower()
        mtype_lower = m_type.lower()

        # Identify Wi-Fi
        is_wifi = (
            "802.11" in ptype_lower or
            "802.11" in mtype_lower or
            any(w in desc_lower for w in WIFI_KEYWORDS) or
            any(w in name_lower for w in WIFI_KEYWORDS)
        )

        # Identify Virtual
        is_virtual = (
            any(v in desc_lower for v in VIRTUAL_KEYWORDS) or
            any(v in name_lower for v in VIRTUAL_KEYWORDS)
        )

        # Determine physical Ethernet
        is_physical_ethernet = (
            not is_wifi and
            not is_virtual and
            (
                "802.3" in ptype_lower or
                "802.3" in mtype_lower or
                "ethernet" in desc_lower or
                "gbe" in desc_lower or
                "gigabit" in desc_lower or
                "controller" in desc_lower or
                "realtek" in desc_lower or
                "intel" in desc_lower or
                "broadcom" in desc_lower
            )
        )

        is_connected = (status.lower() == "up")

        adapter = AdapterInfo(
            name=name,
            interface_description=desc,
            interface_index=idx,
            mac_address=mac,
            status=status,
            link_speed=speed,
            physical_media_type=p_type,
            is_connected=is_connected,
            is_physical_ethernet=is_physical_ethernet,
            is_wifi=is_wifi,
            is_virtual=is_virtual
        )
        adapters.append(adapter)

    return adapters


def get_adapter_ip_config(interface_index: int) -> AdapterConfig:
    """
    Retrieve IPv4 address, subnet, DHCP state, default gateway, and DNS for an interface.
    """
    config = AdapterConfig()
    ps_cmd = (
        f"$idx = {interface_index}; "
        "$ip = Get-NetIPAddress -InterfaceIndex $idx -AddressFamily IPv4 -ErrorAction SilentlyContinue | Select-Object -First 1 IPAddress, PrefixLength; "
        "$intf = Get-NetIPInterface -InterfaceIndex $idx -AddressFamily IPv4 -ErrorAction SilentlyContinue | Select-Object Dhcp; "
        "$gw = (Get-NetRoute -InterfaceIndex $idx -DestinationPrefix '0.0.0.0/0' -ErrorAction SilentlyContinue | Select-Object -First 1).NextHop; "
        "$dns = (Get-DnsClientServerAddress -InterfaceIndex $idx -AddressFamily IPv4 -ErrorAction SilentlyContinue).ServerAddresses; "
        "[PSCustomObject]@{"
        "  IP = $ip.IPAddress; "
        "  Prefix = $ip.PrefixLength; "
        "  Dhcp = if ($intf.Dhcp -eq 1) { $true } else { $false }; "
        "  Gateway = $gw; "
        "  DNS = $dns "
        "} | ConvertTo-Json -Compress"
    )

    data = run_powershell_json(ps_cmd)
    if data and isinstance(data, dict):
        config.dhcp_enabled = bool(data.get("Dhcp", True))
        config.ipv4_address = data.get("IP")
        prefix = data.get("Prefix")
        if prefix is not None:
            config.prefix_length = int(prefix)
            config.subnet_mask = prefix_to_netmask(config.prefix_length)
        config.default_gateway = data.get("Gateway")
        dns_val = data.get("DNS")
        if isinstance(dns_val, list):
            config.dns_servers = [str(d) for d in dns_val if d]
        elif isinstance(dns_val, str) and dns_val.strip():
            config.dns_servers = [dns_val.strip()]

    return config


def prefix_to_netmask(prefix: int) -> str:
    """Convert IPv4 CIDR prefix (e.g. 24) to subnet mask (e.g. 255.255.255.0)."""
    mask = (0xffffffff >> (32 - prefix)) << (32 - prefix)
    return f"{(mask >> 24) & 0xff}.{(mask >> 16) & 0xff}.{(mask >> 8) & 0xff}.{mask & 0xff}"


def ipv4_addresses_on(adapter_name: str) -> List[str]:
    """IPv4 addresses currently assigned to one adapter, by its Windows name."""
    import psutil

    addresses = []
    for entry in psutil.net_if_addrs().get(adapter_name, []):
        if entry.family == socket.AF_INET and entry.address:
            addresses.append(entry.address)
    return addresses


def wait_for_ipv4(
    adapter_name: str,
    expected_ip: str,
    timeout: float = 3.0,
    interval: float = 0.1,
    read_addresses: Optional[Callable[[], List[str]]] = None,
) -> tuple[bool, List[str]]:
    """
    Poll until expected_ip is assigned to adapter_name.
    Returns as soon as it appears. After timeout, returns the last addresses seen.
    """
    reader = read_addresses or (lambda: ipv4_addresses_on(adapter_name))
    deadline = time.monotonic() + timeout
    found: List[str] = []
    while True:
        found = list(reader())
        if expected_ip in found:
            return True, found
        if time.monotonic() >= deadline:
            return False, found
        time.sleep(interval)


def interface_address_snapshot() -> List[tuple]:
    """(name, is_up, ipv4 addresses) for every interface psutil can see."""
    import psutil

    stats = psutil.net_if_stats()
    snapshot = []
    for name, entries in psutil.net_if_addrs().items():
        state = stats.get(name)
        is_up = True if state is None else bool(state.isup)
        ipv4 = [entry.address for entry in entries if entry.family == socket.AF_INET and entry.address]
        snapshot.append((name, is_up, ipv4))
    return snapshot


def find_subnet_conflict(target_ip: str, ignore_name: str) -> Optional[str]:
    """
    Name of another interface that is up and already uses target_ip or its /24.
    Disconnected adapters are ignored, matching the previous conflict rule.
    """
    return conflict_in_snapshot(target_ip, ignore_name, interface_address_snapshot())


def conflict_in_snapshot(target_ip: str, ignore_name: str, snapshot: List[tuple]) -> Optional[str]:
    prefix = ".".join(target_ip.split(".")[:3]) + "."
    for name, is_up, addresses in snapshot:
        if name == ignore_name or not is_up:
            continue
        for address in addresses:
            if address == target_ip or address.startswith(prefix):
                return name
    return None


def get_physical_ethernet_adapters() -> List[AdapterInfo]:
    """
    Get all physical Ethernet adapters, sorted with connected adapters first.
    """
    all_adapters = get_all_adapters()
    ethernet_adapters = [a for a in all_adapters if a.is_physical_ethernet]
    # Sort connected first
    ethernet_adapters.sort(key=lambda a: 0 if a.is_connected else 1)
    return ethernet_adapters
