import json
import threading
from unittest.mock import patch

from core import (
    append_blueprint,
    get_blueprints_from_json,
    get_file_id,
    load_blueprints_data,
    load_existing_blueprints,
    migrate_csv_to_json,
    process_blueprint,
    save_blueprints_data,
    scan_backups,
    tail_log,
)

# Real Game.log format: notification lines with no trailing data after the quote
VALID_LOG_LINE = (
    "<2026-03-26T01:43:22.515Z> [Notice] <SHUDEvent_OnNotification> Added "
    'notification "Received Blueprint: My Blueprint: " [19] to queue.'
)
# Blueprint name containing embedded quotes (real example)
VALID_LOG_LINE_QUOTED_NAME = (
    "<2026-03-26T03:21:02.390Z> [Notice] <SHUDEvent_OnNotification> Added "
    'notification "Received Blueprint: Zenith "Thunderstrike" Laser Sniper Rifle: " [35] to queue.'
)
# Realistic noise lines that should not be parsed as blueprints
NOISE_LINES = [
    "<2026-05-04T10:21:25.392Z> [Notice] <CreateChannel> Opening channel for sc.external.f7a3c...",
    "<2026-05-04T10:21:25.394Z> [Trace] @session: '66d449eb-fb6d-1343-a075-24a5892361a5'",
    "<2026-05-04T10:21:25.394Z> ===============================================================",
]


class TestLoadBlueprintsData:
    def test_missing_file_returns_empty(self, tmp_path):
        result = load_blueprints_data(str(tmp_path / "nonexistent.json"))
        assert result == {"blueprints": []}

    def test_valid_json_loads_correctly(self, tmp_path):
        data_file = tmp_path / "data.json"
        data = {"blueprints": [{"name": "Alpha", "timestamp": "2024-01-01"}]}
        data_file.write_text(json.dumps(data), encoding="utf-8")
        assert load_blueprints_data(str(data_file)) == data

    def test_corrupt_json_returns_empty(self, tmp_path):
        data_file = tmp_path / "data.json"
        data_file.write_text("{ not valid json", encoding="utf-8")
        assert load_blueprints_data(str(data_file)) == {"blueprints": []}

    def test_missing_blueprints_key_is_normalised(self, tmp_path):
        data_file = tmp_path / "data.json"
        data_file.write_text(json.dumps({"other": "stuff"}), encoding="utf-8")
        assert load_blueprints_data(str(data_file)) == {"blueprints": []}


class TestSaveBlueprintsData:
    def test_writes_json_to_disk(self, tmp_path):
        data_file = tmp_path / "data.json"
        data = {"blueprints": [{"name": "Alpha", "timestamp": "2024-01-01"}]}
        save_blueprints_data(str(data_file), data)
        assert json.loads(data_file.read_text(encoding="utf-8")) == data

    def test_overwrites_existing_file(self, tmp_path):
        data_file = tmp_path / "data.json"
        data_file.write_text(json.dumps({"blueprints": []}), encoding="utf-8")
        new_data = {"blueprints": [{"name": "Beta", "timestamp": "2024-02-01"}]}
        save_blueprints_data(str(data_file), new_data)
        assert json.loads(data_file.read_text(encoding="utf-8")) == new_data

    def test_silently_handles_write_error(self, tmp_path):
        path = str(tmp_path / "nonexistent_subdir" / "data.json")
        save_blueprints_data(path, {"blueprints": []})


class TestLoadExistingBlueprints:
    def test_returns_set_of_names(self, tmp_path):
        data_file = tmp_path / "data.json"
        data = {
            "blueprints": [
                {"name": "Alpha", "timestamp": "2024-01-01"},
                {"name": "Beta", "timestamp": "2024-01-02"},
            ]
        }
        data_file.write_text(json.dumps(data), encoding="utf-8")
        assert load_existing_blueprints(str(data_file)) == {"Alpha", "Beta"}

    def test_missing_file_returns_empty_set(self, tmp_path):
        assert load_existing_blueprints(str(tmp_path / "nonexistent.json")) == set()


