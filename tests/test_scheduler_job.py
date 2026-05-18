import pytest
from unittest.mock import patch
from tests.conftest import FULL_LEAD

from jobs.scheduler_job import run


class TestSchedulerRun:

    @patch("jobs.scheduler_job.enqueue_leads")
    @patch("jobs.scheduler_job.fetch_leads", return_value=[FULL_LEAD])
    def test_enqueues_leads_when_found(self, mock_fetch, mock_enqueue):
        run()
        mock_enqueue.assert_called_once_with([FULL_LEAD])

    @patch("jobs.scheduler_job.enqueue_leads")
    @patch("jobs.scheduler_job.fetch_leads", return_value=[])
    def test_skips_enqueue_when_no_leads(self, mock_fetch, mock_enqueue):
        run()
        mock_enqueue.assert_not_called()

    @patch("jobs.scheduler_job.enqueue_leads")
    @patch("jobs.scheduler_job.fetch_leads", return_value=None)
    def test_skips_enqueue_when_fetch_returns_none(self, mock_fetch, mock_enqueue):
        run()
        mock_enqueue.assert_not_called()

    @patch("jobs.scheduler_job.enqueue_leads")
    @patch("jobs.scheduler_job.fetch_leads", return_value=[FULL_LEAD, FULL_LEAD, FULL_LEAD])
    def test_enqueues_all_leads(self, mock_fetch, mock_enqueue):
        run()
        enqueued = mock_enqueue.call_args[0][0]
        assert len(enqueued) == 3

    @patch("jobs.scheduler_job.enqueue_leads")
    @patch("jobs.scheduler_job.fetch_leads", return_value=[FULL_LEAD])
    def test_calls_fetch_exactly_once(self, mock_fetch, mock_enqueue):
        run()
        mock_fetch.assert_called_once()
