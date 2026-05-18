import re
import pytest
import requests
from unittest.mock import patch, MagicMock

from app.indiamart_service import fetch_leads, NO_LEADS_MSG, RATE_LIMIT_MSG

SAMPLE_LEADS = [
    {
        "UNIQUE_QUERY_ID": "QID001",
        "SENDER_NAME": "Alice",
        "SENDER_MOBILE": "9000000001",
        "SENDER_EMAIL": "alice@example.com",
    }
]


def _mock_response(json_data, status_code=200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    if status_code >= 400:
        http_err = requests.exceptions.HTTPError(response=resp)
        http_err.response = resp
        resp.raise_for_status.side_effect = http_err
    else:
        resp.raise_for_status.return_value = None
    return resp


class TestFetchLeads:

    @patch("app.indiamart_service.requests.get")
    def test_returns_leads_on_success(self, mock_get):
        mock_get.return_value = _mock_response({"RESPONSE": SAMPLE_LEADS})
        assert fetch_leads() == SAMPLE_LEADS

    @patch("app.indiamart_service.requests.get")
    def test_returns_multiple_leads(self, mock_get):
        leads = SAMPLE_LEADS * 3
        mock_get.return_value = _mock_response({"RESPONSE": leads})
        assert len(fetch_leads()) == 3

    @patch("app.indiamart_service.requests.get")
    def test_returns_empty_on_no_leads_message(self, mock_get):
        mock_get.return_value = _mock_response({"MESSAGE": NO_LEADS_MSG})
        assert fetch_leads() == []

    @patch("app.indiamart_service.requests.get")
    def test_returns_empty_on_rate_limit_message(self, mock_get):
        mock_get.return_value = _mock_response({"MESSAGE": RATE_LIMIT_MSG})
        assert fetch_leads() == []

    @patch("app.indiamart_service.requests.get")
    def test_returns_empty_when_response_array_is_empty(self, mock_get):
        mock_get.return_value = _mock_response({"RESPONSE": []})
        assert fetch_leads() == []

    @patch("app.indiamart_service.requests.get")
    def test_returns_empty_on_500_error(self, mock_get):
        mock_get.return_value = _mock_response({}, status_code=500)
        assert fetch_leads() == []

    @patch("app.indiamart_service.requests.get")
    def test_returns_empty_on_401_unauthorized(self, mock_get):
        mock_get.return_value = _mock_response({}, status_code=401)
        assert fetch_leads() == []

    @patch("app.indiamart_service.requests.get")
    def test_returns_empty_on_connection_error(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")
        assert fetch_leads() == []

    @patch("app.indiamart_service.requests.get")
    def test_returns_empty_on_timeout(self, mock_get):
        mock_get.side_effect = requests.exceptions.Timeout("Request timed out")
        assert fetch_leads() == []

    @patch("app.indiamart_service.requests.get")
    def test_sends_api_key_in_params(self, mock_get):
        mock_get.return_value = _mock_response({"RESPONSE": []})
        with patch("app.indiamart_service.INDIAMART_KEY", "MY_KEY"):
            fetch_leads()
        params = mock_get.call_args[1]["params"]
        assert params["glusr_crm_key"] == "MY_KEY"

    @patch("app.indiamart_service.requests.get")
    def test_time_params_are_in_correct_format(self, mock_get):
        mock_get.return_value = _mock_response({"RESPONSE": []})
        fetch_leads()
        params = mock_get.call_args[1]["params"]
        fmt = r"^\d{2}-\d{2}-\d{4} \d{2}:\d{2}:\d{2}$"
        assert re.match(fmt, params["start_time"])
        assert re.match(fmt, params["end_time"])

    @patch("app.indiamart_service.requests.get")
    def test_end_time_is_after_start_time(self, mock_get):
        mock_get.return_value = _mock_response({"RESPONSE": []})
        fetch_leads()
        params = mock_get.call_args[1]["params"]
        assert params["end_time"] > params["start_time"]

    @patch("app.indiamart_service.requests.get")
    def test_uses_30_second_timeout(self, mock_get):
        mock_get.return_value = _mock_response({"RESPONSE": []})
        fetch_leads()
        assert mock_get.call_args[1]["timeout"] == 30
