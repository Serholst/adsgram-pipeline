#!/usr/bin/env python3
"""
Data-validation script for AdsGram Pipeline.

Checks:
  1. Leads ↔ Top iGaming Operators company cross-reference
  2. Missing critical fields in Leads (Email, Vertical)
  3. Placeholder / fake emails in Leads
  4. Duplicate emails in Leads
  5. Gmail SENT ↔ Leads email cross-reference (optional, requires --gmail)

Exit codes:
  0 — all checks passed
  1 — warnings found (non-blocking)
  2 — critical issues found

Usage:
    python3 tools/validate_data.py               # Sheets-only checks
    python3 tools/validate_data.py --gmail        # + Gmail sent audit
    python3 tools/validate_data.py --json         # machine-readable output
"""

import argparse
import json
import os
import sys
from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials

# ---------------------------------------------------------------------------
# Paths & config
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
ENV_PATH = PROJECT_DIR / ".env"

SHEETS_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

GMAIL_TOKEN_PATH = PROJECT_DIR / "skills" / "gmail-drafter" / "token.json"
GMAIL_CREDS_PATH = PROJECT_DIR / "gmail_credentials.json"

PLACEHOLDER_PATTERNS = [
    "(apollo has_email)",
    "has_email",
    "none",
    "n/a",
    "",
]


# ---------------------------------------------------------------------------
# Env loader (no external deps)
# ---------------------------------------------------------------------------

def _load_env():
    if not ENV_PATH.exists():
        return
    for line in ENV_PATH.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


_load_env()

CREDENTIALS_PATH = os.environ.get("GOOGLE_CREDENTIALS_PATH", "./credentials.json")
CRM_SHEET_ID = os.environ.get("CRM_SHEET_ID", "")
COMPANYDB_SHEET_ID = os.environ.get("COMPANYDB_SHEET_ID", "")


# ---------------------------------------------------------------------------
# Google Sheets helpers
# ---------------------------------------------------------------------------

def get_sheets_client() -> gspread.Client:
    creds_path = CREDENTIALS_PATH
    if not Path(creds_path).is_absolute():
        creds_path = str(PROJECT_DIR / creds_path)
    creds = Credentials.from_service_account_file(creds_path, scopes=SHEETS_SCOPES)
    return gspread.authorize(creds)


def read_sheet(gc, sheet_id: str, tab: str) -> list[dict]:
    ss = gc.open_by_key(sheet_id)
    ws = ss.worksheet(tab)
    all_values = ws.get_all_values()
    if not all_values:
        return []
    headers = all_values[0]
    # Deduplicate empty/blank headers by appending index
    seen = {}
    clean_headers = []
    for i, h in enumerate(headers):
        h = h.strip()
        if not h:
            h = f"_col_{i}"
        if h in seen:
            seen[h] += 1
            h = f"{h}_{seen[h]}"
        else:
            seen[h] = 0
        clean_headers.append(h)
    records = []
    for row in all_values[1:]:
        record = {}
        for j, header in enumerate(clean_headers):
            record[header] = row[j] if j < len(row) else ""
        records.append(record)
    return records


# ---------------------------------------------------------------------------
# Gmail helper
# ---------------------------------------------------------------------------

