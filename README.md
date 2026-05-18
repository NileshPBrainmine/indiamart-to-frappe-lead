# IndiaMart → Frappe CRM Lead Sync

A lightweight Python service that automatically pulls new leads from the IndiaMart CRM API every minute and creates them as **Lead** records in a Frappe / ERPNext instance.

---

## How It Works

```
Every 1 minute
     │
     ▼
[IndiaMart API]  ── fetch last 5-min window ──▶  [Thread-safe Queue]
                                                          │
                                                          ▼ (worker thread)
                                                   [Duplicate check]
                                                          │ new lead
                                                          ▼
                                                  [Frappe REST API]
                                                   POST /api/resource/Lead
```

- **Scheduler** (main thread) runs every minute, fetches leads, and pushes them into a queue.
- **Worker thread** drains the queue independently, posting each lead to Frappe with a 1-second gap between requests.
- **Deduplication** prevents the same lead from being posted more than once within a 24-hour window.
- **Logs** are written to date-based folders (`logs/YYYY-MM-DD/app.log`) and auto-purged after 7 days.

---

## Project Structure

```
.
├── app/
│   ├── config.py            # Reads env vars
│   ├── indiamart_service.py # Fetches leads from IndiaMart API
│   ├── frappe_service.py    # POSTs leads to Frappe REST API
│   ├── lead_processor.py    # Maps IndiaMart fields → Frappe fields, dedup check
│   └── main.py              # Entry point — starts worker + scheduler
├── jobs/
│   ├── scheduler_job.py     # Fetches and enqueues leads every minute
│   └── queue_worker.py      # Worker thread that processes the queue
├── utils/
│   ├── helpers.py           # Dedup cache, failed lead logger
│   └── logger.py            # Daily rotating file logger
├── logs/                    # Auto-created at runtime
│   ├── YYYY-MM-DD/
│   │   └── app.log
│   ├── seen_leads.json      # Dedup cache (24-hour TTL)
│   └── failed_leads.jsonl   # Failed POST records
├── .env                     # Credentials (never commit this)
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

---

## Prerequisites

- Python 3.11+  **or**  Docker + Docker Compose
- IndiaMart CRM API key (`glusr_crm_key`)
- Frappe / ERPNext instance with API token access

---

## Configuration

Fill in `.env`:

```env
INDIAMART_KEY=your_indiamart_crm_key
FRAPPE_URL=https://your-frappe-instance.com
FRAPPE_TOKEN=token api_key:api_secret
```

| Variable | Description |
|----------|-------------|
| `INDIAMART_KEY` | Your `glusr_crm_key` from IndiaMart CRM settings |
| `FRAPPE_URL` | Base URL of your Frappe instance — no trailing slash |
| `FRAPPE_TOKEN` | Frappe API token in the format `token <key>:<secret>` |

### Getting the Frappe API Token

1. In Frappe go to **Settings → My Account → API Access**
2. Generate an API Key and API Secret
3. Set `FRAPPE_TOKEN=token <api_key>:<api_secret>` in `.env`

---

## Running Locally

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Add credentials to .env

# 3. Start the service
python app/main.py
```

The service fetches leads immediately on startup, then every minute after that.

---

## Running with Docker (Recommended for VPS)

```bash
# Build and start in background
docker compose up -d --build

# View live logs
docker compose logs -f

# Stop
docker compose down
```

The `logs/` folder is mounted as a volume so logs persist across container rebuilds.

---

## Field Mapping

| IndiaMart Field | Frappe Field |
|-----------------|-------------|
| `SENDER_NAME` | `first_name` |
| `SENDER_MOBILE` | `phone` |
| `SENDER_EMAIL` | `email_id` |
| `SENDER_COMPANY` | `company_name` |
| `SENDER_CITY` | `city` |
| `SENDER_STATE` | `custom_state` |
| `SENDER_CITY + SENDER_STATE` | `custom_address` |
| `QUERY_MESSAGE` / `QUERY_PRODUCT_NAME` / `QUERY_MCAT_NAME` | `query_about` (first non-empty) |
| *(hardcoded)* | `status` = `Open` |
| *(hardcoded)* | `source` = `Indiamart` |

---

## Deduplication

The service uses a file-based cache (`logs/seen_leads.json`) to prevent posting the same lead twice.

- **Key**: `UNIQUE_QUERY_ID` from IndiaMart. Falls back to `{phone}_{email}` if not present.
- **TTL**: 24 hours — entries older than this are auto-purged.
- A lead is only marked as seen **after a successful POST** to Frappe, so failed leads are automatically retried on the next cycle.

---

## Log Rotation

Logs rotate at midnight into a new dated folder and old folders are deleted automatically.

```
logs/
  2026-05-12/  app.log   ← auto-deleted after 7 days
  2026-05-13/  app.log
  ...
  2026-05-18/  app.log   ← today (active)
```

- Rotation happens at **midnight** (date change detected on every log write).
- Old folders are also **purged on startup** to clean up after a long downtime.

---

## Failed Leads

If a POST to Frappe fails (network error, auth error, validation error), the raw IndiaMart data is appended to `logs/failed_leads.jsonl`:

```json
{"timestamp": "2026-05-18T15:30:00", "error": "401 Unauthorized", "lead_data": {...}}
```

Each line is a separate JSON record. The lead will be retried automatically on the next fetch cycle since it was never marked as seen.

---

## Deployment on VPS

```bash
# SSH into your VPS
ssh user@your-vps-ip

# Clone the repository
git clone <repo-url> indiamart-frappe
cd indiamart-frappe

# Set credentials
nano .env

# Start service (auto-restarts on crash or reboot)
docker compose up -d --build

# Check it is running
docker compose ps

# Monitor logs
docker compose logs -f
```

To update after a code change:

```bash
git pull
docker compose up -d --build
```

---

## Troubleshooting

| Symptom | Check |
|---------|-------|
| No leads being created | Check `logs/YYYY-MM-DD/app.log` for IndiaMart API errors or "no leads" messages |
| `401 Unauthorized` from Frappe | Verify `FRAPPE_TOKEN` format — must be `token key:secret` with a space after `token` |
| Leads created as duplicates | Check `logs/seen_leads.json` exists and is writable |
| Container keeps restarting | Run `docker compose logs` to see the startup error |
| Old log folders not deleted | Logs are only purged on startup and at midnight rollover — restart the container |
