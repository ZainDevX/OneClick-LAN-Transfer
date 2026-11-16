# OneClick LAN Transfer — Professional Windows 11 Desktop Application

**OneClick LAN Transfer** is a production-quality, offline Windows desktop application engineered for transferring large files (up to 100GB or more) directly between two Windows 10/11 computers using a single Ethernet Cat6 cable at full Gigabit line speeds (~110–125 MB/s).

The application completely eliminates Windows SMB username/password prompts and permission headaches through an independent, TLS-encrypted mutual challenge-response authentication engine. It also automates static IP assignment, Windows Firewall rules, and network restoration with zero manual networking knowledge required.

---

## Table of Contents
1. [Core Features & Architecture](#core-features--architecture)
2. [Quick Start Workflow](#quick-start-workflow)
3. [Host PC Usage Guide](#host-pc-usage-guide)
4. [Client PC Usage Guide](#client-pc-usage-guide)
5. [Network Automation & Security Architecture](#network-automation--security-architecture)
6. [Network Restoration & Safety](#network-restoration--safety)
7. [Troubleshooting Guide](#troubleshooting-guide)
8. [Automated Test Suite & Verification Report](#automated-test-suite--verification-report)
9. [Developer Build & Packaging Instructions](#developer-build--packaging-instructions)

---

## 1. Core Features & Architecture

- **One-Click Network Setup:**
  - Automatically identifies physical Ethernet network adapters while safely ignoring Wi-Fi, Hyper-V, WSL, VMware, and virtual interfaces.
  - Configures **Host PC** to static IP `192.168.50.1` (`255.255.255.0`).
  - Configures **Client PC** to static IP `192.168.50.2` (`255.255.255.0`).
  - Automatically applies Windows `Private` network category to allow local traffic.
- **Independent Application-Level Authentication:**
  - Avoids SMB login dialogs and requires **zero Windows usernames or passwords**.
  - Ephemeral TLS channel encryption (2048-bit RSA / TLS 1.2+).
  - Mutual HMAC-SHA256 challenge-response handshake using a 6-digit dynamic pairing code.
  - Negotiates cryptographic session tokens; rejects unauthorized connection attempts.
- **High-Performance Transfer Engine:**
  - Streams 100GB+ files (ISO, ZIP, EXE, VMDK, raw disk images, nested folders) in memory-efficient chunks (2MB default).
  - Saturates 1 Gbps / 2.5 Gbps Ethernet interfaces.
  - Resume capability: preserves partial `.oneclick.part` files; seamlessly resumes interrupted transfers from byte offset.
  - SHA-256 cryptographic verification: checks complete file hash before renaming `.oneclick.part` to final name.
- **Modern Windows 11 Fluent UI:**
  - Built with PySide6 (Qt6), featuring dark/light theme switching, cards, smooth progress bars, real-time speedometers (MB/s), and ETA indicators.
- **Non-Destructive Network Restoration:**
  - Takes a full snapshot of adapter settings (DHCP vs static, gateway, DNS) prior to changes.
  - Offers one-click restoration on exit or on-demand, reverting your network adapter to DHCP and deleting only application-created firewall rules.

---

## 2. Quick Start Workflow

```
[ HOST PC ]                                                     [ CLIENT PC ]
1. Connect Cat6 Ethernet Cable between both computers
2. Launch OneClickLAN.exe                                        2. Launch OneClickLAN.exe
3. Click "HOST MODE"                                            3. Click "CLIENT MODE"
4. Select Ethernet adapter -> "Start Host"                     4. Select Ethernet adapter -> "Configure Network"
5. View 6-Digit Pairing Code (e.g. 748-219)                     5. Enter Pairing Code -> "Connect & Authenticate"
6. Add Files or Folders to share                                6. Select files to transfer -> Click "Start Download"
   [ Transfer starts at full line speed (110-120 MB/s), verified with SHA-256 ]
```

---

## 3. Host PC Usage Guide

1. **Launch the Application:**
   Run `OneClickLAN.exe` (or run `python main.py`).
2. **Select HOST MODE:**
   On the main dashboard, click the blue **"Select HOST Mode"** button.
3. **Select Ethernet Adapter:**
   From the dropdown list, select your active physical Ethernet adapter (e.g., *Realtek PCIe GbE Family Controller*).
4. **Click "Start Host":**
   - The app will automatically configure the static IP `192.168.50.1` and open the inbound firewall rule on TCP port `52428`.
   - A 6-digit pairing code (e.g., `849-312`) is generated and displayed on screen.
5. **Select Files/Folders to Share:**
   - Click **"➕ Add Files..."** to share individual files (ISO, ZIP, EXE, MP4, etc.).
   - Click **"📁 Add Folder..."** to share complete folder hierarchies.
6. **Wait for Client:**
   When the Client PC connects, the status updates to `🟢 Client Connected`. You can monitor live transfer speed (MB/s), ETA, and progress bar in real time.
7. **Stopping Host Mode:**
   Click **"Stop Host Service"** or **"← Back to Menu"**. The app will automatically offer to restore your original DHCP settings.

---

## 4. Client PC Usage Guide

1. **Launch the Application:**
   Run `OneClickLAN.exe` on the receiving computer.
2. **Select CLIENT MODE:**
   On the dashboard, click the green **"Select CLIENT Mode"** button.
3. **Configure Network:**
   Select your physical Ethernet adapter and click **"Configure Network (192.168.50.2)"**.
4. **Connect to Host:**
   - Ensure the Host IP is set to `192.168.50.1` (prefilled).
   - Enter the 6-digit pairing code displayed on the Host PC screen.
   - Click **"Connect & Authenticate"**.
5. **Select Files & Destination:**
   - Available shared files from the Host appear in the table with file sizes. Check the boxes next to files you wish to download.
   - Verify the destination folder (default: `Downloads\OneClickLAN_Transfers`). The available free disk space is displayed automatically.
6. **Start Transfer:**
   Click **"▶️ Start Download"**. The transfer engine streams file chunks, tracking instantaneous speed and remaining time.
7. **Pause / Resume / Cancel:**
   You can pause the transfer anytime. If the cable is accidentally disconnected or the app is closed, simply reconnect and start again—OneClick LAN Transfer automatically detects partial `.part` files and resumes from the exact byte offset!

---

## 5. Network Automation & Security Architecture

### Zero SMB Exposure
Traditional Windows file sharing relies on SMBv2/v3, which requires Windows account credentials, complex sharing permissions, and often fails with "Access Denied" or network path errors. OneClick LAN Transfer operates entirely at the application layer:
1. **Transport Encryption:** TLS 1.2+ with ephemeral 2048-bit RSA keys negotiated for each session.
2. **Mutual HMAC-SHA256 Handshake:** The Host and Client issue random 32-byte cryptographic nonces. Both sides must independently prove possession of the temporary pairing code via HMAC-SHA256 before any data stream is permitted.
3. **No Credential Leakage:** No Windows usernames, hashes, or passwords are ever queried or transmitted.
4. **Isolated Firewall Rules:** Configures a single inbound rule strictly on TCP port `52428` scoped to the `Private` profile.

---

## 6. Network Restoration & Safety

OneClick LAN Transfer guarantees non-destructive networking:
- **Automatic Backup:** Before applying static IPs, the application queries Windows PowerShell and saves a snapshot containing:
  - Adapter name and MAC address
  - DHCP enabled state
  - Original static IP, prefix length, and subnet mask
  - Default gateway and DNS servers
  - Stored in `%LOCALAPPDATA%\OneClickLAN\backups\backup_<adapter>_<idx>.json`.
- **One-Click Restoration:**
  - On application exit: If `auto_restore_network` is enabled (default), settings revert immediately.
  - Manual button: Click **"🔄 Restore Original Network Settings"** on the Dashboard or Settings page.
  - Firewall cleanup: Deletes only the `OneClickLAN_Direct_Transfer` firewall rule.

---

## 7. Troubleshooting Guide

Every error in OneClick LAN Transfer includes: What happened, Why it may have happened, and How to fix it.

| Error Code | Error Title | What Happened & Root Cause | Exact User Fix |
|---|---|---|---|
| `CABLE_DISCONNECTED` | Ethernet Cable Disconnected | Physical link is down; adapter status is Disconnected. | Plug Cat6 cable firmly into both computers; check link LED lights. |
| `NO_ETHERNET_ADAPTER` | No Ethernet Adapter Found | No active physical Ethernet controller was detected. | Plug in USB-to-Ethernet adapter or enable NIC in Device Manager. |
| `MULTIPLE_ETHERNET_ADAPTERS` | Multiple Adapters Detected | System has onboard LAN plus USB adapter or dock. | Select the adapter connected to the Cat6 cable from dropdown. |
| `IP_CONFLICT` | Subnet Conflict Detected | Another interface is already using `192.168.50.x`. | Disable conflicting VPN or change port/subnet in Settings. |
| `STATIC_IP_FAILED` | Static IP Configuration Failed | Windows Netsh / PowerShell permission denied. | Run application as Administrator via UAC prompt. |
| `HOST_UNREACHABLE` | Host Unreachable | Client cannot ping or reach TCP socket on 192.168.50.1. | Ensure Host is running and "Start Host" was clicked. |
| `FIREWALL_BLOCKED` | Windows Firewall Blocked | Windows Firewall dropped incoming packets. | Allow app in Firewall or click "Allow Port in Firewall" in Settings. |
| `AUTH_FAILED` | Authentication Failed | HMAC verification failed due to pairing code mismatch. | Re-enter the exact 6-digit code shown on the Host screen. |
| `INVALID_PAIRING_CODE` | Invalid Pairing Code | Entered code is empty or improperly formatted. | Enter the 6 digits displayed on the Host PC. |
| `TLS_FAILED` | TLS Handshake Failed | SSL/TLS protocol error or socket dropped during handshake. | Restart Host service; check third-party antivirus SSL scanning. |
| `INSUFFICIENT_DISK_SPACE`| Insufficient Disk Space | Destination drive has less free space than incoming batch. | Select a destination folder on a drive with adequate storage. |
| `FILE_ACCESS_DENIED` | File Access Denied | Source file is locked by another program or permission denied.| Close open applications (e.g. ISO mounters) holding file lock. |
| `TRANSFER_INTERRUPTED` | Transfer Interrupted | Cable disconnected or socket reset during stream. | Reconnect cable and click "Resume Transfer". |
| `HASH_MISMATCH` | SHA-256 Verification Failed | Received file checksum does not match source file. | App automatically retains `.part`; click retry to re-stream corrupted slice. |
| `PORT_IN_USE` | Port Already in Use | Port 52428 is bound by another instance. | Close duplicate instances in Task Manager or change port in Settings. |

---

## 8. Automated Test Suite & Verification Report

The application includes automated unit and integration tests located in `tests/`:

```bash
python -m unittest discover tests
```

### Execution Results:
```
Ran 13 tests in 12.252s
OK
```

- `test_authentication.py`:
  - `test_pairing_code_format`: PASS
  - `test_ephemeral_cert_generation`: PASS
  - `test_mutual_auth_success`: PASS (end-to-end TLS + HMAC verification)
  - `test_mutual_auth_failure_wrong_code`: PASS (immediate rejection of invalid codes)
- `test_integrity.py`:
  - `test_compute_sha256`: PASS (10MB block hashing)
  - `test_verify_integrity_success`: PASS
  - `test_verify_integrity_failure_corrupted`: PASS
  - `test_offset_hashing`: PASS (slice hashing for resume verification)
- `test_transfer.py`:
  - `test_complete_file_transfer`: PASS (15MB binary streaming over TLS socket + SHA-256 check)
  - `test_transfer_resume_from_part`: PASS (offset resume from existing `.part` file)
- `test_network.py`:
  - `test_prefix_to_netmask`: PASS
  - `test_adapter_detection_runnable`: PASS (verifies Windows physical NIC detection & filtering)
  - `test_backup_and_restore_file_creation`: PASS (verifies JSON snapshot format)

---

## 9. Developer Build & Packaging Instructions

### Prerequisites (Developer Machine Only)
- Windows 10 or 11 (64-bit)
- Python 3.10+ (Tested on Python 3.14)
- `pip install -r requirements.txt`

### Automated Build Script
Double-click `build.bat` or run in terminal:
```cmd
build.bat
```

### Manual PyInstaller Build
```cmd
pyinstaller --clean OneClickLAN.spec
```

### Output
The standalone distribution is produced at:
```
dist\OneClickLAN\OneClickLAN.exe
```

> **Note for End Users:**
> The entire `dist\OneClickLAN` directory is fully portable and self-contained. End users **do not need Python, pip, PySide6, or any runtime dependencies installed**. Simply copy the folder or ZIP archive to any Windows 10 or Windows 11 machine and run `OneClickLAN.exe`.
