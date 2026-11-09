"""Usage (server running; from the project root):  python scripts\check_agent.py"""

import requests

BASE = "http://localhost:8000/api"
created = requests.post(f"{BASE}/applications", json={"language": "kn", "consent_given": True}).json()
headers = {"Authorization": f"Bearer {created['session_token']}"}

TURNS = [
    ("voice", "ನನ್ನ ಹೆಸರು ಲಕ್ಷ್ಮಿ ಹೆಗಡೆ, ಹುಟ್ಟಿದ ದಿನಾಂಕ 14 May 2003"),   # read-back expected
    ("voice", "ಹೌದು"),                                                       # confirm
    ("text", "ಮೊಬೈಲ್ ನಂಬರ್ ಅಂದರೆ ಏನು?"),                                    # help
    ("text", "ನನ್ನ ಮೊಬೈಲ್ ನಂಬರ್ 12345"),                                      # rejected
    ("text", "my mobile number is 9876543210"),                                # saved
    ("voice", "my PAN is A B C P E 1 2 3 4 F"),                                # read-back, then:
    ("voice", "no"),                                                           # discarded
]

for source, text in TURNS:
    r = requests.post(f"{BASE}/conversation/turn", headers=headers, json={"text": text, "source": source})
    if not r.ok:
        print(f"\n[{source}] {text}\n  ERROR {r.status_code}: {r.text}")
        break
    body = r.json()
    progress = body["application"]["progress"]
    print(f"\n[{source}] {text}")
    print(f"  intent: {body['intent']} (by {body['understood_by']})")
    print(f"  reply:  {body['reply']}")
    if body["saved"]:
        print("  saved:  ", [(f['field_id'], f['value']) for f in body['saved']])
    if body["pending_confirmation"]:
        print("  pending:", [(f['field_id'], f['value']) for f in body['pending_confirmation']])
    if body["rejected"]:
        print("  rejected:", [f['field_id'] for f in body['rejected']])
    print(f"  progress: {progress['answered_required']}/{progress['total_required']}, next field: {body['next_field']}")