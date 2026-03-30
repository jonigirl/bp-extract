#!/usr/bin/env python3
"""
BP Extract Web Interface Launcher

This script launches the Flask application and opens it in the default browser.
Works on Windows, macOS, and Linux.
"""

import os
import subprocess
import sys
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


def activate_virtual_env(venv_path):
    """Print instructions for activating virtual environment."""
    if sys.platform == "win32":
        activate_script = str(venv_path / "Scripts" / "activate.bat")
        print(f"To manually activate: {activate_script}")
    else:
        activate_script = str(venv_path / "bin" / "activate")
        print(f"To manually activate: source {activate_script}")


def check_and_install_flask():
    """Check if Flask is installed, install if necessary."""
    try:
        import flask

        print(f"✓ Flask is installed (version {flask.__version__})")
        return True
    except ImportError:
        print("Flask not found. Attempting to install...")
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "Flask"],
                stdout=subprocess.DEVNULL,
            )
            print("✓ Flask installed successfully")
            return True
        except subprocess.CalledProcessError:
            print("✗ Failed to install Flask")
            print("  Try running manually: pip install Flask")
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


def main():
    """Main launcher function."""
    print("\n" + "=" * 60)
    print("BP Extract - Blueprint Tracker Web Interface")
    print("=" * 60 + "\n")

    # Check Python version
    print("Checking Python version...")
    check_python_version()
    print(f"✓ Python {sys.version.split()[0]} is compatible\n")

    # Check for virtual environment
    print("Checking for virtual environment...")
    venv = find_virtual_env()
    if venv:
        print(f"✓ Found virtual environment: {venv}\n")
    else:
        print("  No virtual environment found (this is optional)\n")

    # Check and install Flask
    print("Checking Flask installation...")
    if not check_and_install_flask():
        sys.exit(1)

    # Find a free port
    print("\nFinding available port...")
    port = find_free_port()
    if not port:
        print("✗ Could not find an available port")
        sys.exit(1)
    print(f"✓ Using port {port}\n")

    # Prepare to launch
    url = f"http://127.0.0.1:{port}"
    print("=" * 60)
    print("Starting BP Extract...")
    print(f"Access the application at: {url}")
    print("Press Ctrl+C to stop the application")
    print("=" * 60 + "\n")

    # Give user a moment to read the message
    time.sleep(1)

    # Open browser
    try:
        webbrowser.open(url)
        print(f"✓ Opened {url} in your default browser\n")
    except Exception as e:
        print(f"! Could not open browser automatically: {e}")
        print(f"  Please open {url} manually in your browser\n")

    # Launch Flask app
    try:
        if sys.platform == "win32":
            # Windows: use shell=True for better process handling
            os.environ["FLASK_ENV"] = "production"
            subprocess.run(
                [sys.executable, "app.py"],
                cwd=Path(__file__).parent,
            )
        else:
            # Unix-like systems
            os.environ["FLASK_ENV"] = "production"
            subprocess.run(
                [sys.executable, "app.py"],
                cwd=Path(__file__).parent,
            )
    except KeyboardInterrupt:
        print("\n\nShutting down BP Extract...")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Error running application: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure you're in the BP Extract directory")
        print("2. Check that app.py exists in this directory")
        print("3. Try running manually: python app.py")
        sys.exit(1)


if __name__ == "__main__":
    main()
