import time
import threading
import queue
from app.lead_processor import process_lead
from utils.logger import logger

lead_queue = queue.Queue()
_stop_event = threading.Event()


def worker():
    logger.info("Lead queue worker started.")
    while not _stop_event.is_set():
        try:
            lead = lead_queue.get(timeout=2)
        except queue.Empty:
            continue

        try:
            process_lead(lead)
        except Exception as e:
            logger.error(f"Unexpected error processing lead: {e}")
        finally:
            lead_queue.task_done()
            time.sleep(1)  # 1s gap between Frappe POSTs

    logger.info("Lead queue worker stopped.")


def start_worker():
    t = threading.Thread(target=worker, name="lead-worker", daemon=True)
    t.start()
    return t


def stop_worker():
    _stop_event.set()


def enqueue_leads(leads):
    for lead in leads:
        lead_queue.put(lead)
    if leads:
        logger.info(f"Enqueued {len(leads)} lead(s). Queue size: {lead_queue.qsize()}")
