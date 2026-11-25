"""
Permissions and one-shot Windows UAC elevation.

The GUI stays a standard user. When a network action needs administrator
rights, this module launches the same program once with --elevated-helper.
That process runs the whole command list, records every exit code, and exits.
The user sees one consent dialog per action, not one dialog per netsh call.
"""

import sys
import os
import json
import uuid
import ctypes
import logging
import subprocess
from ctypes import wintypes
from dataclasses import dataclass, field, asdict
from pathlib import Path
logger = logging.getLogger("OneClickLAN.Permissions")

HELPER_FLAG = "--elevated-helper"
SEE_MASK_NOCLOSEPROCESS = 0x00000040
SW_HIDE = 0
ERROR_CANCELLED = 1223
WAIT_TIMEOUT = 0x00000102
INFINITE = 0xFFFFFFFF
# The helper is only a netsh/profile runner. Anything else is refused.
_COMMAND_TIMEOUT_SECONDS = 30


@dataclass
class PrivilegedCommand:
    command: str
    required: bool = True
    label: str = ""


@dataclass
class CommandResult:
    label: str
    command: str
    returncode: int
    stdout: str
    stderr: str
    ok: bool
    required: bool


@dataclass
class BatchResult:
    results: list[CommandResult] = field(default_factory=list)
    cancelled: bool = False
    launch_error: str = ""

    @property
    def required_ok(self) -> bool:
        if self.cancelled or self.launch_error:
            return False
        required = [item for item in self.results if item.required]
        return bool(required) and all(item.ok for item in required)


def get_hidden_subprocess_kwargs() -> dict:
    """Subprocess kwargs that keep a console window from flashing on Windows."""
    kwargs = {}
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        kwargs["startupinfo"] = startupinfo
    return kwargs


