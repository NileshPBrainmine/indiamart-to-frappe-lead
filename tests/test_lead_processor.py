import pytest
from unittest.mock import patch
from tests.conftest import FULL_LEAD

from app.lead_processor import process_lead
from app.frappe_service import RESULT_SUCCESS, RESULT_DUPLICATE, RESULT_ERROR


# ── helper ────────────────────────────────────────────────────────────────────

def _run(data, *, duplicate=False, post_result=(RESULT_SUCCESS, "ok")):
    with patch("app.lead_processor.is_duplicate", return_value=duplicate), \
         patch("app.lead_processor.create_lead", return_value=post_result) as mock_create, \
         patch("app.lead_processor.mark_seen") as mock_mark, \
         patch("app.lead_processor.save_failed_lead") as mock_failed, \
         patch("app.lead_processor.save_duplicate_lead") as mock_dup_save:
        process_lead(data)
        return mock_create, mock_mark, mock_failed, mock_dup_save


# ── field mapping ─────────────────────────────────────────────────────────────

class TestFieldMapping:

    def test_first_name(self):
        mock_create, *_ = _run(FULL_LEAD)
        assert mock_create.call_args[0][0]["first_name"] == "Alice"

    def test_phone(self):
        mock_create, *_ = _run(FULL_LEAD)
        assert mock_create.call_args[0][0]["phone"] == "9000000001"

    def test_email_id(self):
        mock_create, *_ = _run(FULL_LEAD)
        assert mock_create.call_args[0][0]["email_id"] == "alice@example.com"

    def test_company_name(self):
        mock_create, *_ = _run(FULL_LEAD)
        assert mock_create.call_args[0][0]["company_name"] == "Acme Corp"

    def test_city(self):
        mock_create, *_ = _run(FULL_LEAD)
        assert mock_create.call_args[0][0]["city"] == "Mumbai"

    def test_custom_state(self):
        mock_create, *_ = _run(FULL_LEAD)
        assert mock_create.call_args[0][0]["custom_state"] == "Maharashtra"

    def test_custom_address_city_and_state(self):
        mock_create, *_ = _run(FULL_LEAD)
        assert mock_create.call_args[0][0]["custom_address"] == "Mumbai, Maharashtra"

    def test_custom_address_city_only(self):
        mock_create, *_ = _run({**FULL_LEAD, "SENDER_STATE": ""})
        assert mock_create.call_args[0][0]["custom_address"] == "Mumbai"

    def test_custom_address_state_only(self):
        mock_create, *_ = _run({**FULL_LEAD, "SENDER_CITY": ""})
        assert mock_create.call_args[0][0]["custom_address"] == "Maharashtra"

    def test_custom_address_both_missing(self):
        mock_create, *_ = _run({**FULL_LEAD, "SENDER_CITY": "", "SENDER_STATE": ""})
        assert mock_create.call_args[0][0]["custom_address"] == ""

    def test_status_is_open(self):
        mock_create, *_ = _run(FULL_LEAD)
        assert mock_create.call_args[0][0]["status"] == "Open"

    def test_source_is_indiamart(self):
        mock_create, *_ = _run(FULL_LEAD)
        assert mock_create.call_args[0][0]["source"] == "Indiamart"


# ── query_about fallback chain ────────────────────────────────────────────────

class TestQueryAbout:

    def test_uses_query_message_first(self):
        mock_create, *_ = _run(FULL_LEAD)
        assert mock_create.call_args[0][0]["query_about"] == "I need 5 units"

    def test_falls_back_to_product_name(self):
        mock_create, *_ = _run({**FULL_LEAD, "QUERY_MESSAGE": ""})
        assert mock_create.call_args[0][0]["query_about"] == "CNC Machine"

    def test_falls_back_to_mcat_name(self):
        mock_create, *_ = _run({**FULL_LEAD, "QUERY_MESSAGE": "", "QUERY_PRODUCT_NAME": ""})
        assert mock_create.call_args[0][0]["query_about"] == "Machinery"

    def test_empty_string_when_all_missing(self):
        mock_create, *_ = _run({**FULL_LEAD, "QUERY_MESSAGE": "", "QUERY_PRODUCT_NAME": "", "QUERY_MCAT_NAME": ""})
        assert mock_create.call_args[0][0]["query_about"] == ""

    def test_none_values_treated_as_missing(self):
        mock_create, *_ = _run({**FULL_LEAD, "QUERY_MESSAGE": None, "QUERY_PRODUCT_NAME": None})
        assert mock_create.call_args[0][0]["query_about"] == "Machinery"


# ── dedup (seen cache) ────────────────────────────────────────────────────────

