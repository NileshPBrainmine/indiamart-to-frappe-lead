import requests
from app.config import INDIAMART_API, INDIAMART_KEY

def fetch_leads():

    params = {
        "glusr_crm_key": INDIAMART_KEY
    }

    response = requests.get(INDIAMART_API, params=params)

    data = response.json()

    return data.get("RESPONSE", [])
