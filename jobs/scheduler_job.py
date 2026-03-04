from app.indiamart_service import fetch_leads
from app.lead_processor import process_lead

def run():

    leads = fetch_leads()

    for lead in leads:
        process_lead(lead)

if __name__ == "__main__":
    run()