class TestDeduplication:

    def test_skips_create_for_seen_lead(self):
        mock_create, *_ = _run(FULL_LEAD, duplicate=True)
        mock_create.assert_not_called()

    def test_does_not_mark_seen_for_cached_lead(self):
        _, mock_mark, *_ = _run(FULL_LEAD, duplicate=True)
        mock_mark.assert_not_called()

    def test_uses_unique_query_id_as_key(self):
        with patch("app.lead_processor.is_duplicate", return_value=False) as mock_dup, \
             patch("app.lead_processor.create_lead", return_value=(RESULT_SUCCESS, "ok")), \
             patch("app.lead_processor.mark_seen"), \
             patch("app.lead_processor.save_failed_lead"), \
             patch("app.lead_processor.save_duplicate_lead"):
            process_lead(FULL_LEAD)
        mock_dup.assert_called_once_with("QID001")

    def test_fallback_key_when_unique_id_is_none(self):
        data = {**FULL_LEAD, "UNIQUE_QUERY_ID": None}
        with patch("app.lead_processor.is_duplicate", return_value=False) as mock_dup, \
             patch("app.lead_processor.create_lead", return_value=(RESULT_SUCCESS, "ok")), \
             patch("app.lead_processor.mark_seen"), \
             patch("app.lead_processor.save_failed_lead"), \
             patch("app.lead_processor.save_duplicate_lead"):
            process_lead(data)
        mock_dup.assert_called_once_with("9000000001_alice@example.com")

    def test_fallback_key_when_unique_id_absent(self):
        data = {k: v for k, v in FULL_LEAD.items() if k != "UNIQUE_QUERY_ID"}
        with patch("app.lead_processor.is_duplicate", return_value=False) as mock_dup, \
             patch("app.lead_processor.create_lead", return_value=(RESULT_SUCCESS, "ok")), \
             patch("app.lead_processor.mark_seen"), \
             patch("app.lead_processor.save_failed_lead"), \
             patch("app.lead_processor.save_duplicate_lead"):
            process_lead(data)
        mock_dup.assert_called_once_with("9000000001_alice@example.com")


# ── success path ──────────────────────────────────────────────────────────────

class TestSuccessPath:

    def test_marks_seen_on_success(self):
        _, mock_mark, *_ = _run(FULL_LEAD)
        mock_mark.assert_called_once_with("QID001")

    def test_does_not_save_failed_on_success(self):
        _, _, mock_failed, _ = _run(FULL_LEAD)
        mock_failed.assert_not_called()

    def test_does_not_save_duplicate_on_success(self):
        _, _, _, mock_dup_save = _run(FULL_LEAD)
        mock_dup_save.assert_not_called()


# ── duplicate email path (Frappe validation) ──────────────────────────────────

class TestDuplicateEmailPath:

    def test_marks_seen_on_duplicate_email(self):
        _, mock_mark, *_ = _run(FULL_LEAD, post_result=(RESULT_DUPLICATE, "Duplicate entry"))
        mock_mark.assert_called_once_with("QID001")

    def test_saves_to_duplicate_file(self):
        _, _, _, mock_dup_save = _run(FULL_LEAD, post_result=(RESULT_DUPLICATE, "Duplicate entry"))
        mock_dup_save.assert_called_once_with(FULL_LEAD, "Duplicate entry")

    def test_does_not_save_to_failed_file(self):
        _, _, mock_failed, _ = _run(FULL_LEAD, post_result=(RESULT_DUPLICATE, "Duplicate entry"))
        mock_failed.assert_not_called()

    def test_does_not_retry_duplicate_email(self):
        # mark_seen called means it won't be retried on next cycle
        _, mock_mark, *_ = _run(FULL_LEAD, post_result=(RESULT_DUPLICATE, "Duplicate entry"))
        mock_mark.assert_called_once()


# ── error path ────────────────────────────────────────────────────────────────

class TestErrorPath:

    def test_saves_to_failed_file_on_error(self):
        _, _, mock_failed, _ = _run(FULL_LEAD, post_result=(RESULT_ERROR, "500 Server Error"))
        mock_failed.assert_called_once_with(FULL_LEAD, "500 Server Error")

    def test_does_not_mark_seen_on_error(self):
        _, mock_mark, *_ = _run(FULL_LEAD, post_result=(RESULT_ERROR, "500 Server Error"))
        mock_mark.assert_not_called()

    def test_does_not_save_duplicate_on_error(self):
        _, _, _, mock_dup_save = _run(FULL_LEAD, post_result=(RESULT_ERROR, "500 Server Error"))
        mock_dup_save.assert_not_called()


# ── edge cases ────────────────────────────────────────────────────────────────

class TestEdgeCases:

    def test_handles_completely_empty_data(self):
        mock_create, *_ = _run({})
        payload = mock_create.call_args[0][0]
        assert payload["first_name"] is None
        assert payload["email_id"] is None
        assert payload["custom_address"] == ""
        assert payload["query_about"] == ""
        assert payload["status"] == "Open"
        assert payload["source"] == "Indiamart"

    def test_handles_missing_phone_and_email_in_fallback_key(self):
        data = {**FULL_LEAD, "UNIQUE_QUERY_ID": None, "SENDER_MOBILE": "", "SENDER_EMAIL": ""}
        with patch("app.lead_processor.is_duplicate", return_value=False) as mock_dup, \
             patch("app.lead_processor.create_lead", return_value=(RESULT_SUCCESS, "ok")), \
             patch("app.lead_processor.mark_seen"), \
             patch("app.lead_processor.save_failed_lead"), \
             patch("app.lead_processor.save_duplicate_lead"):
            process_lead(data)
        mock_dup.assert_called_once_with("_")
