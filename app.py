"""Flask web application for BP Extract."""

import csv
import logging
import os
import threading
import time
from datetime import datetime
from io import StringIO
from pathlib import Path

from flask import Flask, abort, jsonify, redirect, render_template, request, url_for

from config import get_config, get_or_create_secret_key
from core import (
    get_blueprints_from_json,
    load_existing_blueprints,
    scan_backups,
    tail_log,
)

APP_VERSION = "0.4.7"


def get_base_dir() -> Path:
    """Return the base directory for templates and static files.

    When frozen by PyInstaller, files are extracted to sys._MEIPASS.
    In normal operation, use the directory containing this file.
    """
    import sys

    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).parent


_base = get_base_dir()
app = Flask(
    __name__,
    template_folder=str(_base / "templates"),
    static_folder=str(_base / "static"),
)
_secret_key_env = os.environ.get("SECRET_KEY")
app.secret_key = (
    _secret_key_env.encode() if _secret_key_env else get_or_create_secret_key()
)
logger = logging.getLogger(__name__)

# Configuration from config system
config = None
LOG_FILE = None
DATA_FILE = None
BACKUP_DIR = None
POLL_INTERVAL = None
WAIT_INTERVAL = None


def initialize():
    """Initialize configuration on app startup."""
    global config, LOG_FILE, DATA_FILE, BACKUP_DIR, POLL_INTERVAL, WAIT_INTERVAL

    if LOG_FILE is not None:
        # Already initialized
        return

    config = get_config()

    LOG_FILE = config.get("log_file")
    DATA_FILE = config.get("data_file")
    BACKUP_DIR = config.get("backup_dir")
    POLL_INTERVAL = config.get("poll_interval", 0.5)
    WAIT_INTERVAL = config.get("wait_interval", 1.0)


def _require_xhr():
    """Abort with 403 if the request was not sent as an XMLHttpRequest.

    This is a lightweight CSRF mitigation for same-origin API endpoints.
    All legitimate callers (the built-in dashboard JS) send this header.
    Cross-site form submissions and most CSRF attack vectors cannot set it.
    """
    if request.headers.get("X-Requested-With") != "XMLHttpRequest":
        abort(403)


# Initialize on import
try:
    initialize()
except Exception as e:
    logging.warning("Startup initialization failed: %s", e)

# Global state
monitoring_thread = None
_stop_event = None
_pause_event = threading.Event()  # set() = monitoring paused
_scanning_event = threading.Event()  # set() = backup scan in progress
last_updated = None
lock = threading.Lock()

# Heartbeat tracking for browser-close detection
_last_heartbeat = None
_heartbeat_lock = threading.Lock()

# Scan progress tracking
_scan_status = {"current": 0, "total": 0, "found_new": 0}


def start_monitoring():
    """Start background monitoring thread."""
    global monitoring_thread, _stop_event

    _stop_event = threading.Event()
    stop_event = _stop_event  # captured by closure

    # Snapshot file paths at start time so the thread isn't affected by
    # later changes to the module-level globals (e.g. during tests).
    data_file = DATA_FILE
    log_file = LOG_FILE

    if not isinstance(data_file, (str, os.PathLike)) or not isinstance(
        log_file, (str, os.PathLike)
    ):
        logger.warning(
            "start_monitoring skipped: LOG_FILE or DATA_FILE is not a valid path"
        )
        return None

    def on_new():
        global last_updated
        with lock:
            last_updated = datetime.now().isoformat()

    def monitor():
        known_blueprints = load_existing_blueprints(data_file)
        tail_log(
            log_file,
            data_file,
            poll_interval=POLL_INTERVAL,
            wait_interval=WAIT_INTERVAL,
            known_blueprints=known_blueprints,
            should_pause_fn=_pause_event.is_set,
            stop_event=stop_event,
            on_new_blueprint=on_new,
        )

    monitoring_thread = threading.Thread(target=monitor, daemon=True)
    monitoring_thread.start()
    return monitoring_thread


@app.before_request
def check_initialized():
    """Return 503 if the app failed to initialize."""
    if DATA_FILE is None and request.endpoint not in (
        "index",
        "setup",
        "setup_post",
        "static",
        None,
    ):
        return jsonify(
            {"error": "Configuration not loaded. Check the console for errors."}
        ), 503


