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
