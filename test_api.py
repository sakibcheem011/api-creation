import urllib.request
import urllib.error
import json

# Target local server endpoint
url = "https://novaforge-investigator-api.onrender.com/analyze-ticket"

# Sample complaint request body
payload = {
    "ticket_id": "TCK-4001",
    "complaint": "I sent 500 Tk to agent point 01711223344 but it failed and the money got cut.",
    "language": "Banglish",
    "channel": "in_app",
    "user_type": "retail_customer",
    "campaign_context": "none",
    "transaction_history": [
        {
            "transaction_id": "TXN-7766",
            "timestamp": "2026-06-26T12:00:00Z",
            "type": "cash_in",
            "amount": 500.0,
            "counterparty": "01711223344",
            "status": "failed"
        }
    ]
}

# Encode headers and body
req_data = json.dumps(payload).encode("utf-8")
req = urllib.request.Request(
    url, 
    data=req_data, 
    headers={"Content-Type": "application/json", "Accept": "application/json"},
    method="POST"
)

print("--- SENDING COMPLAINT ---")
print(f"Complaint: \"{payload['complaint']}\"")
print(f"Checking transaction amount: {payload['transaction_history'][0]['amount']} to {payload['transaction_history'][0]['counterparty']}\n")

try:
    with urllib.request.urlopen(req) as response:
        status_code = response.getcode()
        body = response.read().decode("utf-8")
        result = json.loads(body)
        
        print(f"--- API RESPONSE (Status: {status_code}) ---")
        print(json.dumps(result, indent=2))
        
except urllib.error.URLError as e:
    print("--- CONNECTION ERROR ---")
    print(f"Could not connect to the local API server. Is it running? Details: {e}")
