import pytest
import requests
from unittest.mock import patch, MagicMock

from app.frappe_service import create_lead, RESULT_SUCCESS, RESULT_DUPLICATE, RESULT_ERROR

SAMPLE_LEAD = {
    "first_name": "Alice",
    "email_id": "alice@example.com",
    "phone": "9000000001",
    "status": "Open",
    "source": "Indiamart",
}


def _http_error(status_code, json_body=None, text_body=""):
    resp = MagicMock()
    resp.status_code = status_code
    if json_body is not None:
        resp.json.return_value = json_body
    else:
        resp.json.side_effect = ValueError("No JSON")
        resp.text = text_body
    err = requests.exceptions.HTTPError(response=resp)
    err.response = resp
    return err


def _success_response():
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status.return_value = None
    return resp


# ── success ───────────────────────────────────────────────────────────────────

class TestCreateLeadSuccess:

    @patch("app.frappe_service.requests.post")
    def test_returns_success_status_on_200(self, mock_post):
        mock_post.return_value = _success_response()
        status, _ = create_lead(SAMPLE_LEAD)
        assert status == RESULT_SUCCESS

    @patch("app.frappe_service.requests.post")
    def test_success_message(self, mock_post):
        mock_post.return_value = _success_response()
        _, msg = create_lead(SAMPLE_LEAD)
        assert msg == "Lead created successfully"

    @patch("app.frappe_service.requests.post")
    def test_posts_to_correct_url(self, mock_post):
        mock_post.return_value = _success_response()
        with patch("app.frappe_service.FRAPPE_URL", "https://erp.example.com"):
            create_lead(SAMPLE_LEAD)
        assert mock_post.call_args[0][0] == "https://erp.example.com/api/resource/Lead"

    @patch("app.frappe_service.requests.post")
    def test_sends_authorization_header(self, mock_post):
        mock_post.return_value = _success_response()
        with patch("app.frappe_service.FRAPPE_TOKEN", "token key:secret"):
            create_lead(SAMPLE_LEAD)
        assert mock_post.call_args[1]["headers"]["Authorization"] == "token key:secret"

    @patch("app.frappe_service.requests.post")
    def test_sends_content_type_header(self, mock_post):
        mock_post.return_value = _success_response()
        create_lead(SAMPLE_LEAD)
        assert mock_post.call_args[1]["headers"]["Content-Type"] == "application/json"

    @patch("app.frappe_service.requests.post")
    def test_sends_lead_as_json_body(self, mock_post):
        mock_post.return_value = _success_response()
        create_lead(SAMPLE_LEAD)
        assert mock_post.call_args[1]["json"] == SAMPLE_LEAD


# ── duplicate email detection ─────────────────────────────────────────────────