def is_admin() -> bool:
    """True when this process already has a Windows administrator token."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception as exc:
        logger.warning(f"Failed to check admin status: {exc}")
        return False


def adapter_name_is_safe(name: str) -> bool:
    """Reject adapter names that would break or escape a shell command."""
    if not name or not name.strip():
        return False
    forbidden = set('"&|<>\n\r`$')
    return not any(char in forbidden for char in name)


def command_is_allowed(command: str) -> bool:
    """
    Allow only the network commands this application generates.
    The elevated helper must not become a general administrator shell.
    """
    text = (command or "").strip()
    lowered = text.lower()
    if not text or any(char in text for char in "\r\n&|<>`"):
        return False
    if lowered.startswith("netsh interface ipv4 "):
        return True
    if lowered.startswith("netsh advfirewall firewall "):
        return True
    if lowered.startswith("powershell -noprofile -command "):
        if "set-netconnectionprofile" not in lowered:
            return False
        if any(token in text for token in (";", "$(")):
            return False
        return True
    return False


def run_command_capturing(command: str, label: str = "", required: bool = True, timeout: float = _COMMAND_TIMEOUT_SECONDS) -> CommandResult:
    """Run one command in this process and keep its real exit code and output."""
    try:
        completed = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
            **get_hidden_subprocess_kwargs(),
        )
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        return CommandResult(
            label=label,
            command=command,
            returncode=completed.returncode,
            stdout=stdout,
            stderr=stderr,
            ok=completed.returncode == 0,
            required=required,
        )
    except subprocess.TimeoutExpired as exc:
        return CommandResult(
            label=label,
            command=command,
            returncode=-1,
            stdout=exc.stdout or "" if isinstance(exc.stdout, str) else "",
            stderr=f"Command timed out after {timeout:.0f}s.",
            ok=False,
            required=required,
        )
    except Exception as exc:
        return CommandResult(
            label=label,
            command=command,
            returncode=-1,
            stdout="",
            stderr=str(exc),
            ok=False,
            required=required,
        )


def execute_commands(commands: list[PrivilegedCommand]) -> list[CommandResult]:
    """Run commands in order. Stop after the first required command fails."""
    results: list[CommandResult] = []
    for command in commands:
        if not command_is_allowed(command.command):
            results.append(CommandResult(
                label=command.label,
                command=command.command,
                returncode=-1,
                stdout="",
                stderr="Command is not allowed.",
                ok=False,
                required=command.required,
            ))
            if command.required:
                break
            continue
        result = run_command_capturing(command.command, command.label, command.required)
        results.append(result)
        logger.info(
            "Privileged command %s finished with exit %s",
            command.label or command.command,
            result.returncode,
        )
        if result.stderr.strip():
            logger.info("stderr: %s", result.stderr.strip())
        if command.required and not result.ok:
            break
    return results


def run_privileged_commands(commands: list[PrivilegedCommand]) -> BatchResult:
    """
    Run commands here when this process is already admin.
    Otherwise elevate this same program once and wait for its report.
    """
    if not commands:
        return BatchResult(launch_error="No commands to run.")
    for command in commands:
        if not command_is_allowed(command.command):
            return BatchResult(launch_error=f"Refused an unsafe command ({command.label or 'command'}).")
    if is_admin():
        return BatchResult(results=execute_commands(commands))
    return _launch_elevated_helper(commands)


def run_elevated_command(command: str) -> tuple[bool, str]:
    """
    One privileged command. Success is the command's own exit code.
    Output is stdout, or stderr when stdout is empty.
    """
    batch = run_privileged_commands([PrivilegedCommand(command=command, required=True, label="command")])
    if batch.cancelled:
        return False, "Administrator permission was cancelled."
    if batch.launch_error:
        return False, batch.launch_error
    if not batch.results:
        return False, "The elevated command did not return a result."
    result = batch.results[0]
    output = (result.stdout or result.stderr).strip()
    if result.ok:
        return True, output
    return False, output or f"Command failed with exit code {result.returncode}."


def elevated_helper_main(argv: list[str]) -> int:
    """
    Entry point for the elevated process. No window is created.
    argv is the full sys.argv list.
    """
    try:
        flag_index = argv.index(HELPER_FLAG)
        job_path = Path(argv[flag_index + 1])
        result_path = Path(argv[flag_index + 2])
    except (ValueError, IndexError):
        return 2

    try:
        if not is_admin():
            _write_result(result_path, [], "The helper process is not running as administrator.")
            return 1
        payload = json.loads(job_path.read_text(encoding="utf-8"))
        commands = [
            PrivilegedCommand(
                command=item["command"],
                required=bool(item.get("required", True)),
                label=str(item.get("label", "")),
            )
            for item in payload.get("commands", [])
        ]
        for command in commands:
            if not command_is_allowed(command.command):
                _write_result(result_path, [], f"Refused an unsafe command ({command.label or 'command'}).")
                return 1
        results = execute_commands(commands)
        _write_result(result_path, results, "")
        return 0
    except Exception as exc:
        try:
            _write_result(result_path, [], str(exc))
        except Exception:
            pass
        return 1


def _launch_elevated_helper(commands: list[PrivilegedCommand]) -> BatchResult:
    job_dir = Path(os.environ.get("TEMP", ".")) / "OneClickLAN" / "jobs"
    job_dir.mkdir(parents=True, exist_ok=True)
    token = uuid.uuid4().hex
    job_path = job_dir / f"{token}.json"
    result_path = job_dir / f"{token}.result.json"
    payload = {
        "commands": [asdict(command) for command in commands],
    }
    job_path.write_text(json.dumps(payload), encoding="utf-8")
    try:
        launched = _shell_execute_helper(job_path, result_path)
        if launched.cancelled or launched.launch_error:
            return launched
        if not result_path.exists():
            return BatchResult(launch_error="The elevated helper finished without a result file.")
        data = json.loads(result_path.read_text(encoding="utf-8"))
        if data.get("error"):
            return BatchResult(launch_error=str(data["error"]))
        results = [
            CommandResult(
                label=item.get("label", ""),
                command=item.get("command", ""),
                returncode=int(item.get("returncode", -1)),
                stdout=item.get("stdout", ""),
                stderr=item.get("stderr", ""),
                ok=bool(item.get("ok", False)),
                required=bool(item.get("required", True)),
            )
            for item in data.get("results", [])
        ]
        return BatchResult(results=results)
    finally:
        for path in (job_path, result_path):
            try:
                path.unlink(missing_ok=True)
            except Exception:
                pass


def _shell_execute_helper(job_path: Path, result_path: Path) -> BatchResult:
    executable, parameters = _helper_target(job_path, result_path)
    workdir = str(Path(executable).resolve().parent) if getattr(sys, "frozen", False) else str(Path(sys.argv[0]).resolve().parent)

    class ShellExecuteInfo(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("fMask", wintypes.ULONG),
            ("hwnd", wintypes.HWND),
            ("lpVerb", wintypes.LPCWSTR),
            ("lpFile", wintypes.LPCWSTR),
            ("lpParameters", wintypes.LPCWSTR),
            ("lpDirectory", wintypes.LPCWSTR),
            ("nShow", ctypes.c_int),
            ("hInstApp", wintypes.HINSTANCE),
            ("lpIDList", ctypes.c_void_p),
            ("lpClass", wintypes.LPCWSTR),
            ("hkeyClass", wintypes.HKEY),
            ("dwHotKey", wintypes.DWORD),
            ("hMonitor", wintypes.HANDLE),
            ("hProcess", wintypes.HANDLE),
        ]

    shell32 = ctypes.WinDLL("shell32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    shell_execute = shell32.ShellExecuteExW
    shell_execute.argtypes = [ctypes.POINTER(ShellExecuteInfo)]
    shell_execute.restype = wintypes.BOOL

    info = ShellExecuteInfo()
    info.cbSize = ctypes.sizeof(ShellExecuteInfo)
    info.fMask = SEE_MASK_NOCLOSEPROCESS
    info.lpVerb = "runas"
    info.lpFile = executable
    info.lpParameters = parameters
    info.lpDirectory = workdir
    info.nShow = SW_HIDE

    logger.info("Requesting one elevation for the network helper.")
    if not shell_execute(ctypes.byref(info)):
        error_code = ctypes.get_last_error()
        if error_code == ERROR_CANCELLED:
            return BatchResult(cancelled=True)
        return BatchResult(launch_error=f"Windows could not start the elevated helper (error {error_code}).")

    try:
        wait_result = kernel32.WaitForSingleObject(info.hProcess, INFINITE)
        if wait_result == WAIT_TIMEOUT:
            return BatchResult(launch_error="The elevated helper timed out.")
    finally:
        if info.hProcess:
            kernel32.CloseHandle(info.hProcess)
    return BatchResult()


def _helper_target(job_path: Path, result_path: Path) -> tuple[str, str]:
    arguments = f'{HELPER_FLAG} "{job_path}" "{result_path}"'
    if getattr(sys, "frozen", False):
        return sys.executable, arguments
    script = str(Path(sys.argv[0]).resolve())
    return sys.executable, f'"{script}" {arguments}'


def _write_result(result_path: Path, results: list[CommandResult], error: str) -> None:
    payload = {
        "results": [asdict(item) for item in results],
        "error": error,
    }
    result_path.write_text(json.dumps(payload), encoding="utf-8")