@app.route("/")
def index():
    """Serve the main dashboard."""
    if config and config.is_first_run():
        return redirect(url_for("setup"))
    return render_template("index.html", version=APP_VERSION)


# setup.html is rendered by this route — created separately
@app.route("/setup")
def setup():
    """Serve the first-run setup wizard."""
    if config and not config.is_first_run():
        return redirect(url_for("index"))
    detected = {
        "log_file": config.get("log_file") if config else "",
        "backup_dir": config.get("backup_dir") if config else "",
        "data_file": config.get("data_file") if config else "",
    }
    return render_template("setup.html", detected=detected, version=APP_VERSION)


@app.route("/setup", methods=["POST"])
def setup_post():
    """Handle first-run setup form submission."""
    host = request.host.split(":")[0]
    if host not in ("127.0.0.1", "localhost"):
        abort(403)

    log_file = request.form.get("log_file", "").strip()
    backup_dir = request.form.get("backup_dir", "").strip()
    data_file = request.form.get("data_file", "").strip()

    global LOG_FILE, DATA_FILE, BACKUP_DIR
    if config:
        if log_file:
            config.set("log_file", log_file)
        if backup_dir:
            config.set("backup_dir", backup_dir)
        if data_file:
            config.set("data_file", data_file)
        config.save()
        LOG_FILE = config.get("log_file")
        DATA_FILE = config.get("data_file")
        BACKUP_DIR = config.get("backup_dir")
        if LOG_FILE is not None and monitoring_thread is None:
            start_monitoring()

    return redirect(url_for("index"))


@app.route("/api/blueprints")
def get_blueprints():
    """Get all blueprints with optional filtering and sorting."""
    blueprints = get_blueprints_from_json(DATA_FILE)

    # Search filtering
    search_query = request.args.get("search", "").lower()
    if search_query:
        blueprints = [bp for bp in blueprints if search_query in bp["name"].lower()]

    # Sorting
    sort_by = request.args.get("sort", "timestamp")
    reverse = request.args.get("reverse", "false").lower() == "true"

    if sort_by == "name":
        blueprints.sort(key=lambda x: x["name"], reverse=reverse)
    else:  # timestamp (default)
        blueprints.sort(key=lambda x: x["timestamp"], reverse=not reverse)

    return jsonify(
        {
            "blueprints": blueprints,
            "total_count": len(blueprints),
            "last_updated": last_updated or datetime.now().isoformat(),
        }
    )


@app.route("/api/stats")
def get_stats():
    """Get statistics about blueprints."""
    blueprints = get_blueprints_from_json(DATA_FILE)

    # Today's blueprints
    today_str = datetime.now().strftime("%Y-%m-%d")
    today_count = sum(1 for bp in blueprints if bp["timestamp"].startswith(today_str))

    # Last acquired
    last_acquired = None
    if blueprints:
        last_acquired = blueprints[-1]

    return jsonify(
        {
            "total_count": len(blueprints),
            "today_count": today_count,
            "last_acquired": last_acquired,
            "monitoring_paused": _pause_event.is_set(),
            "is_scanning": _scanning_event.is_set(),
            "scan_status": dict(_scan_status),
            "last_updated": last_updated or datetime.now().isoformat(),
        }
    )


@app.route("/api/scan-backups", methods=["POST"])
def trigger_scan_backups():
    """Trigger a backup scan."""
    _require_xhr()
    global last_updated

    if _scanning_event.is_set():
        return jsonify({"error": "Scan already in progress"}), 400

    _scanning_event.set()
    _scan_status["current"] = 0
    _scan_status["total"] = 0
    _scan_status["found_new"] = 0

    def _on_progress(current, total, found_new):
        _scan_status["current"] = current
        _scan_status["total"] = total
        _scan_status["found_new"] = found_new

    def do_scan():
        global last_updated
        try:
            scan_backups(
                BACKUP_DIR, DATA_FILE, LOG_FILE, progress_callback=_on_progress
            )
            with lock:
                last_updated = datetime.now().isoformat()
        except Exception as e:
            logger.error("Error scanning backups: %s", e)
        finally:
            _scanning_event.clear()

    thread = threading.Thread(target=do_scan, daemon=True)
    thread.start()

    return jsonify({"status": "Backup scan started"})