class TestDuplicateEmailDetection:

    @patch("app.frappe_service.requests.post")
    def test_returns_duplicate_on_409(self, mock_post):
        mock_post.return_value.raise_for_status.side_effect = _http_error(409, text_body="Conflict")
        status, _ = create_lead(SAMPLE_LEAD)
        assert status == RESULT_DUPLICATE

    @patch("app.frappe_service.requests.post")
    def test_returns_duplicate_on_exc_type_duplicateentryerror(self, mock_post):
        mock_post.return_value.raise_for_status.side_effect = _http_error(
            422, json_body={"exc_type": "DuplicateEntryError", "message": "Lead exists"}
        )
        status, _ = create_lead(SAMPLE_LEAD)
        assert status == RESULT_DUPLICATE

    @patch("app.frappe_service.requests.post")
    def test_returns_duplicate_on_message_duplicate_entry(self, mock_post):
        mock_post.return_value.raise_for_status.side_effect = _http_error(
            422, json_body={"exc_type": "ValidationError", "message": "Duplicate entry for email"}
        )
        status, _ = create_lead(SAMPLE_LEAD)
        assert status == RESULT_DUPLICATE

    @patch("app.frappe_service.requests.post")
    def test_returns_duplicate_on_message_already_exists(self, mock_post):
        mock_post.return_value.raise_for_status.side_effect = _http_error(
            422, json_body={"message": "Lead already exists with this email"}
        )
        status, _ = create_lead(SAMPLE_LEAD)
        assert status == RESULT_DUPLICATE

    @patch("app.frappe_service.requests.post")
    def test_returns_duplicate_on_text_body_duplicate_entry(self, mock_post):
        mock_post.return_value.raise_for_status.side_effect = _http_error(
            422, text_body="Duplicate entry 'alice@example.com'"
        )
        status, _ = create_lead(SAMPLE_LEAD)
        assert status == RESULT_DUPLICATE

    @patch("app.frappe_service.requests.post")
    def test_returns_duplicate_on_exc_field_in_traceback(self, mock_post):
        mock_post.return_value.raise_for_status.side_effect = _http_error(
            422, json_body={"exc": "...DuplicateEntryError: alice@example.com..."}
        )
        status, _ = create_lead(SAMPLE_LEAD)
        assert status == RESULT_DUPLICATE

    @patch("app.frappe_service.requests.post")
    def test_non_duplicate_422_returns_error_not_duplicate(self, mock_post):
        mock_post.return_value.raise_for_status.side_effect = _http_error(
            422, json_body={"exc_type": "ValidationError", "message": "Missing required field"}
        )
        status, _ = create_lead(SAMPLE_LEAD)
        assert status == RESULT_ERROR

    @patch("app.frappe_service.requests.post")
    def test_duplicate_result_includes_error_message(self, mock_post):
        mock_post.return_value.raise_for_status.side_effect = _http_error(
            409, text_body="Conflict"
        )
        status, msg = create_lead(SAMPLE_LEAD)
        assert status == RESULT_DUPLICATE
        assert msg != ""


# ── other http errors ─────────────────────────────────────────────────────────

class TestCreateLeadHttpErrors:

    @patch("app.frappe_service.requests.post")
    def test_returns_error_on_401(self, mock_post):
        mock_post.return_value.raise_for_status.side_effect = _http_error(401, text_body="Unauthorized")
        status, _ = create_lead(SAMPLE_LEAD)
        assert status == RESULT_ERROR

    @patch("app.frappe_service.requests.post")
    def test_returns_error_on_403(self, mock_post):
        mock_post.return_value.raise_for_status.side_effect = _http_error(403, text_body="Forbidden")
        status, _ = create_lead(SAMPLE_LEAD)
        assert status == RESULT_ERROR

    @patch("app.frappe_service.requests.post")
    def test_returns_error_on_500(self, mock_post):
        mock_post.return_value.raise_for_status.side_effect = _http_error(500, text_body="Server Error")
        status, _ = create_lead(SAMPLE_LEAD)
        assert status == RESULT_ERROR

    @patch("app.frappe_service.requests.post")
    def test_error_message_included_on_422(self, mock_post):
        mock_post.return_value.raise_for_status.side_effect = _http_error(
            422, json_body={"message": "Validation failed"}
        )
        _, msg = create_lead(SAMPLE_LEAD)
        assert "Validation failed" in msg


# ── network errors ────────────────────────────────────────────────────────────

class TestCreateLeadNetworkErrors:

    @patch("app.frappe_service.requests.post")
    def test_returns_error_on_connection_error(self, mock_post):
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection refused")
        status, msg = create_lead(SAMPLE_LEAD)
        assert status == RESULT_ERROR
        assert msg != ""

    @patch("app.frappe_service.requests.post")
    def test_returns_error_on_timeout(self, mock_post):
        mock_post.side_effect = requests.exceptions.Timeout("Timed out")
        status, _ = create_lead(SAMPLE_LEAD)
        assert status == RESULT_ERROR

    @patch("app.frappe_service.requests.post")
    def test_returns_error_on_generic_request_exception(self, mock_post):
        mock_post.side_effect = requests.exceptions.RequestException("Unknown")
        status, _ = create_lead(SAMPLE_LEAD)
        assert status == RESULT_ERROR
