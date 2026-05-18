import json
from app.frappe_service import create_lead, RESULT_SUCCESS, RESULT_DUPLICATE
from utils.helpers import save_failed_lead, save_duplicate_lead, is_duplicate, mark_seen
from utils.logger import logger


def process_lead(data):
    lead_id = str(data.get("UNIQUE_QUERY_ID") or "")
    if not lead_id:
        lead_id = f"{data.get('SENDER_MOBILE','')}_{data.get('SENDER_EMAIL','')}"

    if is_duplicate(lead_id):
        logger.info(f"Skipping duplicate lead: {lead_id}")
        return

    logger.info(f"Raw received data: {json.dumps(data)}")

    city = data.get("SENDER_CITY", "")
    state = data.get("SENDER_STATE", "")

    query_about = (
        data.get("QUERY_MESSAGE")
        or data.get("QUERY_PRODUCT_NAME")
        or data.get("QUERY_MCAT_NAME")
        or ""
    )

    lead = {
        "first_name": data.get("SENDER_NAME"),
        "phone": data.get("SENDER_MOBILE"),
        "email_id": data.get("SENDER_EMAIL"),
        "company_name": data.get("SENDER_COMPANY"),
        "city": city,
        "custom_state": state,
        "custom_address": f"{city}, {state}".strip(", "),
        "query_about": query_about,
        "status": "Open",
        "source": "Indiamart",
    }

    logger.info(f"Converted Frappe payload: {json.dumps(lead)}")

    result, message = create_lead(lead)

    if result == RESULT_SUCCESS:
        mark_seen(lead_id)
        logger.info(f"Lead created: {lead.get('email_id')}")

    elif result == RESULT_DUPLICATE:
        mark_seen(lead_id)  # prevent retrying a lead Frappe will always reject
        save_duplicate_lead(data, message)
        logger.warning(f"Duplicate email in Frappe, saved to duplicate_leads.jsonl: {lead.get('email_id')}")

    else:
        save_failed_lead(data, message)
        logger.warning(f"Failed to post lead: {lead.get('email_id')}. Reason: {message}. Will retry next cycle.")
