"""
Install DiskAssistent Host Agent as a native OS service.

Windows  — registers a Windows Service via pywin32.
Linux    — writes a systemd unit file to /etc/systemd/system/ and enables it.

Usage:
    python install_service.py install    # install & start
    python install_service.py remove     # stop & remove
    python install_service.py status     # show current status
"""

from __future__ import annotations

import os
import platform
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
PYTHON = sys.executable
SERVICE_NAME = "DiskAssistentHostAgent"
SERVICE_DISPLAY = "DiskAssistent Host Agent"
SERVICE_DESC = "Filesystem API for DiskAssistent containers"
UNIT_NAME = "diskassistent-agent.service"
UNIT_PATH = Path(f"/etc/systemd/system/{UNIT_NAME}")


# ── Entry point ───────────────────────────────────────────────────────────────


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("install", "remove", "status"):
        print("Usage: python install_service.py [install|remove|status]")
        sys.exit(1)

    cmd = sys.argv[1]
    if platform.system() == "Windows":
        _windows(cmd)
    else:
        _linux(cmd)


# ── Windows ───────────────────────────────────────────────────────────────────


def _windows(cmd: str):
    try:
        import win32service  # noqa: F401
        import win32serviceutil  # noqa: F401
    except ImportError:
        print("ERROR: pywin32 required.  Run:  pip install pywin32")
        sys.exit(1)

    import win32service
    import win32serviceutil

    if cmd == "status":
        try:
            status = win32serviceutil.QueryServiceStatus(SERVICE_NAME)
            state = {1: "stopped", 4: "running"}.get(status[1], str(status[1]))
            print(f"{SERVICE_NAME}: {state}")
        except Exception as exc:
            print(f"Not installed or error: {exc}")
        return

    if cmd == "install":
        try:
            win32serviceutil.InstallService(
                pythonClassString=None,
                serviceName=SERVICE_NAME,
                displayName=SERVICE_DISPLAY,
                description=SERVICE_DESC,
                startType=win32service.SERVICE_AUTO_START,
                exeName=PYTHON,
                exeArgs=f'"{SCRIPT_DIR / "main.py"}"',
            )
            win32serviceutil.StartService(SERVICE_NAME)
            print(f"Service '{SERVICE_NAME}' installed and started.")
            print("Tip: set HOST_AGENT_SECRET in the service environment for security.")
        except Exception as exc:
            print(f"Install failed: {exc}")
            sys.exit(1)
        return

    if cmd == "remove":
        try:
            win32serviceutil.StopService(SERVICE_NAME)
        except Exception:
            pass
        try:
            win32serviceutil.RemoveService(SERVICE_NAME)
            print(f"Service '{SERVICE_NAME}' removed.")
        except Exception as exc:
            print(f"Remove failed: {exc}")
            sys.exit(1)


# ── Linux (systemd) ───────────────────────────────────────────────────────────


def _linux(cmd: str):
    if cmd == "status":
        subprocess.run(["systemctl", "status", UNIT_NAME], check=False)  # noqa: S603, S607
        return

    if cmd == "remove":
        subprocess.run(["systemctl", "stop", UNIT_NAME], check=False)  # noqa: S603, S607
        subprocess.run(["systemctl", "disable", UNIT_NAME], check=False)  # noqa: S603, S607
        if UNIT_PATH.exists():
            UNIT_PATH.unlink()
        subprocess.run(["systemctl", "daemon-reload"], check=False)  # noqa: S603, S607
        print(f"Service '{UNIT_NAME}' removed.")
        return

    if cmd == "install":
        user = os.getenv("USER", "root")
        secret = os.getenv("HOST_AGENT_SECRET", "CHANGE_ME_" + os.urandom(8).hex())
        unit = f"""[Unit]
Description={SERVICE_DESC}
After=network.target

[Service]
Type=simple
User={user}
WorkingDirectory={SCRIPT_DIR}
ExecStart={PYTHON} {SCRIPT_DIR}/main.py
Restart=on-failure
RestartSec=5
Environment=HOST_AGENT_HOST=0.0.0.0
Environment=HOST_AGENT_PORT=8003
Environment=HOST_AGENT_SECRET={secret}

[Install]
WantedBy=multi-user.target
"""
        try:
            UNIT_PATH.write_text(unit)
            subprocess.run(["systemctl", "daemon-reload"], check=True)  # noqa: S603, S607
            subprocess.run(["systemctl", "enable", UNIT_NAME], check=True)  # noqa: S603, S607
            subprocess.run(["systemctl", "start", UNIT_NAME], check=True)  # noqa: S603, S607
            print(f"Service '{UNIT_NAME}' installed and started.")
            print(f"\nAuto-generated secret: {secret}")
            print("Set HOST_AGENT_SECRET in the unit file and in your podman-compose.yml.")
        except PermissionError:
            print("ERROR: run with sudo to install a systemd service.")
            sys.exit(1)
        except Exception as exc:
            print(f"Install failed: {exc}")
            sys.exit(1)


if __name__ == "__main__":
    main()
