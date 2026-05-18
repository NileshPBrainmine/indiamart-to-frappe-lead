import json
import os
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch


def _patch_paths(tmp_path):
    seen_file = str(tmp_path / "seen_leads.json")
    return (
        patch("utils.helpers.LOG_DIR", str(tmp_path)),
        patch("utils.helpers.SEEN_LEADS_FILE", seen_file),
    )


# ── is_duplicate ──────────────────────────────────────────────────────────────

class TestIsDuplicate:

    def test_returns_false_for_brand_new_lead(self, tmp_path):
        p1, p2 = _patch_paths(tmp_path)
        with p1, p2:
            from utils.helpers import is_duplicate
            assert is_duplicate("NEW_001") is False

    def test_returns_true_after_mark_seen(self, tmp_path):
        seen_file = tmp_path / "seen_leads.json"
        seen_file.write_text(json.dumps({"KNOWN_001": datetime.now().isoformat()}))
        p1, p2 = _patch_paths(tmp_path)
        with p1, p2:
            from utils.helpers import is_duplicate
            assert is_duplicate("KNOWN_001") is True

    def test_returns_false_for_expired_lead(self, tmp_path):
        expired_ts = (datetime.now() - timedelta(hours=25)).isoformat()
        seen_file = tmp_path / "seen_leads.json"
        seen_file.write_text(json.dumps({"OLD_001": expired_ts}))
        p1, p2 = _patch_paths(tmp_path)
        with p1, p2:
            from utils.helpers import is_duplicate
            assert is_duplicate("OLD_001") is False

    def test_purges_expired_entries_from_file(self, tmp_path):
        seen_file = tmp_path / "seen_leads.json"
        seen_file.write_text(json.dumps({
            "OLD_001": (datetime.now() - timedelta(hours=25)).isoformat(),
            "FRESH_001": datetime.now().isoformat(),
        }))
        p1, p2 = _patch_paths(tmp_path)
        with p1, p2:
            from utils.helpers import is_duplicate
            is_duplicate("ANY")
            remaining = json.loads(seen_file.read_text())
        assert "OLD_001" not in remaining
        assert "FRESH_001" in remaining

    def test_returns_false_when_file_does_not_exist(self, tmp_path):
        p1, p2 = _patch_paths(tmp_path)
        with p1, p2:
            from utils.helpers import is_duplicate
            assert is_duplicate("MISSING_001") is False

    def test_different_leads_are_independent(self, tmp_path):
        seen_file = tmp_path / "seen_leads.json"
        seen_file.write_text(json.dumps({"LEAD_A": datetime.now().isoformat()}))
        p1, p2 = _patch_paths(tmp_path)
        with p1, p2:
            from utils.helpers import is_duplicate
            assert is_duplicate("LEAD_A") is True
            assert is_duplicate("LEAD_B") is False


# ── mark_seen ─────────────────────────────────────────────────────────────────

class TestMarkSeen:

    def test_creates_seen_file_if_missing(self, tmp_path):
        p1, p2 = _patch_paths(tmp_path)
        with p1, p2:
            from utils.helpers import mark_seen
            mark_seen("LEAD_001")
        assert (tmp_path / "seen_leads.json").exists()

    def test_stores_lead_id(self, tmp_path):
        p1, p2 = _patch_paths(tmp_path)
        with p1, p2:
            from utils.helpers import mark_seen
            mark_seen("LEAD_001")
        data = json.loads((tmp_path / "seen_leads.json").read_text())
        assert "LEAD_001" in data

    def test_stores_iso_timestamp(self, tmp_path):
        p1, p2 = _patch_paths(tmp_path)
        with p1, p2:
            from utils.helpers import mark_seen
            mark_seen("LEAD_001")
        ts = json.loads((tmp_path / "seen_leads.json").read_text())["LEAD_001"]
        datetime.fromisoformat(ts)

    def test_appends_without_overwriting_others(self, tmp_path):
        seen_file = tmp_path / "seen_leads.json"
        seen_file.write_text(json.dumps({"EXISTING": datetime.now().isoformat()}))
        p1, p2 = _patch_paths(tmp_path)
        with p1, p2:
            from utils.helpers import mark_seen
            mark_seen("NEW_001")
        data = json.loads(seen_file.read_text())
        assert "EXISTING" in data
        assert "NEW_001" in data

    def test_refreshes_timestamp_on_re_mark(self, tmp_path):
        old_ts = (datetime.now() - timedelta(hours=10)).isoformat()
        seen_file = tmp_path / "seen_leads.json"
        seen_file.write_text(json.dumps({"LEAD_001": old_ts}))
        p1, p2 = _patch_paths(tmp_path)
        with p1, p2:
            from utils.helpers import mark_seen
            mark_seen("LEAD_001")
        assert json.loads(seen_file.read_text())["LEAD_001"] > old_ts


# ── save_failed_lead ──────────────────────────────────────────────────────────

