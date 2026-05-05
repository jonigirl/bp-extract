"""Flask web application for BP Extract."""

import csv
import os
import sys
import threading
from datetime import datetime
from io import StringIO

from flask import Flask, jsonify, render_template, request

from config import get_config
from core import (
    get_blueprints_from_json,
    load_existing_blueprints,
    scan_backups,
    tail_log,
)

APP_VERSION = "0.3.0"

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", os.urandom(24))

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


# Initialize on import
try:
    initialize()
except Exception as e:
    print(f"Warning: startup initialization failed: {e}", file=sys.stderr)

# Global state
monitoring_thread = None
_stop_event = None
_pause_event = threading.Event()  # set() = monitoring paused
_scanning_event = threading.Event()  # set() = backup scan in progress
last_updated = None
lock = threading.Lock()


def start_monitoring():
    """Start background monitoring thread."""
    global monitoring_thread, _stop_event

    _stop_event = threading.Event()
    stop_event = _stop_event  # captured by closure

    def monitor():
        known_blueprints = load_existing_blueprints(DATA_FILE)
        tail_log(
            LOG_FILE,
            DATA_FILE,
            poll_interval=POLL_INTERVAL,
            wait_interval=WAIT_INTERVAL,
            known_blueprints=known_blueprints,
            should_pause_fn=_pause_event.is_set,
            stop_event=stop_event,
        )

    monitoring_thread = threading.Thread(target=monitor, daemon=True)
    monitoring_thread.start()
    return monitoring_thread


@app.before_request
def check_initialized():
    """Return 503 if the app failed to initialize."""
    if DATA_FILE is None and request.endpoint not in ("index", "static", None):
        return jsonify(
            {"error": "Configuration not loaded. Check the console for errors."}
        ), 503


@app.route("/")
def index():
    """Serve the main dashboard."""
    return render_template("index.html", version=APP_VERSION)


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
            "last_updated": last_updated or datetime.now().isoformat(),
        }
    )


@app.route("/api/scan-backups", methods=["POST"])
def trigger_scan_backups():
    """Trigger a backup scan."""
    global last_updated

    if _scanning_event.is_set():
        return jsonify({"error": "Scan already in progress"}), 400

    _scanning_event.set()

    def do_scan():
        global last_updated
        try:
            scan_backups(BACKUP_DIR, DATA_FILE, LOG_FILE)
            with lock:
                last_updated = datetime.now().isoformat()
        except Exception as e:
            print(f"Error scanning backups: {e}")
        finally:
            _scanning_event.clear()

    thread = threading.Thread(target=do_scan, daemon=True)
    thread.start()

    return jsonify({"status": "Backup scan started"})


@app.route("/api/pause", methods=["POST"])
def pause_monitoring():
    """Pause monitoring."""
    _pause_event.set()
    return jsonify({"status": "Monitoring paused"})


@app.route("/api/resume", methods=["POST"])
def resume_monitoring():
    """Resume monitoring."""
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


@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors."""
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors."""
    return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    _base = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(os.path.join(_base, "templates"), exist_ok=True)
    os.makedirs(os.path.join(_base, "static"), exist_ok=True)

    _port = int(os.environ.get("BP_EXTRACT_PORT", 5000))

    print("Starting BP Extract web server...")
    print(f"Monitoring log file: {LOG_FILE}")
    print(f"Data file: {DATA_FILE}")
    print(f"Access dashboard at: http://127.0.0.1:{_port}")

    monitoring_thread = start_monitoring()

    app.run(debug=False, host="127.0.0.1", port=_port)
