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


def _called_url(mock_get):
    return mock_get.call_args[0][0]


class TestFetchLeads:

    @patch("app.indiamart_service.requests.get")
    def test_returns_leads_on_success(self, mock_get):
        mock_get.return_value = _mock_response({"RESPONSE": SAMPLE_LEADS})
        assert fetch_leads() == SAMPLE_LEADS

    @patch("app.indiamart_service.requests.get")
    def test_returns_multiple_leads(self, mock_get):
        mock_get.return_value = _mock_response({"RESPONSE": SAMPLE_LEADS * 3})
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
    def test_returns_empty_on_http_429(self, mock_get):
        mock_get.return_value = _mock_response({}, status_code=429)
        assert fetch_leads() == []

    @patch("app.indiamart_service.requests.get")
    def test_returns_empty_on_500_error(self, mock_get):
        mock_get.return_value = _mock_response({}, status_code=500)
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
    def test_api_key_is_in_url(self, mock_get):
        mock_get.return_value = _mock_response({"RESPONSE": []})
        with patch("app.indiamart_service.INDIAMART_KEY", "MY_KEY"):
            fetch_leads()
        assert "glusr_crm_key=MY_KEY" in _called_url(mock_get)

    @patch("app.indiamart_service.requests.get")
    def test_time_params_are_in_url(self, mock_get):
        mock_get.return_value = _mock_response({"RESPONSE": []})
        fetch_leads()
        url = _called_url(mock_get)
        assert "start_time=" in url
        assert "end_time=" in url

    @patch("app.indiamart_service.requests.get")
    def test_url_contains_no_encoded_colons(self, mock_get):
        # IndiaMart rejects %3A — colons must be sent raw
        mock_get.return_value = _mock_response({"RESPONSE": []})
        fetch_leads()
        assert "%3A" not in _called_url(mock_get)
        assert "%3a" not in _called_url(mock_get)

    @patch("app.indiamart_service.requests.get")
    def test_time_format_is_dd_mm_yyyy_hh_mm_ss(self, mock_get):
        mock_get.return_value = _mock_response({"RESPONSE": []})
        fetch_leads()
        url = _called_url(mock_get)
        # e.g. start_time=20-05-2026%2010:30:00
        fmt = r"start_time=\d{2}-\d{2}-\d{4}(?:%20| )\d{2}:\d{2}:\d{2}"
        assert re.search(fmt, url), f"Time format wrong in URL: {url}"

    @patch("app.indiamart_service.requests.get")
    def test_end_time_is_after_start_time(self, mock_get):
        mock_get.return_value = _mock_response({"RESPONSE": []})
        fetch_leads()
        url = _called_url(mock_get)
        start = re.search(r"start_time=([^&]+)", url).group(1).replace("%20", " ")
        end   = re.search(r"end_time=([^&]+)", url).group(1).replace("%20", " ")
        assert end > start

    @patch("app.indiamart_service.requests.get")
    def test_uses_30_second_timeout(self, mock_get):
        mock_get.return_value = _mock_response({"RESPONSE": []})
        fetch_leads()
        assert mock_get.call_args[1]["timeout"] == 30
