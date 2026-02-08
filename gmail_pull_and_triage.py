import os
import base64
import json
from email import message_from_bytes
import csv
from pathlib import Path

import requests
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

TRIAGE_API_URL = "http://localhost:8000/triage-email"

LOG_PATH = Path("triage_log.csv")


def get_gmail_service():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    service = build("gmail", "v1", credentials=creds)
    return service


def get_message_detail(service, msg_id):
    msg = (
        service.users()
        .messages()
        .get(userId="me", id=msg_id, format="full")
        .execute()
    )

    headers = msg.get("payload", {}).get("headers", [])
    subject = next(
        (h["value"] for h in headers if h["name"].lower() == "subject"), ""
    )
    sender = next(
        (h["value"] for h in headers if h["name"].lower() == "from"), ""
    )

    body_text = extract_body_text(msg)

    return {
        "sender": sender,
        "recipient": "me",      # or your actual address if you want
        "subject": subject,
        "body": body_text,
    }


def extract_body_text(msg):
    payload = msg.get("payload", {})
    data = None

    if "parts" in payload:
        for part in payload["parts"]:
            if part.get("mimeType") == "text/plain":
                data = part.get("body", {}).get("data")
                if data:
                    break
    else:
        data = payload.get("body", {}).get("data")

    if not data:
        return ""

    decoded_bytes = base64.urlsafe_b64decode(data.encode("UTF-8"))
    try:
        return decoded_bytes.decode("UTF-8", errors="ignore")
    except Exception:
        return ""


def triage_via_api(details: dict) -> dict:
    print("\n--- PAYLOAD TO TRIAGE API ---")
    print(json.dumps(details, indent=2))
    resp = requests.post(TRIAGE_API_URL, json=details)
    resp.raise_for_status()
    return resp.json()



def describe_planned_action(triage: dict) -> dict:
    action = triage.get("suggested_action")
    labels = triage.get("labels", [])
    category = triage.get("category")
    confidence = triage.get("confidence", 0.0)

    if action == "label_only" and "NEWSLETTER" in labels:
        plan = "Apply label [NEWSLETTER] and consider archiving."
    elif action == "needs_reply":
        plan = "Add to reply queue (manual follow-up needed)."
    elif action == "needs_forward":
        plan = "Forward to the appropriate team/address."
    else:
        plan = "No automatic action, leave as is for now."

    return {
        "plan": plan,
        "action": action,
        "labels": labels,
        "category": category,
        "confidence": confidence,
    }

def append_log(message_id: str, details: dict, triage: dict):
    row = {
        "message_id": message_id,
        "sender": details.get("sender", ""),
        "recipient": details.get("recipient", ""),
        "subject": details.get("subject", ""),
        "category": triage.get("category", ""),
        "suggested_action": triage.get("suggested_action", ""),
        "confidence": triage.get("confidence", ""),
        "labels": ",".join(triage.get("labels", [])),
    }

    file_exists = LOG_PATH.exists()
    with LOG_PATH.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "message_id",
                "sender",
                "recipient",
                "subject",
                "category",
                "suggested_action",
                "confidence",
                "labels",
            ],
        )
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def main():
    service = get_gmail_service()

    seen_ids = set()
    if LOG_PATH.exists():
        with LOG_PATH.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                seen_ids.add(row.get("message_id"))

    results = (
        service.users()
        .messages()
        .list(userId="me", labelIds=["INBOX"], maxResults=1)
        .execute()
    )
    messages = results.get("messages", [])

    if not messages:
        print("No messages found.")
        return

    for m in messages:
        msg_id = m["id"]
        if msg_id in seen_ids:
            continue
        
        details = get_message_detail(service, msg_id)

        print("\n=== EMAIL ===")
        print(f"From: {details.get('sender', '(no sender)')}")
        print(f"Subject: {details.get('subject', '(no subject)')}")
        print("-" * 40)

        triage = triage_via_api(details)

        # Log to CSV
        append_log(msg_id, details, triage)

        print("=== TRIAGE RAW ===")
        print(json.dumps(triage, indent=2))

        summary = describe_planned_action(triage)

        print("\n=== TRIAGE SUMMARY ===")
        print(f"Category: {summary['category']}")
        print(f"Suggested action: {summary['action']}")
        print(f"Labels: {summary['labels']}")
        print(f"Confidence: {summary['confidence']:.2f}")
        print(f"Planned action: {summary['plan']}")
        print("=" * 60)


if __name__ == "__main__":
    main()
