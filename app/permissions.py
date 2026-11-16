"""
Permissions and Windows UAC Elevation Management
Provides checks for Administrator privileges and safe UAC elevation helpers.
Guarantees completely silent, non-flashing subprocess execution on Windows.
"""

import sys
import os
import ctypes
import subprocess
import logging

logger = logging.getLogger("OneClickLAN.Permissions")

def get_hidden_subprocess_kwargs() -> dict:
    """
    Returns subprocess kwargs to completely suppress any console / terminal window
    from flashing on Windows.
    """
    kwargs = {}
    if os.name == 'nt':
        # CREATE_NO_WINDOW prevents creation of a new console window
        kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        kwargs['startupinfo'] = startupinfo
    return kwargs

def is_admin() -> bool:
    """
    Check if the current process has Windows Administrator privileges.
    """
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception as e:
        logger.warning(f"Failed to check admin status: {e}")
        return False

def request_uac_elevation(args: list = None) -> bool:
    """
    Request UAC elevation to restart the current script/executable with admin rights.
    Returns True if ShellExecute was successfully dispatched.
    """
    if is_admin():
        return True

    if args is None:
        args = sys.argv[1:]

    # Parameters to pass to elevated process
    params = " ".join([f'"{arg}"' for arg in args])

    try:
        if getattr(sys, 'frozen', False):
            # Running as compiled PyInstaller executable
            executable = sys.executable
        else:
            # Running as Python script
            executable = sys.executable
            params = f'"{sys.argv[0]}" {params}'.strip()

        logger.info(f"Relaunching elevated: {executable} {params}")
        ret = ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            executable,
            params,
            None,
            1  # SW_SHOWNORMAL
        )
        if ret > 32:
            return True
        else:
            logger.error(f"ShellExecute failed with return code: {ret}")
            return False
    except Exception as e:
        logger.error(f"Elevation request failed: {e}")
        return False

def run_elevated_command(command: str) -> tuple[bool, str]:
    """
    Execute a command requiring elevation without popping up console windows.
    If already admin, runs directly via subprocess with CREATE_NO_WINDOW.
    If not, executes via powershell Start-Process -Verb RunAs -WindowStyle Hidden.
    Returns (success, output_or_error).
    """
    hidden_kwargs = get_hidden_subprocess_kwargs()

    if is_admin():
        try:
            res = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                check=False,
                **hidden_kwargs
            )
            return res.returncode == 0, res.stdout or res.stderr
        except Exception as e:
            return False, str(e)
    else:
        # Run elevated via hidden PowerShell
        escaped_cmd = command.replace('"', '`"')
        ps_script = f'Start-Process powershell -WindowStyle Hidden -ArgumentList \'-NoProfile -Command "{escaped_cmd}"\' -Verb RunAs -Wait'
        try:
            res = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden", "-Command", ps_script],
                capture_output=True,
                text=True,
                check=False,
                **hidden_kwargs
            )
            return res.returncode == 0, res.stdout or res.stderr
        except Exception as e:
            return False, str(e)
