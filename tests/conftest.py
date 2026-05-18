import os
import pytest

# Provide dummy env vars before any app module is imported
os.environ.setdefault("INDIAMART_KEY", "TEST_INDIAMART_KEY")
os.environ.setdefault("FRAPPE_URL", "https://test.frappe.io")
os.environ.setdefault("FRAPPE_TOKEN", "token test_key:test_secret")


FULL_LEAD = {
    "UNIQUE_QUERY_ID": "QID001",
    "SENDER_NAME": "Alice",
    "SENDER_MOBILE": "9000000001",
    "SENDER_EMAIL": "alice@example.com",
    "SENDER_COMPANY": "Acme Corp",
    "SENDER_CITY": "Mumbai",
    "SENDER_STATE": "Maharashtra",
    "QUERY_MESSAGE": "I need 5 units",
    "QUERY_PRODUCT_NAME": "CNC Machine",
    "QUERY_MCAT_NAME": "Machinery",
}
