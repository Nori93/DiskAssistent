"""
DiskAssistent Host Agent — configuration.
Reads from environment variables so it can run as a Windows Service
or Linux systemd unit with different settings per machine.
"""

from __future__ import annotations

import logging
import os
import platform

IS_WINDOWS = platform.system() == "Windows"
IS_LINUX = platform.system() == "Linux"

# Bind address — 0.0.0.0 so containers on the same host can reach it.
# Change to 127.0.0.1 if you want local-only access.
APP_HOST = os.getenv("HOST_AGENT_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("HOST_AGENT_PORT", "8003"))

# Optional shared secret.  When set every request must include:
#   Authorization: Bearer <HOST_AGENT_SECRET>
# Use a long random string in production:  python -c "import secrets; print(secrets.token_hex(32))"
AGENT_SECRET = os.getenv("HOST_AGENT_SECRET", "")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("host-agent")
