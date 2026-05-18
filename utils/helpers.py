import os
import json
from datetime import datetime, timedelta

LOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/logs'
SEEN_LEADS_FILE = os.path.join(LOG_DIR, 'seen_leads.json')
SEEN_LEADS_TTL_HOURS = 24


def _load_seen_leads():
    if not os.path.exists(SEEN_LEADS_FILE):
        return {}
    with open(SEEN_LEADS_FILE, 'r') as f:
        return json.load(f)


def _save_seen_leads(seen):
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(SEEN_LEADS_FILE, 'w') as f:
        json.dump(seen, f)


def is_duplicate(lead_id: str) -> bool:
    seen = _load_seen_leads()
    cutoff = (datetime.now() - timedelta(hours=SEEN_LEADS_TTL_HOURS)).isoformat()
    seen = {k: v for k, v in seen.items() if v >= cutoff}
    _save_seen_leads(seen)
    return lead_id in seen


def mark_seen(lead_id: str):
    seen = _load_seen_leads()
    seen[lead_id] = datetime.now().isoformat()
    _save_seen_leads(seen)


def _append_jsonl(file_path, record):
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(file_path, 'a') as f:
        f.write(json.dumps(record) + '\n')


def save_failed_lead(lead_data, error_message):
    _append_jsonl(
        os.path.join(LOG_DIR, 'failed_leads.jsonl'),
        {
            "timestamp": datetime.now().isoformat(),
            "error": error_message,
            "lead_data": lead_data,
        }
    )


def save_duplicate_lead(lead_data, error_message):
    _append_jsonl(
        os.path.join(LOG_DIR, 'duplicate_leads.jsonl'),
        {
            "timestamp": datetime.now().isoformat(),
            "email_id": lead_data.get("SENDER_EMAIL", ""),
            "error": error_message,
            "lead_data": lead_data,
        }
    )
