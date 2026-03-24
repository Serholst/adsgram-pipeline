#!/usr/bin/env python3
"""
Gmail Draft Creator for AdsGram Pipeline.

Creates Gmail drafts from a JSON batch file. Does NOT send emails.

Usage:
    # Single draft:
    python create_drafts.py --to "user@example.com" --subject "Hello" --body "Message"

    # Batch mode (preferred):
    python create_drafts.py --batch-file drafts.json

    # First-time auth (run manually in terminal with browser access):
    python create_drafts.py --auth-only

Batch JSON format:
[
    {
        "to": "user@example.com",
        "subject": "Subject line",
        "body": "Email body text",
        "lead_name": "John Doe"
    }
]

Requirements:
    pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
"""

import argparse
import base64
import json
import os
import sys
from email.mime.text import MIMEText
from pathlib import Path

SCOPES = ["https://www.googleapis.com/auth/gmail.compose"]

# Credentials paths
SCRIPT_DIR = Path(__file__).parent
CREDENTIALS_PATH = Path.home() / "Documents" / "ai_data" / "gmail_credentials.json"
TOKEN_PATH = SCRIPT_DIR / "token.json"


def get_gmail_service():
    """Authenticate and return Gmail API service."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = None

    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None

        if not creds:
            if not CREDENTIALS_PATH.exists():
                print(json.dumps({
                    "status": "blocked",
                    "error": f"OAuth2 credentials not found at {CREDENTIALS_PATH}. "
                             f"Download from Google Cloud Console → APIs & Services → Credentials → "
                             f"OAuth 2.0 Client IDs → Download JSON → save as {CREDENTIALS_PATH}"
                }))
                sys.exit(1)

            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_PATH), SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open(TOKEN_PATH, "w") as token:
            token.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def create_draft(service, to: str, subject: str, body: str, sender: str = "me") -> dict:
    """Create a single Gmail draft. Returns draft metadata."""
    message = MIMEText(body, "plain", "utf-8")
    message["to"] = to
    message["subject"] = subject

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

    draft_body = {"message": {"raw": raw}}

    try:
        draft = service.users().drafts().create(
            userId=sender, body=draft_body
        ).execute()

        return {
            "status": "created",
            "draft_id": draft["id"],
            "message_id": draft["message"]["id"],
            "to": to,
            "subject": subject,
        }
    except Exception as e:
        return {
            "status": "error",
            "to": to,
            "subject": subject,
            "error": str(e),
        }


def process_batch(batch_file: str) -> dict:
    """Process a batch of drafts from a JSON file."""
    with open(batch_file, "r", encoding="utf-8") as f:
        pitches = json.load(f)

    if not pitches:
        return {"status": "blocked", "error": "Empty batch file"}

    service = get_gmail_service()

    results = []
    created = 0
    errors = 0

    for pitch in pitches:
        to = pitch.get("to")
        subject = pitch.get("subject")
        body = pitch.get("body")
        lead_name = pitch.get("lead_name", "Unknown")

        if not to or not subject or not body:
            results.append({
                "status": "error",
                "lead_name": lead_name,
                "error": "Missing required field (to, subject, or body)",
            })
            errors += 1
            continue

        result = create_draft(service, to, subject, body)
        result["lead_name"] = lead_name
        results.append(result)

        if result["status"] == "created":
            created += 1
        else:
            errors += 1

    status = "success" if errors == 0 else "partial" if created > 0 else "blocked"

    return {
        "status": status,
        "drafts_created": created,
        "drafts_failed": errors,
        "total": len(pitches),
        "results": results,
    }


def process_single(to: str, subject: str, body: str) -> dict:
    """Create a single draft."""
    service = get_gmail_service()
    result = create_draft(service, to, subject, body)
    result["lead_name"] = to
    status = "success" if result["status"] == "created" else "blocked"
    return {
        "status": status,
        "drafts_created": 1 if status == "success" else 0,
        "drafts_failed": 0 if status == "success" else 1,
        "total": 1,
        "results": [result],
    }


def main():
    parser = argparse.ArgumentParser(description="Create Gmail drafts for AdsGram outreach")
    parser.add_argument("--batch-file", help="Path to JSON file with batch of pitches")
    parser.add_argument("--to", help="Recipient email (single mode)")
    parser.add_argument("--subject", help="Email subject (single mode)")
    parser.add_argument("--body", help="Email body (single mode)")
    parser.add_argument("--auth-only", action="store_true", help="Only run auth flow, don't create drafts")

    args = parser.parse_args()

    if args.auth_only:
        service = get_gmail_service()
        profile = service.users().getProfile(userId="me").execute()
        print(json.dumps({
            "status": "success",
            "message": "Authentication successful",
            "email": profile.get("emailAddress"),
        }, indent=2))
        return

    if args.batch_file:
        result = process_batch(args.batch_file)
    elif args.to and args.subject and args.body:
        result = process_single(args.to, args.subject, args.body)
    else:
        parser.print_help()
        sys.exit(1)

    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(0 if result["status"] in ("success", "partial") else 1)


if __name__ == "__main__":
    main()