class TestGetBlueprintsFromJson:
    def test_returns_list_of_dicts(self, tmp_path):
        data_file = tmp_path / "data.json"
        blueprints = [
            {"name": "Alpha", "timestamp": "2024-01-01"},
            {"name": "Beta", "timestamp": "2024-01-02"},
        ]
        data_file.write_text(json.dumps({"blueprints": blueprints}), encoding="utf-8")
        assert get_blueprints_from_json(str(data_file)) == blueprints

    def test_missing_file_returns_empty_list(self, tmp_path):
        assert get_blueprints_from_json(str(tmp_path / "nonexistent.json")) == []


class TestAppendBlueprint:
    def test_adds_new_blueprint(self, tmp_path):
        data_file = tmp_path / "data.json"
        data_file.write_text(json.dumps({"blueprints": []}), encoding="utf-8")
        append_blueprint("Alpha", "2024-01-01", str(data_file))
        result = json.loads(data_file.read_text(encoding="utf-8"))
        assert len(result["blueprints"]) == 1
        assert result["blueprints"][0]["name"] == "Alpha"

    def test_skips_duplicate(self, tmp_path):
        data_file = tmp_path / "data.json"
        existing = {"blueprints": [{"name": "Alpha", "timestamp": "2024-01-01"}]}
        data_file.write_text(json.dumps(existing), encoding="utf-8")
        append_blueprint("Alpha", "2024-01-02", str(data_file))
        result = json.loads(data_file.read_text(encoding="utf-8"))
        assert len(result["blueprints"]) == 1

    def test_creates_file_when_missing(self, tmp_path):
        data_file = str(tmp_path / "new_data.json")
        append_blueprint("Alpha", "2024-01-01", data_file)
        result = json.loads(open(data_file, encoding="utf-8").read())
        assert result["blueprints"][0]["name"] == "Alpha"


class TestMigrateCsvToJson:
    def test_missing_csv_returns_false(self, tmp_path):
        result = migrate_csv_to_json(
            str(tmp_path / "nonexistent.csv"), str(tmp_path / "data.json")
        )
        assert result is False

    def test_valid_csv_with_header_migrates_correctly(self, tmp_path):
        csv_file = tmp_path / "blueprints.csv"
        data_file = tmp_path / "data.json"
        csv_file.write_text(
            "blueprint name,timestamp\nAlpha,2024-01-01\nBeta,2024-01-02\n",
            encoding="utf-8",
        )
        result = migrate_csv_to_json(str(csv_file), str(data_file))
        assert result is True
        data = json.loads(data_file.read_text(encoding="utf-8"))
        assert len(data["blueprints"]) == 2
        assert data["blueprints"][0] == {"name": "Alpha", "timestamp": "2024-01-01"}

    def test_csv_without_header_migrates_all_rows(self, tmp_path):
        csv_file = tmp_path / "blueprints.csv"
        data_file = tmp_path / "data.json"
        csv_file.write_text("Alpha,2024-01-01\nBeta,2024-01-02\n", encoding="utf-8")
        result = migrate_csv_to_json(str(csv_file), str(data_file))
        assert result is True
        data = json.loads(data_file.read_text(encoding="utf-8"))
        assert len(data["blueprints"]) == 2

    def test_skips_rows_with_fewer_than_two_columns(self, tmp_path):
        csv_file = tmp_path / "blueprints.csv"
        data_file = tmp_path / "data.json"
        csv_file.write_text("Alpha\nBeta,2024-01-02\n", encoding="utf-8")
        migrate_csv_to_json(str(csv_file), str(data_file))
        data = json.loads(data_file.read_text(encoding="utf-8"))
        assert len(data["blueprints"]) == 1
        assert data["blueprints"][0]["name"] == "Beta"

    def test_returns_false_on_save_exception(self, tmp_path):
        csv_file = tmp_path / "blueprints.csv"
        csv_file.write_text("Alpha,2024-01-01\n", encoding="utf-8")
        with patch("core.save_blueprints_data", side_effect=Exception("disk error")):
            result = migrate_csv_to_json(str(csv_file), str(tmp_path / "data.json"))
        assert result is False


