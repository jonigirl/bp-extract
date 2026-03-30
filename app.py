"""Flask web application for BP Extract."""

import os
import threading
from datetime import datetime

from flask import Flask, jsonify, render_template, request

from config import get_config
from core import (
    append_blueprint,
    get_blueprints_from_json,
    load_existing_blueprints,
    scan_backups,
    tail_log,
)
from setup_wizard import run_setup

app = Flask(__name__)

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

    # Run setup wizard if first run (but only if interactive - skip if running tests)
    try:
        run_setup()
    except (EOFError, KeyboardInterrupt):
        # In non-interactive mode, just skip setup
        pass

    LOG_FILE = config.get("log_file")
    DATA_FILE = config.get("data_file")
    BACKUP_DIR = config.get("backup_dir")
    POLL_INTERVAL = config.get("poll_interval", 0.5)
    WAIT_INTERVAL = config.get("wait_interval", 1.0)


# Initialize on import
try:
    initialize()
except Exception:
    # If initialization fails (e.g., in tests), continue with None values
    pass

# Global state
monitoring_thread = None
monitoring_paused = False
is_scanning = False
last_updated = None
lock = threading.Lock()


def start_monitoring():
    """Start background monitoring thread."""
    global monitoring_thread

    def monitor():
        global last_updated
        known_blueprints = load_existing_blueprints(DATA_FILE)
        tail_log(
            LOG_FILE,
            DATA_FILE,
            poll_interval=POLL_INTERVAL,
            wait_interval=WAIT_INTERVAL,
            known_blueprints=known_blueprints,
            should_pause_fn=lambda: monitoring_paused,
            stop_event=getattr(monitor, "_stop_event", None),
        )

    # Create and start thread
    stop_event = threading.Event()
    monitor._stop_event = stop_event
    monitoring_thread = threading.Thread(target=monitor, daemon=True)
    monitoring_thread.start()
    return monitoring_thread


@app.route("/")
def index():
    """Serve the main dashboard."""
    return render_template("index.html")


@app.route("/api/blueprints")
def get_blueprints():
    """Get all blueprints with optional filtering and sorting."""
    blueprints = get_blueprints_from_json(DATA_FILE)

    # Search filtering
    search_query = request.args.get("search", "").lower()
    if search_query:
        blueprints = [
            bp for bp in blueprints
            if search_query in bp["name"].lower()
        ]

    # Sorting
    sort_by = request.args.get("sort", "timestamp")
    reverse = request.args.get("reverse", "false").lower() == "true"

    if sort_by == "name":
        blueprints.sort(key=lambda x: x["name"], reverse=reverse)
    else:  # timestamp (default)
        blueprints.sort(key=lambda x: x["timestamp"], reverse=not reverse)

    return jsonify({
        "blueprints": blueprints,
        "total_count": len(blueprints),
        "last_updated": last_updated or datetime.now().isoformat(),
    })


@app.route("/api/stats")
def get_stats():
    """Get statistics about blueprints."""
    blueprints = get_blueprints_from_json(DATA_FILE)
    known_blueprints = load_existing_blueprints(DATA_FILE)

    # Today's blueprints
    today_str = datetime.now().strftime("%Y-%m-%d")
    today_count = sum(
        1 for bp in blueprints
        if bp["timestamp"].startswith(today_str)
    )

    # Last acquired
    last_acquired = None
    if blueprints:
        last_acquired = blueprints[-1]

    return jsonify({
        "total_count": len(known_blueprints),
        "today_count": today_count,
        "last_acquired": last_acquired,
        "monitoring_paused": monitoring_paused,
        "is_scanning": is_scanning,
        "last_updated": last_updated or datetime.now().isoformat(),
    })


@app.route("/api/scan-backups", methods=["POST"])
def trigger_scan_backups():
    """Trigger a backup scan."""
    global is_scanning, last_updated

    if is_scanning:
        return jsonify({"error": "Scan already in progress"}), 400

    is_scanning = True

    def do_scan():
        global is_scanning, last_updated
        try:
            scan_backups(BACKUP_DIR, DATA_FILE, LOG_FILE)
            last_updated = datetime.now().isoformat()
        except Exception as e:
            print(f"Error scanning backups: {e}")
        finally:
            is_scanning = False

    thread = threading.Thread(target=do_scan, daemon=True)
    thread.start()

    return jsonify({"status": "Backup scan started"})


@app.route("/api/pause", methods=["POST"])
def pause_monitoring():
    """Pause monitoring."""
    global monitoring_paused
    monitoring_paused = True
    return jsonify({"status": "Monitoring paused"})


@app.route("/api/resume", methods=["POST"])
def resume_monitoring():
    """Resume monitoring."""
    global monitoring_paused
    monitoring_paused = False
    return jsonify({"status": "Monitoring resumed"})


@app.route("/api/status")
def get_status():
    """Get current application status."""
    return jsonify({
        "log_file": LOG_FILE,
        "data_file": DATA_FILE,
        "backup_dir": BACKUP_DIR,
        "monitoring_paused": monitoring_paused,
        "is_scanning": is_scanning,
        "log_exists": os.path.exists(LOG_FILE) if LOG_FILE else False,
    })


@app.route("/api/export/csv", methods=["GET"])
def export_csv():
    """Export blueprints as CSV."""
    import csv
    from io import StringIO

    blueprints = get_blueprints_from_json(DATA_FILE)

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Blueprint Name", "Timestamp"])
    for bp in blueprints:
        writer.writerow([bp["name"], bp["timestamp"]])

    return output.getvalue(), 200, {
        "Content-Disposition": "attachment; filename=blueprints.csv",
        "Content-Type": "text/csv",
    }


@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors."""
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors."""
    return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    # Create necessary directories
    os.makedirs("templates", exist_ok=True)
    os.makedirs("static", exist_ok=True)

    # Initialize configuration
    initialize()

    # Start monitoring thread
    print(f"Starting BP Extract web server...")
    print(f"Monitoring log file: {LOG_FILE}")
    print(f"Data file: {DATA_FILE}")
    print(f"Access dashboard at: http://localhost:5000")

    monitoring_thread = start_monitoring()

    # Run Flask app
    app.run(debug=False, host="127.0.0.1", port=5000)
