from app.frappe_service import create_lead

def process_lead(data):

    lead = {
        "first_name": data.get("SENDER_NAME"),
        "phone": data.get("SENDER_MOBILE"),
        "email_id": data.get("SENDER_EMAIL"),
        "company_name": data.get("SENDER_COMPANY"),
        "city": data.get("SENDER_CITY"),
        "source": "Indiamart"
    }

    create_lead(lead)
