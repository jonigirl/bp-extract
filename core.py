"""Core monitoring functions for BP Extract."""

import csv
import json
import os
import re
import time
from pathlib import Path

PATTERN = re.compile(r'<([^>]+)>.*Received Blueprint:\s*(.*?):\s*"')
YES_CHOICES = {"y", "yes"}
NO_CHOICES = {"n", "no"}

# Deprecated - kept for CSV migration only
DEFAULT_CSV_FILE = "blueprints.csv"


# ============================================================================
# JSON Data Management
# ============================================================================


def load_blueprints_data(data_file: str) -> dict:
    """Load blueprints data from JSON file.

    Returns: {"blueprints": [{"name": "...", "timestamp": "..."}]}
    """
    if not os.path.exists(data_file):
        return {"blueprints": []}

    try:
        with open(data_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Ensure correct structure
            if "blueprints" not in data:
                data = {"blueprints": []}
            return data
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error reading {data_file}: {e}")
        return {"blueprints": []}


def save_blueprints_data(data_file: str, data: dict) -> None:
    """Save blueprints data to JSON file."""
    try:
        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except IOError as e:
        print(f"Error writing to {data_file}: {e}")


def load_existing_blueprints(data_file: str) -> set:
    """Load existing blueprint names into a set for fast lookup."""
    data = load_blueprints_data(data_file)
    return {bp["name"] for bp in data["blueprints"]}


def get_blueprints_from_json(data_file: str) -> list:
    """Load blueprints with timestamps for web UI.

    Returns: [{"name": "...", "timestamp": "..."}, ...]
    """
    data = load_blueprints_data(data_file)
    return data.get("blueprints", [])


def append_blueprint(blueprint_name: str, timestamp: str, data_file: str) -> None:
    """Append a new blueprint entry to the JSON file."""
    data = load_blueprints_data(data_file)

    # Check if blueprint already exists
    for bp in data["blueprints"]:
        if bp["name"] == blueprint_name:
            # Already exists, don't add duplicate
            return

    # Add new blueprint
    data["blueprints"].append({"name": blueprint_name, "timestamp": timestamp})
    save_blueprints_data(data_file, data)


# ============================================================================
# CSV Migration (Legacy Support)
# ============================================================================


def migrate_csv_to_json(csv_file: str, data_file: str) -> bool:
    """Migrate existing CSV data to JSON format.

    Returns: True if migration successful, False otherwise.
    """
    if not os.path.exists(csv_file):
        return False

    print(f"Migrating data from {csv_file} to {data_file}...")

    try:
        blueprints = []
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for idx, row in enumerate(reader):
                if not row or len(row) < 2:
                    continue
                if idx == 0 and row[0].lower() == "blueprint name":
                    continue

                blueprints.append({"name": row[0], "timestamp": row[1]})

        # Save to JSON
        data = {"blueprints": blueprints}
        save_blueprints_data(data_file, data)

        print(f"[OK] Successfully migrated {len(blueprints)} blueprints to JSON")
        return True

    except Exception as e:
        print(f"[ERROR] Migration failed: {e}")
        return False


# ============================================================================
# Blueprint Processing
# ============================================================================


def process_blueprint(line: str, known_blueprints: set, data_file: str, source: str = "") -> bool:
    """Extract and process a blueprint from a log line if it's new.

    Returns: True if a new blueprint was processed, False otherwise.
    """
    match = PATTERN.search(line)
    if match:
        timestamp = match.group(1).strip()
        bp = match.group(2).strip()
        if bp not in known_blueprints:
            known_blueprints.add(bp)
            append_blueprint(bp, timestamp, data_file)
            if source:
                print(f"[{timestamp}] New blueprint acquired {source}: {bp}")
            else:
                print(f"[{timestamp}] New blueprint acquired: {bp}")
            return True
    return False


# ============================================================================
# File Monitoring
# ============================================================================


def get_file_id(path: str):
    """Get file ID (device + inode) to detect file rotation."""
    try:
        stat_result = os.stat(path)
        return stat_result.st_dev, stat_result.st_ino
    except FileNotFoundError:
        return None


def scan_backups(
    backup_dir: str, data_file: str, log_file: str = None
) -> set:
    """Scan backup log files for blueprints."""
    if not os.path.exists(backup_dir):
        print(f"Backup directory not found: {backup_dir}")
        return None

    known_blueprints = load_existing_blueprints(data_file)
    print(f"Scanning backups in {backup_dir}...")

    files = sorted([f for f in os.listdir(backup_dir) if f.endswith(".log")])
    if not files:
        print("No log backups found.")
        return None

    for filename in files:
        filepath = os.path.join(backup_dir, filename)
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    process_blueprint(line, known_blueprints, data_file, f"from backup {filename}")
        except (OSError, IOError) as e:
            print(f"Error reading {filename}: {e}")

    return known_blueprints


def tail_log(
    log_file: str,
    data_file: str,
    poll_interval: float = 0.5,
    wait_interval: float = 1.0,
    known_blueprints: set = None,
    should_pause_fn = None,
    stop_event = None,
) -> None:
    """Monitor a log file for new blueprints continuously.

    Args:
        log_file: Path to game log file to monitor
        data_file: Path to JSON data file
        poll_interval: Seconds between log checks
        wait_interval: Seconds to wait for log file to be created
        known_blueprints: Pre-loaded set of known blueprint names
        should_pause_fn: Optional callable that returns True if monitoring should pause
        stop_event: Optional threading.Event that signals when to stop monitoring
    """
    if known_blueprints is None:
        known_blueprints = load_existing_blueprints(data_file)

    print(f"Monitoring log file: {log_file}")

    # Wait for the file to exist before starting
    while not os.path.exists(log_file):
        if stop_event and stop_event.is_set():
            return
        print(f"Waiting for {log_file} to be created...", end="\r")
        time.sleep(wait_interval)

    print(f"\nLoaded {len(known_blueprints)} known blueprints.")
    print("Log processing started. Waiting for new lines...")

    f = None
    try:
        f = open(log_file, "r", encoding="utf-8", errors="replace")
        file_id = get_file_id(log_file)

        while True:
            if stop_event and stop_event.is_set():
                break

            # Check if paused
            if should_pause_fn and should_pause_fn():
                time.sleep(0.1)
                continue

            line = f.readline()
            if not line:
                # Reached end of file. Check if file was rotated/recreated.
                current_id = get_file_id(log_file)
                if current_id and current_id != file_id:
                    print(f"\n{log_file} was recreated/rotated. Reopening...")
                    f.close()
                    f = open(log_file, "r", encoding="utf-8", errors="replace")
                    file_id = current_id
                    continue

                time.sleep(poll_interval)
                continue

            process_blueprint(line, known_blueprints, data_file, "and logged")
    finally:
        if f:
            f.close()
