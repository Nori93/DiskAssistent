#!/usr/bin/env python3
"""
run.py — convenience launcher for DiskAssistent.
Usage:  python run.py
"""

import subprocess
import sys


def main():
    subprocess.run(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "main:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
            "--reload",
        ],
        check=True,
    )


if __name__ == "__main__":
    main()
