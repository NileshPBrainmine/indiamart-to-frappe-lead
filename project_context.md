# IndiaMart to Frappe Lead Ingestion System

## Project Context

This document provides the complete source code and structure for the Python lead ingestion system. The system fetches leads from IndiaMart, processes them sequentially, and robustly handles duplicate email errors from Frappe by logging failing leads to a separate file so no data is lost.

### Folder Structure

```
IndiaMart to Frappe/
├── app/
│   ├── config.py
│   ├── frappe_service.py
│   ├── indiamart_service.py
│   ├── lead_processor.py
│   └── main.py
├── jobs/
│   └── scheduler_job.py
├── logs/
│   ├── app.log
│   └── failed_leads.jsonl
├── utils/
│   ├── helpers.py
│   └── logger.py
├── .env
├── README.md
└── requirements.txt
```

---

### Source Code

#### `app/config.py`

```python
import os

INDIAMART_API = "https://mapi.indiamart.com/wservce/crm/crmListing/v2/"
INDIAMART_KEY = os.getenv("INDIAMART_KEY")

FRAPPE_URL = os.getenv("FRAPPE_URL")
FRAPPE_TOKEN = os.getenv("FRAPPE_TOKEN")
```

#### `app/indiamart_service.py`

```python
import requests
from app.config import INDIAMART_API, INDIAMART_KEY

def fetch_leads():

    params = {
        "glusr_crm_key": INDIAMART_KEY
    }

    response = requests.get(INDIAMART_API, params=params)

    data = response.json()

    return data.get("RESPONSE", [])
```

#### `app/frappe_service.py`

```python
import requests
from app.config import FRAPPE_URL, FRAPPE_TOKEN
from utils.logger import logger

def create_lead(lead):

    headers = {
        "Authorization": FRAPPE_TOKEN,
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(
            f"{FRAPPE_URL}/api/resource/Lead",
            json=lead,
            headers=headers
        )
        response.raise_for_status()
        return True, "Lead created successfully"
    except requests.exceptions.RequestException as e:
        error_msg = str(e)
        if e.response is not None:
            try:
                error_msg += " - " + str(e.response.json())
            except ValueError:
                error_msg += " - " + e.response.text
        logger.error(f"Error creating lead for {lead.get('email_id')}: {error_msg}")
        return False, error_msg
```

#### `app/lead_processor.py`

```python
from app.frappe_service import create_lead
from utils.helpers import save_failed_lead
from utils.logger import logger

def process_lead(data):

    lead = {
        "first_name": data.get("SENDER_NAME"),
        "phone": data.get("SENDER_MOBILE"),
        "email_id": data.get("SENDER_EMAIL"),
        "company_name": data.get("SENDER_COMPANY"),
        "city": data.get("SENDER_CITY"),
        "source": "Indiamart"
    }

    logger.info(f"Processing lead for email: {lead.get('email_id')}")
    success, message = create_lead(lead)

    if not success:
        logger.warning(f"Failed to post lead: {lead.get('email_id')}. Saving to failed log.")
        save_failed_lead(data, message)
```

#### `app/main.py`

```python
def main():
    print("Lead ingestion system initialized. Run jobs/scheduler_job.py to start.")

if __name__ == "__main__":
    main()
```

#### `jobs/scheduler_job.py`

```python
import time
from app.indiamart_service import fetch_leads
from app.lead_processor import process_lead
from utils.logger import logger

def run():
    logger.info("Scheduler job started. Fetching leads...")
    leads = fetch_leads()

    if not leads:
        logger.info("No leads found from IndiaMart.")
        return

    logger.info(f"Fetched {len(leads)} leads. Processing sequentially in a queue...")

    for index, lead in enumerate(leads, start=1):
        logger.info(f"Processing lead {index}/{len(leads)}")
        process_lead(lead)
        # Add a sleep to prevent overwhelming the Frappe API and process as a sequence.
        time.sleep(1)

    logger.info("Scheduler job completed processing all leads.")

if __name__ == "__main__":
    run()
```

#### `utils/logger.py`

```python
import logging
import os

log_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/logs'
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'app.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
```

#### `utils/helpers.py`

```python
import os
import json
from datetime import datetime

def save_failed_lead(lead_data, error_message):
    log_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/logs'
    os.makedirs(log_dir, exist_ok=True)
    file_path = os.path.join(log_dir, 'failed_leads.jsonl')

    record = {
        "timestamp": datetime.now().isoformat(),
        "error": error_message,
        "lead_data": lead_data
    }

    with open(file_path, 'a') as f:
        f.write(json.dumps(record) + '\n')
```

#### `requirements.txt`

```text
requests
python-dotenv
```

#### `.env`

```env
INDIAMART_KEY=your_key
FRAPPE_URL=https://brainmineai.in
FRAPPE_TOKEN=token API_KEY:API_SECRET
```

#### `README.md`

```markdown
# Lead Ingestion System

This is a lead ingestion system to fetch leads from IndiaMart and create them in Frappe.

## Setup

1. Install requirements:
   `pip install -r requirements.txt`

2. Setup `.env` file with accurate keys:
```

INDIAMART_KEY=your_key
FRAPPE_URL=https://brainmineai.in
FRAPPE_TOKEN=token API_KEY:API_SECRET

```

3. Run the scheduler:
`python3 jobs/scheduler_job.py`

## Automation (cron)
Open crontab:
`crontab -e`

Add the following job to run every 5 minutes:
`*/5 * * * * python3 /path/to/lead_ingestion_system/jobs/scheduler_job.py`
```