@app.route("/api/pause", methods=["POST"])
def pause_monitoring():
    """Pause monitoring."""
    _require_xhr()
    _pause_event.set()
    return jsonify({"status": "Monitoring paused"})


@app.route("/api/resume", methods=["POST"])
def resume_monitoring():
    """Resume monitoring."""
    _require_xhr()
    _pause_event.clear()
    return jsonify({"status": "Monitoring resumed"})


@app.route("/api/status")
def get_status():
    """Get current application status."""
    return jsonify(
        {
            "log_file": LOG_FILE,
            "data_file": DATA_FILE,
            "backup_dir": BACKUP_DIR,
            "monitoring_paused": _pause_event.is_set(),
            "is_scanning": _scanning_event.is_set(),
            "log_exists": os.path.exists(LOG_FILE) if LOG_FILE else False,
        }
    )


@app.route("/api/export/csv", methods=["GET"])
def export_csv():
    """Export blueprints as CSV."""
    blueprints = get_blueprints_from_json(DATA_FILE)

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Blueprint Name", "Timestamp"])
    for bp in blueprints:
        writer.writerow([bp["name"], bp["timestamp"]])

    return (
        output.getvalue(),
        200,
        {
            "Content-Disposition": "attachment; filename=blueprints.csv",
            "Content-Type": "text/csv",
        },
    )


@app.route("/api/settings")
def get_settings():
    """Get current user-configurable settings."""
    if config is None:
        return jsonify({"error": "Configuration not loaded"}), 503
    return jsonify(
        {
            "ui_mode": config.get("ui_mode", "browser"),
            "log_file": config.get("log_file"),
            "backup_dir": config.get("backup_dir"),
            "data_file": config.get("data_file"),
            "poll_interval": config.get("poll_interval", 0.5),
        }
    )


@app.route("/api/settings", methods=["POST"])
def update_settings():
    """Update user-configurable settings."""
    _require_xhr()
    if config is None:
        return jsonify({"error": "Configuration not loaded"}), 503

    data = request.get_json(silent=True) or {}

    allowed_keys = {"ui_mode", "log_file", "backup_dir", "poll_interval"}
    updated = []
    for key in allowed_keys:
        if key in data:
            value = data[key]
            if key == "ui_mode" and value not in ("browser", "webview", "tray"):
                return jsonify({"error": f"Invalid ui_mode: {value}"}), 400
            if key == "poll_interval":
                try:
                    value = float(value)
                    if value < 0.1 or value > 60:
                        return jsonify(
                            {"error": "poll_interval must be between 0.1 and 60"}
                        ), 400
                except (TypeError, ValueError):
                    return jsonify({"error": "poll_interval must be a number"}), 400
            config.set(key, value)
            updated.append(key)

    if updated:
        config.save()

    return jsonify({"status": "ok", "updated": updated})


@app.route("/api/heartbeat")
def heartbeat():
    """Receive a keep-alive ping from the browser."""
    global _last_heartbeat
    with _heartbeat_lock:
        _last_heartbeat = time.time()
    return jsonify({"ok": True})


@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors."""
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors."""
    return jsonify({"error": "Internal server error"}), 500


def _start_browser_watchdog(timeout: float = 20.0) -> None:
    """Exit the process if no heartbeat is received for `timeout` seconds.

    The watchdog only activates after the first heartbeat arrives, so a slow
    browser open on startup does not trigger a false exit.
    """
    import sys

    def watch():
        while True:
            time.sleep(5)
            with _heartbeat_lock:
                hb = _last_heartbeat
            if hb is None:
                continue
            if time.time() - hb > timeout:
                logger.info("No browser heartbeat for %.0fs — exiting.", timeout)
                if sys.stdout is not None:
                    sys.stdout.flush()
                os._exit(0)

    t = threading.Thread(target=watch, daemon=True, name="browser-watchdog")
    t.start()


def run_server(port: int, browser_watchdog: bool = False) -> None:
    """Start the Flask server and monitoring thread. Blocks until stopped."""
    if LOG_FILE is not None:
        start_monitoring()
    if browser_watchdog:
        _start_browser_watchdog()
    app.run(host="127.0.0.1", port=port, debug=False, threaded=True, use_reloader=False)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    port = int(os.environ.get("BP_EXTRACT_PORT", "5000"))
    run_server(port)
