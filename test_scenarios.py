import urllib.request
import urllib.error
import json

url = "http://127.0.0.1:8000/analyze-ticket"

scenarios = [
    {
        "name": "Scenario 1: Wrong Transfer (Bangla/Banglish)",
        "payload": {
            "ticket_id": "TCK-5001",
            "complaint": "bhai ami vul kore 01811223344 a 1200 taka send korsi. help me.",
            "language": "Banglish",
            "channel": "whatsapp",
            "user_type": "retail_customer",
            "campaign_context": "none",
            "transaction_history": [
                {
                    "transaction_id": "TXN-1200",
                    "timestamp": "2026-06-26T14:00:00Z",
                    "type": "transfer",
                    "amount": 1200.0,
                    "counterparty": "01811223344",
                    "status": "successful"
                }
            ]
        }
    },
    {
        "name": "Scenario 2: Phishing / Social Engineering Scam (Critical Risk)",
        "payload": {
            "ticket_id": "TCK-5002",
            "complaint": "Someone hacked my account and stole 15000 Tk. They called me and asked for my code.",
            "language": "en",
            "channel": "email",
            "user_type": "retail_customer",
            "campaign_context": "none",
            "transaction_history": [
                {
                    "transaction_id": "TXN-9999",
                    "timestamp": "2026-06-26T15:30:00Z",
                    "type": "transfer",
                    "amount": 15000.0,
                    "counterparty": "unknown_wallet",
                    "status": "successful"
                }
            ]
        }
    },
    {
        "name": "Scenario 3: No Matching Transactions (Insufficient Data)",
        "payload": {
            "ticket_id": "TCK-5003",
            "complaint": "I lost 200 taka yesterday during a cashout but I do not see it in my statement.",
            "language": "en",
            "channel": "in_app",
            "user_type": "retail_customer",
            "campaign_context": "none",
            "transaction_history": []  # Empty statement history
        }
    },
    {
        "name": "Scenario 4: Duplicate Payment / Double Debit",
        "payload": {
            "ticket_id": "TCK-5004",
            "complaint": "I paid my electricity bill twice. 2000 taka was deducted two times for reference ELEC-12.",
            "language": "en",
            "channel": "in_app",
            "user_type": "retail_customer",
            "campaign_context": "none",
            "transaction_history": [
                {
                    "transaction_id": "TXN-8801",
                    "timestamp": "2026-06-26T10:00:00Z",
                    "type": "payment",
                    "amount": 2000.0,
                    "counterparty": "ELEC-12",
                    "status": "successful"
                },
                {
                    "transaction_id": "TXN-8802",
                    "timestamp": "2026-06-26T10:01:00Z",
                    "type": "payment",
                    "amount": 2000.0,
                    "counterparty": "ELEC-12",
                    "status": "successful"
                }
            ]
        }
    }
]

for s in scenarios:
    print("\n" + "="*50)
    print(f"RUNNING: {s['name']}")
    print("="*50)
    
    req_data = json.dumps(s['payload']).encode("utf-8")
    req = urllib.request.Request(
        url, 
        data=req_data, 
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode("utf-8"))
            print(f"Case Type:  {result['case_type']}")
            print(f"Severity:   {result['severity']}")
            print(f"Queue:      {result['department']}")
            print(f"Verdict:    {result['evidence_verdict']}")
            print(f"Conf Score: {result['confidence']}")
            print(f"Review Req: {result['human_review_required']}")
            print(f"Reason Codes: {result['reason_codes']}")
            print(f"Agent Action: {result['recommended_next_action']}")
            print(f"Reply Draft:  {result['customer_reply']}")
    except urllib.error.URLError as e:
        print(f"Error testing scenario: {e}")
