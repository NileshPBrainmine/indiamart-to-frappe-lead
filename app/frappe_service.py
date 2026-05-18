import requests
from app.config import FRAPPE_URL, FRAPPE_TOKEN
from utils.logger import logger

RESULT_SUCCESS = "success"
RESULT_DUPLICATE = "duplicate_email"
RESULT_ERROR = "error"


def _is_duplicate_email_error(response) -> bool:
    if response is None:
        return False
    if response.status_code == 409:
        return True
    try:
        body = response.json()
        # Frappe puts the exception class name in exc_type or inside exc (traceback string)
        combined = " ".join([
            str(body.get("exc_type") or ""),
            str(body.get("message") or ""),
            str(body.get("exc") or ""),
        ]).lower()
    except (ValueError, AttributeError):
        combined = (response.text or "").lower()

    return any(kw in combined for kw in (
        "duplicateentryerror",
        "duplicate entry",
        "already exists",
    ))


def create_lead(lead):
    headers = {
        "Authorization": FRAPPE_TOKEN,
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            f"{FRAPPE_URL}/api/resource/Lead",
            json=lead,
            headers=headers,
        )
        response.raise_for_status()
        return RESULT_SUCCESS, "Lead created successfully"

    except requests.exceptions.HTTPError as e:
        error_msg = str(e)
        if e.response is not None:
            try:
                error_msg += " - " + str(e.response.json())
            except ValueError:
                error_msg += " - " + e.response.text

        if _is_duplicate_email_error(e.response):
            logger.warning(f"Duplicate email in Frappe for {lead.get('email_id')}: {error_msg}")
            return RESULT_DUPLICATE, error_msg

        logger.error(f"Error creating lead for {lead.get('email_id')}: {error_msg}")
        return RESULT_ERROR, error_msg

    except requests.exceptions.RequestException as e:
        error_msg = str(e)
        logger.error(f"Error creating lead for {lead.get('email_id')}: {error_msg}")
        return RESULT_ERROR, error_msg
