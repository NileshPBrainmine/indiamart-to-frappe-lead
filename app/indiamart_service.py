import requests
from datetime import datetime, timedelta
from app.config import INDIAMART_API, INDIAMART_KEY
from utils.logger import logger

NO_LEADS_MSG = "There are no leads in the given time duration. Please try for a different duration."
RATE_LIMIT_MSG = "It is advised to hit this API once in every 5 minutes,but it seems that you have crossed this limit. Please try again after 5 minutes."

def fetch_leads():
    now = datetime.now()
    start_time = (now - timedelta(minutes=5)).strftime("%d-%m-%Y %H:%M:%S")
    end_time = now.strftime("%d-%m-%Y %H:%M:%S")

    # Build URL manually — requests encodes colons as %3A which IndiaMart rejects
    url = (
        f"{INDIAMART_API}"
        f"?glusr_crm_key={INDIAMART_KEY}"
        f"&start_time={start_time.replace(' ', '%20')}"
        f"&end_time={end_time.replace(' ', '%20')}"
    )

    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 429:
            logger.warning("IndiaMart rate limit hit (429). Skipping this cycle.")
            return []
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"IndiaMart API request failed: {e}")
        return []

    message = data.get("MESSAGE", "")
    if message in (NO_LEADS_MSG, RATE_LIMIT_MSG):
        logger.info(f"IndiaMart: {message}")
        return []

    leads = data.get("RESPONSE", [])
    logger.info(f"IndiaMart returned {len(leads)} lead(s) for window {start_time} → {end_time}")
    return leads
