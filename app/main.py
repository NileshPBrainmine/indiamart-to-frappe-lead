import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import signal
import schedule
from dotenv import load_dotenv
from jobs.scheduler_job import run
from jobs.queue_worker import start_worker, stop_worker
from utils.logger import logger

load_dotenv()


def main():
    logger.info("Lead ingestion system starting...")
    start_worker()

    run()  # fetch immediately on startup
    schedule.every(5).minutes.do(run)

    def shutdown(signum, frame):
        logger.info("Shutdown signal received. Stopping...")
        stop_worker()
        raise SystemExit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    while True:
        schedule.run_pending()
        time.sleep(10)


if __name__ == "__main__":
    main()
