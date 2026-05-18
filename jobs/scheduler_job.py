from dotenv import load_dotenv
from app.indiamart_service import fetch_leads
from jobs.queue_worker import enqueue_leads
from utils.logger import logger

load_dotenv()


def run():
    logger.info("Fetching leads from IndiaMart...")
    leads = fetch_leads()

    if not leads:
        logger.info("No new leads from IndiaMart.")
        return

    enqueue_leads(leads)


if __name__ == "__main__":
    run()
