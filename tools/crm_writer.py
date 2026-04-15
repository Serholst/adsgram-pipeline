#!/usr/bin/env python3
"""
CRM Writer — Python replacement for CRM Writer Claude agent.

Reads data/pipeline/crm-writer-input.json, validates, deduplicates,
sorts by priority, writes to Google Sheets CRM, updates Company DB.

Usage:
    python3 tools/crm_writer.py [--dry-run]

Input:  data/pipeline/crm-writer-input.json
Output: stdout JSON + data/pipeline/crm-writer-output.json
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent

from pipeline_io import PIPELINE_DIR

INPUT_PATH = PIPELINE_DIR / "crm-writer-input.json"
OUTPUT_PATH = PIPELINE_DIR / "crm-writer-output.json"

REQUIRED_FIELDS = ["company", "first_name", "last_name", "title"]
VALID_LEAD_STATUS = {"Verified", "Partially verified", "Not verified", "Needs review", "Skip"}
VALID_EMAIL_STATUS = {"verified", "catchall", "unverified", "unavailable", None}
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _die(msg: str):
    print(json.dumps({"error": msg}))
    sys.exit(1)


def _run_helper(command: str, json_file: str | None = None) -> dict:
    """Run sheets_helper.py and return parsed JSON output."""
    cmd = [sys.executable, str(SCRIPT_DIR / "sheets_helper.py"), command]
    if json_file:
        cmd.append(json_file)

    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(PROJECT_DIR))
    if result.returncode != 0:
        stderr = result.stderr.strip()
        # sheets_helper outputs errors as JSON to stdout
        if result.stdout.strip():
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                pass
        return {"error": f"sheets_helper {command} failed: {stderr or result.stdout}"}

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"error": f"sheets_helper {command} returned invalid JSON: {result.stdout[:200]}"}


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_lead(lead: dict) -> str | None:
    """Return error message if lead is invalid, None if ok."""
    for field in REQUIRED_FIELDS:
        if not lead.get(field, "").strip():
            return f"missing required field: {field}"

    email = lead.get("email")
    if email and not EMAIL_RE.match(email.strip()):
        return f"invalid email format: {email}"

    ls = lead.get("lead_status")
    if ls and ls not in VALID_LEAD_STATUS:
        return f"invalid lead_status: {ls}"

    es = lead.get("email_status")
    if es is not None and es not in VALID_EMAIL_STATUS:
        return f"invalid email_status: {es}"

    return None


def check_dedup(lead: dict, dedup_emails: set, dedup_name_company: set) -> str | None:
    """Return dedup reason or None."""
    email = (lead.get("email") or "").strip().lower()
    if email and email in dedup_emails:
        return "duplicate: existing email in CRM"

    first = (lead.get("first_name") or "").strip().lower()
    last = (lead.get("last_name") or "").strip().lower()
    name = f"{first} {last}".strip()
    company = (lead.get("company") or "").strip().lower()
    if name and company:
        key = f"{name}|||{company}"
        if key in dedup_name_company:
            return "duplicate: existing name+company in CRM"

    return None


# ---------------------------------------------------------------------------
# Field formatting — CRM column values
# ---------------------------------------------------------------------------

def format_name(lead: dict) -> str:
    return f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip()


def format_socials(lead: dict) -> str:
    parts = []
    if lead.get("linkedin_url"):
        parts.append(f"LinkedIn: {lead['linkedin_url']}")
    if lead.get("telegram_handle"):
        parts.append(f"TG: {lead['telegram_handle']}")
    if lead.get("twitter"):
        parts.append(f"Twitter: {lead['twitter']}")
    if lead.get("instagram"):
        parts.append(f"IG: {lead['instagram']}")

    # Company-level socials (only add if not already covered by lead-level)
    cc = lead.get("company_contacts") or {}
    sl = cc.get("social_links") or {}
    if sl.get("telegram") and not lead.get("telegram_handle"):
        parts.append(f"TG (company): {sl['telegram']}")
    if sl.get("twitter") and not lead.get("twitter"):
        parts.append(f"Twitter (company): {sl['twitter']}")
    if sl.get("instagram") and not lead.get("instagram"):
        parts.append(f"IG (company): {sl['instagram']}")

    return " | ".join(parts)


def format_alt_contacts(lead: dict) -> str:
    parts = []
    if lead.get("phone"):
        parts.append(f"Phone: {lead['phone']}")
    if lead.get("whatsapp"):
        parts.append(f"WhatsApp: {lead['whatsapp']}")

    cc = lead.get("company_contacts") or {}
    if cc.get("general_email"):
        parts.append(f"Alt email: {cc['general_email']}")
    if cc.get("press_email"):
        parts.append(f"Press email: {cc['press_email']}")
    if cc.get("partnerships_email"):
        parts.append(f"Partners email: {cc['partnerships_email']}")
    if cc.get("phone") and not lead.get("phone"):
        parts.append(f"Company phone: {cc['phone']}")

    return " | ".join(parts)


def format_sources_signals(lead: dict) -> str:
    parts = []
    sources = lead.get("contact_sources") or []
    if sources:
        parts.append(f"Source: {', '.join(sources)}")

    conferences = lead.get("conference_appearances") or []
    for c in conferences:
        parts.append(f"Conference: {c}")

    signals = lead.get("industry_signals") or []
    for s in signals:
        parts.append(s)

    es = lead.get("email_source")
    if es:
        parts.append(f"Email via: {es}")

    return " | ".join(parts)


def format_notes(lead: dict) -> str:
    parts = []
    if lead.get("verification_note"):
        parts.append(lead["verification_note"])
    if lead.get("headline"):
        parts.append(f"Headline: {lead['headline']}")
    if lead.get("role_description"):
        parts.append(f"Role desc: {lead['role_description']}")
    if lead.get("enrichment_note"):
        parts.append(lead["enrichment_note"])
    flags = lead.get("enrichment_flags") or []
    if flags:
        parts.append(f"Flags: {', '.join(flags)}")
    return " | ".join(parts)


def lead_to_crm_row(lead: dict) -> dict:
    """Convert a lead dict to CRM column dict (keys match CRM_EXPECTED_HEADERS)."""
    return {
        "Company": lead.get("company", ""),
        "Vertical": lead.get("vertical") or "",
        "Country": lead.get("country") or "",
        "Name": format_name(lead),
        "Title": lead.get("title", ""),
        "Email": lead.get("email") or "",
        "Email Status": lead.get("email_status") or "",
        "Socials": format_socials(lead),
        "Alt Contacts": format_alt_contacts(lead),
        "Sources & Signals": format_sources_signals(lead),
        "Lead Status": lead.get("lead_status", ""),
        "Stage": "",
        "First Contact Date": "",
        "Last Activity Date": "",
        "Suggested CTA": "",
        "Notes": format_notes(lead),
    }


# ---------------------------------------------------------------------------
# Priority sorting
# ---------------------------------------------------------------------------

TIER1_KEYWORDS = ["director", "vp ", "vice president", "head of", "chief", "cmo", "cro"]
TIER2_KEYWORDS = ["growth", "ua ", "user acquisition", "media buy", "performance market"]


def sort_key(lead: dict) -> tuple:
    title = (lead.get("title") or "").lower()
    if any(kw in title for kw in TIER1_KEYWORDS):
        tier = 1
    elif any(kw in title for kw in TIER2_KEYWORDS):
        tier = 2
    else:
        tier = 3

    # Within tier: SKIP leads last
    is_skip = 1 if lead.get("lead_status") == "Skip" else 0

    return (is_skip, tier)


# ---------------------------------------------------------------------------
# Company DB update
# ---------------------------------------------------------------------------

def update_company_db(leads: list[dict], dry_run: bool) -> dict:
    """Update Company DB with companies from processed leads."""
    companies = {}
    for lead in leads:
        company = lead.get("company", "").strip()
        domain = lead.get("company_domain", "").strip()
        if not company:
            continue
        if company not in companies:
            companies[company] = {"domain": domain, "leads": [], "verticals": set()}
        companies[company]["leads"].append(lead)
        v = lead.get("vertical")
        if v:
            companies[company]["verticals"].add(v)

    if not companies:
        return {"company_db_updated": False, "companies_added": 0}

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    batch = []
    for name, info in companies.items():
        lead_count = len(info["leads"])
        statuses = [l.get("lead_status", "") for l in info["leads"]]
        skip_count = sum(1 for s in statuses if s == "Skip")
        active_count = lead_count - skip_count

        summary_parts = []
        if active_count > 0:
            titles = [l.get("title", "") for l in info["leads"] if l.get("lead_status") != "Skip"]
            summary_parts.append(f"{active_count} leads: {', '.join(t for t in titles[:3] if t)}")
            emails = sum(1 for l in info["leads"] if l.get("email") and l.get("lead_status") != "Skip")
            if emails:
                summary_parts.append(f"{emails} with email")
        if skip_count > 0:
            summary_parts.append(f"{skip_count} skipped")

        batch.append({
            "company": name,
            "updates": {
                "Prospected": f"Yes ({today})",
                "Search Results": ". ".join(summary_parts) + ".",
            },
        })

    if dry_run:
        return {"company_db_updated": False, "companies_added": len(batch), "dry_run": True, "batch": batch}

    tmp_file = str(PIPELINE_DIR / "companies_batch.json")
    with open(tmp_file, "w") as f:
        json.dump(batch, f, ensure_ascii=False, indent=2)

    result = _run_helper("companydb-update-cells", tmp_file)
    if "error" in result:
        return {"company_db_updated": False, "companies_added": 0, "error": result["error"]}

    return {
        "company_db_updated": True,
        "companies_added": result.get("updated", 0),
        "companies_not_found": result.get("not_found", 0),
    }


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="CRM Writer — write leads to Google Sheets")
    parser.add_argument("--dry-run", action="store_true", help="Validate and format only, don't write")
    parser.add_argument("--input", type=str, default=str(INPUT_PATH), help="Path to crm-writer-input.json")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        _die(f"Input file not found: {input_path}")

    try:
        with open(input_path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        _die(f"Invalid JSON in {input_path}: {e}")

    leads = data.get("leads", [])
    metadata = data.get("write_metadata", {})

    if not leads:
        result = {
            "status": "success",
            "rows_written": 0, "rows_rejected": 0, "rows_duplicate": 0,
            "rejection_details": [],
            "company_db_updated": False, "companies_added": 0,
            "escalation": None, "recommendation": "No leads in input",
        }
        _write_output(result)
        return

    # Step 1: Validate CRM headers
    if not args.dry_run:
        headers_check = _run_helper("crm-validate-headers")
        if "error" in headers_check:
            result = {
                "status": "blocked",
                "rows_written": 0, "rows_rejected": 0, "rows_duplicate": 0,
                "rejection_details": [],
                "company_db_updated": False, "companies_added": 0,
                "escalation": f"sheets_helper error: {headers_check['error']}",
                "recommendation": None,
            }
            _write_output(result)
            return

        if headers_check.get("status") != "ok":
            result = {
                "status": "blocked",
                "rows_written": 0, "rows_rejected": 0, "rows_duplicate": 0,
                "rejection_details": [],
                "company_db_updated": False, "companies_added": 0,
                "escalation": f"CRM headers mismatch: expected {headers_check.get('expected')}, got {headers_check.get('actual')}",
                "recommendation": None,
            }
            _write_output(result)
            return

    # Step 2: Load dedup set
    dedup_emails = set()
    dedup_name_company = set()

    if not args.dry_run:
        dedup_data = _run_helper("crm-dedup-set")
        if "error" not in dedup_data:
            dedup_emails = set(dedup_data.get("emails", []))
            dedup_name_company = set(dedup_data.get("name_company", []))

    # Step 3: Validate, dedup, track batch-internal dedup
    valid_leads = []
    rejected = []
    duplicated = []
    batch_emails = set()
    batch_name_company = set()

    for lead in leads:
        lead_label = f"{lead.get('first_name', '')} {lead.get('last_name', '')} @ {lead.get('company', '')}"

        # Validate
        err = validate_lead(lead)
        if err:
            rejected.append({"lead": lead_label, "reason": err})
            continue

        # Dedup against existing CRM
        dup = check_dedup(lead, dedup_emails, dedup_name_company)
        if dup:
            duplicated.append({"lead": lead_label, "reason": dup})
            continue

        # Dedup within this batch
        email = (lead.get("email") or "").strip().lower()
        if email and email in batch_emails:
            duplicated.append({"lead": lead_label, "reason": "duplicate: within batch (email)"})
            continue

        first = (lead.get("first_name") or "").strip().lower()
        last = (lead.get("last_name") or "").strip().lower()
        name = f"{first} {last}".strip()
        company = (lead.get("company") or "").strip().lower()
        name_key = f"{name}|||{company}"
        if name and company and name_key in batch_name_company:
            duplicated.append({"lead": lead_label, "reason": "duplicate: within batch (name+company)"})
            continue

        if email:
            batch_emails.add(email)
        if name and company:
            batch_name_company.add(name_key)

        valid_leads.append(lead)

    # Step 4: Sort by priority
    valid_leads.sort(key=sort_key)

    # Step 5: Format CRM rows
    crm_rows = [lead_to_crm_row(lead) for lead in valid_leads]

    # Step 6: Write to CRM
    rows_written = 0
    if crm_rows and not args.dry_run:
        tmp_file = str(PIPELINE_DIR / "leads_batch.json")
        with open(tmp_file, "w") as f:
            json.dump(crm_rows, f, ensure_ascii=False, indent=2)

        # Get row count before
        count_before = _run_helper("crm-row-count")
        before = count_before.get("row_count", 0)

        # Write
        write_result = _run_helper("crm-append-rows", tmp_file)
        if "error" in write_result:
            result = {
                "status": "blocked",
                "rows_written": 0,
                "rows_rejected": len(rejected),
                "rows_duplicate": len(duplicated),
                "rejection_details": rejected + duplicated,
                "company_db_updated": False, "companies_added": 0,
                "escalation": f"Write failed: {write_result['error']}",
                "recommendation": None,
            }
            _write_output(result)
            return

        # Verify row count
        count_after = _run_helper("crm-row-count")
        after = count_after.get("row_count", 0)
        rows_written = after - before

        if rows_written != len(crm_rows):
            # Non-fatal: some rows may have had API issues but report it
            pass
    elif args.dry_run:
        rows_written = len(crm_rows)

    # Step 7: Update Company DB
    companydb_result = update_company_db(valid_leads, args.dry_run)

    # Step 8: Build result
    total_input = len(leads)
    total_processed = rows_written + len(rejected) + len(duplicated)

    recommendation = None
    if len(rejected) > total_input * 0.1 and total_input > 0:
        recommendation = f"Rejected {len(rejected)}/{total_input} leads (>{10}%). Data quality issue from previous stages."

    status = "success"
    if rejected or duplicated:
        status = "partial" if rows_written > 0 else "blocked"

    result = {
        "status": status,
        "rows_written": rows_written,
        "rows_rejected": len(rejected),
        "rows_duplicate": len(duplicated),
        "rejection_details": rejected + duplicated,
        "company_db_updated": companydb_result.get("company_db_updated", False),
        "companies_added": companydb_result.get("companies_added", 0),
        "escalation": None,
        "recommendation": recommendation,
    }

    if args.dry_run:
        result["dry_run"] = True
        result["crm_rows_preview"] = crm_rows[:3]

    _write_output(result)


def _write_output(result: dict):
    """Write to both stdout and file."""
    PIPELINE_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
