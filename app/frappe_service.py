import requests
from app.config import FRAPPE_URL, FRAPPE_TOKEN

def create_lead(lead):

    headers = {
        "Authorization": FRAPPE_TOKEN,
        "Content-Type": "application/json"
    }

    requests.post(
        f"{FRAPPE_URL}/api/resource/Lead",
        json=lead,
        headers=headers
    )