class TestProcessBlueprint:
    def test_valid_line_returns_true(self, tmp_path):
        known = set()
        result = process_blueprint(VALID_LOG_LINE, known, str(tmp_path / "data.json"))
        assert result is True

    def test_valid_line_adds_to_known_set(self, tmp_path):
        known = set()
        process_blueprint(VALID_LOG_LINE, known, str(tmp_path / "data.json"))
        assert "My Blueprint" in known

    def test_valid_line_persists_to_data_file(self, tmp_path):
        data_file = str(tmp_path / "data.json")
        process_blueprint(VALID_LOG_LINE, set(), data_file)
        blueprints = get_blueprints_from_json(data_file)
        assert any(bp["name"] == "My Blueprint" for bp in blueprints)

    def test_irrelevant_line_returns_false(self, tmp_path):
        known = set()
        result = process_blueprint(
            "Some unrelated log line", known, str(tmp_path / "data.json")
        )
        assert result is False

    def test_duplicate_blueprint_returns_false(self, tmp_path):
        known = {"My Blueprint"}
        result = process_blueprint(VALID_LOG_LINE, known, str(tmp_path / "data.json"))
        assert result is False

    def test_duplicate_does_not_write_to_file(self, tmp_path):
        data_file = tmp_path / "data.json"
        data_file.write_text(
            json.dumps(
                {"blueprints": [{"name": "My Blueprint", "timestamp": "2024-01-01"}]}
            ),
            encoding="utf-8",
        )
        process_blueprint(VALID_LOG_LINE, {"My Blueprint"}, str(data_file))
        data = json.loads(data_file.read_text(encoding="utf-8"))
        assert len(data["blueprints"]) == 1

    def test_noise_lines_return_false(self, tmp_path):
        known = set()
        data_file = str(tmp_path / "data.json")
        for line in NOISE_LINES:
            assert process_blueprint(line, known, data_file) is False
        assert known == set()

    def test_blueprint_name_with_embedded_quotes(self, tmp_path):
        """Blueprint names that contain double-quotes parse correctly."""
        known = set()
        data_file = str(tmp_path / "data.json")
        result = process_blueprint(VALID_LOG_LINE_QUOTED_NAME, known, data_file)
        assert result is True
        assert any('"Thunderstrike"' in name for name in known)


class TestScanBackups:
    def test_missing_dir_returns_empty_set(self, tmp_path):
        result = scan_backups(
            str(tmp_path / "nonexistent"), str(tmp_path / "data.json")
        )
        assert result == set()

    def test_empty_dir_no_log_files_returns_empty_set(self, tmp_path):
        backup_dir = tmp_path / "logbackups"
        backup_dir.mkdir()
        result = scan_backups(str(backup_dir), str(tmp_path / "data.json"))
        assert result == set()

    def test_processes_blueprints_from_log_files(self, tmp_path):
        backup_dir = tmp_path / "logbackups"
        backup_dir.mkdir()
        data_file = str(tmp_path / "data.json")
        content = (
            "<2026-03-26T01:43:22.515Z> [Notice] <SHUDEvent_OnNotification> Added "
            'notification "Received Blueprint: Backup Blueprint: " [19] to queue.'
        )
        (backup_dir / "game_backup.log").write_text(content, encoding="utf-8")
        result = scan_backups(str(backup_dir), data_file)
        assert result is not None
        assert "Backup Blueprint" in result


class TestTailLog:
    def test_returns_when_stop_event_set_before_file_exists(self, tmp_path):
        stop_event = threading.Event()
        stop_event.set()
        log_path = str(tmp_path / "nonexistent.log")
        data_file = str(tmp_path / "data.json")
        tail_log(log_path, data_file, wait_interval=0.01, stop_event=stop_event)

    def test_returns_when_stop_event_set_with_existing_file(self, tmp_path):
        stop_event = threading.Event()
        stop_event.set()
        log_file = tmp_path / "Game.log"
        log_file.write_text("", encoding="utf-8")
        data_file = str(tmp_path / "data.json")
        tail_log(str(log_file), data_file, stop_event=stop_event)


class TestGetFileId:
    def test_returns_two_element_tuple_for_existing_file(self, tmp_path):
        f = tmp_path / "test.log"
        f.write_text("content", encoding="utf-8")
        result = get_file_id(str(f))
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_returns_none_for_missing_file(self, tmp_path):
        result = get_file_id(str(tmp_path / "nonexistent.log"))
        assert result is None