class TestSaveFailedLead:

    def test_creates_failed_leads_file(self, tmp_path):
        p1, p2 = _patch_paths(tmp_path)
        with p1, p2:
            from utils.helpers import save_failed_lead
            save_failed_lead({"email": "a@b.com"}, "500 Error")
        assert (tmp_path / "failed_leads.jsonl").exists()

    def test_record_has_timestamp(self, tmp_path):
        p1, p2 = _patch_paths(tmp_path)
        with p1, p2:
            from utils.helpers import save_failed_lead
            save_failed_lead({"email": "a@b.com"}, "err")
        record = json.loads((tmp_path / "failed_leads.jsonl").read_text().strip())
        datetime.fromisoformat(record["timestamp"])

    def test_record_has_error_message(self, tmp_path):
        p1, p2 = _patch_paths(tmp_path)
        with p1, p2:
            from utils.helpers import save_failed_lead
            save_failed_lead({"email": "a@b.com"}, "401 Unauthorized")
        record = json.loads((tmp_path / "failed_leads.jsonl").read_text().strip())
        assert record["error"] == "401 Unauthorized"

    def test_record_has_lead_data(self, tmp_path):
        lead = {"SENDER_EMAIL": "a@b.com", "SENDER_NAME": "Alice"}
        p1, p2 = _patch_paths(tmp_path)
        with p1, p2:
            from utils.helpers import save_failed_lead
            save_failed_lead(lead, "err")
        assert json.loads((tmp_path / "failed_leads.jsonl").read_text().strip())["lead_data"] == lead

    def test_appends_multiple_records(self, tmp_path):
        p1, p2 = _patch_paths(tmp_path)
        with p1, p2:
            from utils.helpers import save_failed_lead
            save_failed_lead({"id": 1}, "err1")
            save_failed_lead({"id": 2}, "err2")
        lines = (tmp_path / "failed_leads.jsonl").read_text().strip().splitlines()
        assert len(lines) == 2
        assert json.loads(lines[1])["error"] == "err2"

    def test_each_line_is_valid_json(self, tmp_path):
        p1, p2 = _patch_paths(tmp_path)
        with p1, p2:
            from utils.helpers import save_failed_lead
            for i in range(5):
                save_failed_lead({"id": i}, f"error_{i}")
        for line in (tmp_path / "failed_leads.jsonl").read_text().strip().splitlines():
            json.loads(line)


# ── save_duplicate_lead ───────────────────────────────────────────────────────

class TestSaveDuplicateLead:

    def test_creates_duplicate_leads_file(self, tmp_path):
        p1, p2 = _patch_paths(tmp_path)
        with p1, p2:
            from utils.helpers import save_duplicate_lead
            save_duplicate_lead({"SENDER_EMAIL": "a@b.com"}, "Duplicate entry")
        assert (tmp_path / "duplicate_leads.jsonl").exists()

    def test_record_has_timestamp(self, tmp_path):
        p1, p2 = _patch_paths(tmp_path)
        with p1, p2:
            from utils.helpers import save_duplicate_lead
            save_duplicate_lead({"SENDER_EMAIL": "a@b.com"}, "err")
        record = json.loads((tmp_path / "duplicate_leads.jsonl").read_text().strip())
        datetime.fromisoformat(record["timestamp"])

    def test_record_has_email_id(self, tmp_path):
        p1, p2 = _patch_paths(tmp_path)
        with p1, p2:
            from utils.helpers import save_duplicate_lead
            save_duplicate_lead({"SENDER_EMAIL": "alice@example.com"}, "err")
        record = json.loads((tmp_path / "duplicate_leads.jsonl").read_text().strip())
        assert record["email_id"] == "alice@example.com"

    def test_record_has_error_message(self, tmp_path):
        p1, p2 = _patch_paths(tmp_path)
        with p1, p2:
            from utils.helpers import save_duplicate_lead
            save_duplicate_lead({"SENDER_EMAIL": "a@b.com"}, "DuplicateEntryError")
        record = json.loads((tmp_path / "duplicate_leads.jsonl").read_text().strip())
        assert record["error"] == "DuplicateEntryError"

    def test_record_has_full_lead_data(self, tmp_path):
        lead = {"SENDER_EMAIL": "a@b.com", "SENDER_NAME": "Alice", "UNIQUE_QUERY_ID": "QID001"}
        p1, p2 = _patch_paths(tmp_path)
        with p1, p2:
            from utils.helpers import save_duplicate_lead
            save_duplicate_lead(lead, "err")
        record = json.loads((tmp_path / "duplicate_leads.jsonl").read_text().strip())
        assert record["lead_data"] == lead

    def test_appends_multiple_duplicate_records(self, tmp_path):
        p1, p2 = _patch_paths(tmp_path)
        with p1, p2:
            from utils.helpers import save_duplicate_lead
            save_duplicate_lead({"SENDER_EMAIL": "a@b.com"}, "dup1")
            save_duplicate_lead({"SENDER_EMAIL": "b@c.com"}, "dup2")
        lines = (tmp_path / "duplicate_leads.jsonl").read_text().strip().splitlines()
        assert len(lines) == 2

    def test_does_not_write_to_failed_leads_file(self, tmp_path):
        p1, p2 = _patch_paths(tmp_path)
        with p1, p2:
            from utils.helpers import save_duplicate_lead
            save_duplicate_lead({"SENDER_EMAIL": "a@b.com"}, "err")
        assert not (tmp_path / "failed_leads.jsonl").exists()

    def test_email_id_empty_string_when_missing(self, tmp_path):
        p1, p2 = _patch_paths(tmp_path)
        with p1, p2:
            from utils.helpers import save_duplicate_lead
            save_duplicate_lead({}, "err")
        record = json.loads((tmp_path / "duplicate_leads.jsonl").read_text().strip())
        assert record["email_id"] == ""
