#!/usr/bin/env python3
"""
BP Extract Web Interface Launcher

This script launches the Flask application and opens it in the default browser.
Works on Windows, macOS, and Linux.
"""

import multiprocessing
import os
import sys
import threading
import time
import webbrowser
from pathlib import Path


def check_python_version():
    """Ensure Python 3.12+ is being used."""
    if sys.version_info < (3, 12):
        print(f"Error: Python 3.12+ required. You have {sys.version}")
        sys.exit(1)


def find_virtual_env():
    """Try to find and return the path to a virtual environment."""
    venv_paths = [".venv", "venv", "env"]
    for path in venv_paths:
        if Path(path).exists():
            return Path(path)
    return None


def check_flask_installed():
    """Check if Flask is installed."""
    if getattr(sys, "frozen", False):
        return True
    try:
        from importlib.metadata import PackageNotFoundError, version

        ver = version("flask")
        print(f"✓ Flask is installed (version {ver})")
        return True
    except PackageNotFoundError:
        print("✗ Flask not found.")
        print("  Install dependencies first: uv sync  (or: pip install flask)")
        return False


def find_free_port(host="127.0.0.1", start_port=5000):
    """Find a free port to run the server on."""
    import socket

    for port in range(start_port, start_port + 100):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()
            if result != 0:
                return port
        except socket.error:
            pass
    return None


def get_base_dir() -> Path:
    """Return base directory — sys._MEIPASS when frozen, else script dir."""
    import sys

    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).parent


def wait_for_port(host: str, port: int, timeout: float = 10.0) -> bool:
    """Wait until the given port is accepting connections. Returns True if ready."""
    import socket

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.1):
                return True
        except (ConnectionRefusedError, OSError):
            time.sleep(0.1)
    return False


def _run_flask(port: int) -> None:
    """Import and run the Flask app in-process."""
    from app import run_server

    run_server(port)


def main():
    print("\n" + "=" * 60)
    print("BP Extract - Blueprint Tracker Web Interface")
    print("=" * 60 + "\n")

    check_python_version()
    print(f"✓ Python {sys.version.split()[0]} is compatible\n")

    venv = find_virtual_env()
    if venv:
        print(f"✓ Found virtual environment: {venv}\n")
    else:
        print("  No virtual environment found (this is optional)\n")

    if not check_flask_installed():
        sys.exit(1)

    port = find_free_port()
    if not port:
        print("✗ Could not find an available port")
        sys.exit(1)
    print(f"✓ Using port {port}\n")

    url = f"http://127.0.0.1:{port}"
    print("=" * 60)
    print("Starting BP Extract...")
    print(f"Access the application at: {url}")
    print("Press Ctrl+C to stop")
    print("=" * 60 + "\n")

    # Start Flask in a daemon thread
    os.environ["BP_EXTRACT_PORT"] = str(port)
    flask_thread = threading.Thread(target=_run_flask, args=(port,), daemon=True)
    flask_thread.start()

    # Wait for Flask to be ready before opening the browser
    if not wait_for_port("127.0.0.1", port):
        print("✗ Server did not start in time")
        sys.exit(1)

    try:
        webbrowser.open(url)
        print(f"✓ Opened {url} in your default browser\n")
    except Exception as e:
        print(f"! Could not open browser: {e}")
        print(f"  Open {url} manually\n")

    # Watchdog loop — main thread polls the heartbeat flag so os._exit fires
    # reliably rather than from a daemon thread nested inside another daemon.
    import app as _app_module

    _watchdog_timeout = 20.0
    _watchdog_poll = 5.0
    try:
        while flask_thread.is_alive():
            time.sleep(_watchdog_poll)
            with _app_module._heartbeat_lock:
                hb = _app_module._last_heartbeat
            if hb is None:
                continue
            if time.time() - hb > _watchdog_timeout:
                print("\nNo browser heartbeat — shutting down.")
                sys.stdout.flush()
                os._exit(0)
    except KeyboardInterrupt:
        print("\n\nShutting down BP Extract...")
        sys.exit(0)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