def get_gmail_sent_emails() -> list[dict]:
    """Return list of {to, subject, date} from SENT folder."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials as OAuthCreds
    from googleapiclient.discovery import build

    if not GMAIL_TOKEN_PATH.exists():
        return []

    token_data = json.loads(GMAIL_TOKEN_PATH.read_text())
    creds = OAuthCreds(
        token=token_data.get("token"),
        refresh_token=token_data.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=token_data.get("client_id"),
        client_secret=token_data.get("client_secret"),
        scopes=token_data.get("scopes", GMAIL_SCOPES),
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())

    service = build("gmail", "v1", credentials=creds, cache_discovery=False)

    sent = []
    page_token = None
    while True:
        resp = service.users().messages().list(
            userId="me", labelIds=["SENT"], maxResults=200, pageToken=page_token
        ).execute()
        messages = resp.get("messages", [])
        for msg_stub in messages:
            msg = service.users().messages().get(
                userId="me", id=msg_stub["id"], format="metadata",
                metadataHeaders=["To", "Subject", "Date"],
            ).execute()
            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
            to_raw = headers.get("To", "")
            # Extract email from "Name <email>" format
            if "<" in to_raw and ">" in to_raw:
                email = to_raw.split("<")[1].split(">")[0].strip().lower()
            else:
                email = to_raw.strip().lower()
            sent.append({
                "to": email,
                "subject": headers.get("Subject", ""),
                "date": headers.get("Date", ""),
            })
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    return sent


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def check_sheets(gc) -> dict:
    """Run all Sheets-based validation checks."""
    leads = read_sheet(gc, CRM_SHEET_ID, "Leads")
    operators = read_sheet(gc, COMPANYDB_SHEET_ID, "Top iGaming Operators")

    lead_companies = {str(r.get("Company", "")).strip().lower() for r in leads if r.get("Company")}
    op_companies = {str(r.get("Company", "")).strip().lower() for r in operators if r.get("Company")}

    # Cross-reference
    in_leads_only = sorted(lead_companies - op_companies)
    in_operators_only_count = len(op_companies - lead_companies)
    overlap = len(lead_companies & op_companies)

    # Missing fields
    missing_email = []
    missing_vertical = []
    placeholder_emails = []
    seen_emails = {}
    duplicate_emails = []

    for i, r in enumerate(leads, start=2):  # row 2 = first data row
        email = str(r.get("Email", "")).strip().lower()
        company = str(r.get("Company", ""))
        name = str(r.get("Name", ""))

        # Missing email
        if not email or email in PLACEHOLDER_PATTERNS:
            if email and email not in ("", "none", "n/a"):
                placeholder_emails.append({"row": i, "company": company, "value": email})
            else:
                missing_email.append({"row": i, "company": company, "name": name})
            continue

        # Duplicate email
        if email in seen_emails:
            duplicate_emails.append({
                "email": email,
                "rows": [seen_emails[email], i],
                "company": company,
            })
        else:
            seen_emails[email] = i

        # Missing vertical
        if not str(r.get("Vertical", "")).strip():
            missing_vertical.append({"row": i, "company": company})

    return {
        "leads_count": len(leads),
        "operators_count": len(operators),
        "overlap": overlap,
        "in_leads_only": in_leads_only,
        "unprospected_operators": in_operators_only_count,
        "missing_email": missing_email,
        "missing_vertical": missing_vertical,
        "placeholder_emails": placeholder_emails,
        "duplicate_emails": duplicate_emails,
    }


def check_gmail(leads_emails: set[str]) -> dict:
    """Cross-reference Gmail SENT with Leads emails."""
    sent = get_gmail_sent_emails()
    sent_emails = {}
    for s in sent:
        email = s["to"]
        if email and email not in sent_emails:
            sent_emails[email] = {"subject": s["subject"], "date": s["date"]}

    sent_not_in_leads = []
    for email, meta in sorted(sent_emails.items()):
        if email not in leads_emails:
            sent_not_in_leads.append({"email": email, **meta})

    in_leads_not_sent = sorted(leads_emails - set(sent_emails.keys()))

    return {
        "total_sent_unique": len(sent_emails),
        "sent_not_in_leads": sent_not_in_leads,
        "in_leads_not_sent": in_leads_not_sent,
    }


# ---------------------------------------------------------------------------
# Report formatting
# ---------------------------------------------------------------------------

def severity(sheets_result: dict, gmail_result: dict | None) -> int:
    """0=ok, 1=warnings, 2=critical."""
    level = 0
    if sheets_result["missing_email"]:
        level = max(level, 1)
    if sheets_result["placeholder_emails"]:
        level = max(level, 1)
    if sheets_result["duplicate_emails"]:
        level = max(level, 2)
    if gmail_result and gmail_result["sent_not_in_leads"]:
        level = max(level, 2)  # sent emails missing from CRM is critical
    return level


def print_report(sheets_result: dict, gmail_result: dict | None):
    """Human-readable report to stdout."""
    s = sheets_result
    print("=" * 60)
    print("  AdsGram Data Validation Report")
    print("=" * 60)

    print(f"\n--- Sheets Overview ---")
    print(f"  Leads:            {s['leads_count']} rows")
    print(f"  Operators:        {s['operators_count']} rows")
    print(f"  Overlap:          {s['overlap']} companies")
    print(f"  Unprospected:     {s['unprospected_operators']} operators")

    if s["in_leads_only"]:
        print(f"\n  Leads-only companies ({len(s['in_leads_only'])}):")
        for c in s["in_leads_only"]:
            print(f"    - {c}")

    if s["missing_email"]:
        print(f"\n[WARN] Missing email: {len(s['missing_email'])} leads")

    if s["missing_vertical"]:
        print(f"[WARN] Missing vertical: {len(s['missing_vertical'])} leads")

    if s["placeholder_emails"]:
        print(f"[WARN] Placeholder emails: {len(s['placeholder_emails'])}")
        for p in s["placeholder_emails"][:5]:
            print(f"    row {p['row']}: {p['company']} → \"{p['value']}\"")

    if s["duplicate_emails"]:
        print(f"\n[CRIT] Duplicate emails: {len(s['duplicate_emails'])}")
        for d in s["duplicate_emails"]:
            print(f"    {d['email']} (rows {d['rows']})")

    if gmail_result:
        g = gmail_result
        print(f"\n--- Gmail Sent Audit ---")
        print(f"  Unique sent-to:     {g['total_sent_unique']}")
        print(f"  Sent but not in CRM: {len(g['sent_not_in_leads'])}")
        print(f"  In CRM but unsent:   {len(g['in_leads_not_sent'])}")

        if g["sent_not_in_leads"]:
            print(f"\n[CRIT] Sent but MISSING from CRM:")
            for e in g["sent_not_in_leads"]:
                print(f"    {e['email']}  |  {e.get('subject', '')}  |  {e.get('date', '')}")

        if g["in_leads_not_sent"]:
            print(f"\n[INFO] In CRM but never sent to ({len(g['in_leads_not_sent'])}):")
            for e in g["in_leads_not_sent"][:10]:
                print(f"    {e}")
            if len(g["in_leads_not_sent"]) > 10:
                print(f"    ... and {len(g['in_leads_not_sent']) - 10} more")

    level = severity(sheets_result, gmail_result)
    label = {0: "PASS", 1: "WARNINGS", 2: "CRITICAL"}[level]
    print(f"\n{'=' * 60}")
    print(f"  Result: {label}")
    print(f"{'=' * 60}")
    return level


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="AdsGram data validation")
    parser.add_argument("--gmail", action="store_true", help="Include Gmail SENT audit")
    parser.add_argument("--json", action="store_true", help="JSON output instead of text")
    args = parser.parse_args()

    gc = get_sheets_client()
    sheets_result = check_sheets(gc)

    gmail_result = None
    if args.gmail:
        # Build set of valid lead emails for cross-ref
        leads = read_sheet(gc, CRM_SHEET_ID, "Leads")
        leads_emails = set()
        for r in leads:
            email = str(r.get("Email", "")).strip().lower()
            if email and email not in PLACEHOLDER_PATTERNS:
                leads_emails.add(email)
        gmail_result = check_gmail(leads_emails)

    if args.json:
        output = {"sheets": sheets_result}
        if gmail_result:
            output["gmail"] = gmail_result
        output["severity"] = severity(sheets_result, gmail_result)
        print(json.dumps(output, ensure_ascii=False, indent=2))
        sys.exit(output["severity"])
    else:
        level = print_report(sheets_result, gmail_result)
        sys.exit(level)


if __name__ == "__main__":
    main()
