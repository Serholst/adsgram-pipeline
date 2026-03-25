#!/usr/bin/env python3
"""
Google Sheets CLI helper for AdsGram Pipeline agents.

Agents call this via Bash tool:
    python3 tools/sheets_helper.py <command> [args]

All output is JSON to stdout. Errors go to stderr.

Environment variables (from .env):
    CRM_SHEET_ID          — Google Sheet ID for the CRM
    COMPANYDB_SHEET_ID    — Google Sheet ID for Company DB
    GOOGLE_CREDENTIALS_PATH — path to service account JSON (default: ./credentials.json)
"""

import json
import logging
import os
import sys
import time
from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
ENV_PATH = PROJECT_DIR / ".env"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

CRM_SHEET_NAME = "Leads"
COMPANYDB_SHEET_NAME = "Top iGaming Operators"
CRM_EXPECTED_HEADERS = [
    "Company", "Vertical", "Country", "Name", "Title",
    "Email", "Email Status", "Web Search", "Lead Status", "Stage",
    "First Contact Date", "Last Activity Date", "Suggested CTA", "Notes",
]

WRITE_RETRIES = 3
WRITE_BACKOFF_BASE = 5  # seconds

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Environment loading
# ---------------------------------------------------------------------------

def _load_env():
    """Load .env file into os.environ (simple parser, no dependency)."""
    if not ENV_PATH.exists():
        return
    for line in ENV_PATH.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


_load_env()

CREDENTIALS_PATH = os.environ.get("GOOGLE_CREDENTIALS_PATH", "./credentials.json")
CRM_SHEET_ID = os.environ.get("CRM_SHEET_ID", "")
COMPANYDB_SHEET_ID = os.environ.get("COMPANYDB_SHEET_ID", "")


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

_gc = None


def _get_client() -> gspread.Client:
    global _gc
    if _gc is not None:
        return _gc

    creds_path = CREDENTIALS_PATH
    if not Path(creds_path).is_absolute():
        creds_path = str(PROJECT_DIR / creds_path)

    if not Path(creds_path).exists():
        _die(f"Credentials file not found: {creds_path}")

    creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    _gc = gspread.authorize(creds)
    return _gc


def _open_sheet(sheet_id: str, worksheet_name: str | None = None) -> gspread.Worksheet:
    gc = _get_client()
    try:
        ss = gc.open_by_key(sheet_id)
    except gspread.exceptions.SpreadsheetNotFound:
        _die(f"Spreadsheet not found (ID: {sheet_id}). Check Sheet ID and sharing.")
    if worksheet_name:
        try:
            return ss.worksheet(worksheet_name)
        except gspread.exceptions.WorksheetNotFound:
            _die(f"Worksheet '{worksheet_name}' not found in spreadsheet {sheet_id}.")
    return ss.sheet1


def _open_crm() -> gspread.Worksheet:
    if not CRM_SHEET_ID:
        _die("CRM_SHEET_ID not set in .env")
    return _open_sheet(CRM_SHEET_ID, CRM_SHEET_NAME)


def _open_companydb() -> gspread.Worksheet:
    if not COMPANYDB_SHEET_ID:
        _die("COMPANYDB_SHEET_ID not set in .env")
    return _open_sheet(COMPANYDB_SHEET_ID, COMPANYDB_SHEET_NAME)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _die(msg: str):
    print(json.dumps({"error": msg}), file=sys.stdout)
    sys.exit(1)


def _output(data):
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _append_rows_with_retry(ws, rows: list[list], retries: int = WRITE_RETRIES):
    """Batch append rows with retry on API errors."""
    for attempt in range(retries):
        try:
            ws.append_rows(
                rows,
                value_input_option="USER_ENTERED",
                table_range="A1",
            )
            return
        except gspread.exceptions.APIError as e:
            if attempt < retries - 1:
                wait = WRITE_BACKOFF_BASE * (attempt + 1)
                logger.warning("Sheets API error (attempt %d/%d), retrying in %ds: %s",
                               attempt + 1, retries, wait, e)
                time.sleep(wait)
            else:
                raise


# ---------------------------------------------------------------------------
# CRM Commands
# ---------------------------------------------------------------------------

def cmd_crm_read_all():
    """Read all CRM rows as list of dicts."""
    ws = _open_crm()
    records = ws.get_all_records(numericise_ignore=["all"])
    _output(records)


def cmd_crm_read_headers():
    """Read CRM header row."""
    ws = _open_crm()
    headers = ws.row_values(1)
    _output(headers)


def cmd_crm_append_rows(json_file: str):
    """Append rows from a JSON file to CRM. JSON = list of dicts with CRM column keys."""
    data = _read_json_file(json_file)
    if not isinstance(data, list):
        _die("JSON file must contain a list of objects")

    ws = _open_crm()
    rows = []
    for item in data:
        row = [str(item.get(col, "")) for col in CRM_EXPECTED_HEADERS]
        rows.append(row)

    if rows:
        _append_rows_with_retry(ws, rows)

    _output({"status": "ok", "rows_appended": len(rows)})


def cmd_crm_dedup_set():
    """Return dedup sets: emails and (name, company) pairs from CRM."""
    ws = _open_crm()
    records = ws.get_all_records(numericise_ignore=["all"])

    emails = set()
    name_company = set()

    for r in records:
        email = str(r.get("Email", "")).strip().lower()
        if email:
            emails.add(email)
        name = str(r.get("Name", "")).strip().lower()
        company = str(r.get("Company", "")).strip().lower()
        if name and company:
            name_company.add(f"{name}|||{company}")

    _output({
        "emails": sorted(emails),
        "name_company": sorted(name_company),
        "total_rows": len(records),
    })


def cmd_crm_validate_headers():
    """Validate CRM has correct headers in correct order."""
    ws = _open_crm()
    headers = ws.row_values(1)

    if headers == CRM_EXPECTED_HEADERS:
        _output({"status": "ok", "headers": headers})
    else:
        _output({
            "status": "error",
            "message": "Headers mismatch",
            "expected": CRM_EXPECTED_HEADERS,
            "actual": headers,
        })


def cmd_crm_row_count():
    """Return number of data rows in CRM (excluding header)."""
    ws = _open_crm()
    all_values = ws.get_all_values()
    count = max(0, len(all_values) - 1)  # subtract header
    _output({"row_count": count})


# ---------------------------------------------------------------------------
# Company DB Commands
# ---------------------------------------------------------------------------

def cmd_companydb_read_all():
    """Read all Company DB rows as list of dicts."""
    ws = _open_companydb()
    records = ws.get_all_records(numericise_ignore=["all"])
    _output(records)


def cmd_companydb_domains():
    """Return list of domains from Company DB (column with 'Domain' in header)."""
    ws = _open_companydb()
    headers = ws.row_values(1)

    # Find domain column (flexible: "Domain", "Company Domain", etc.)
    domain_col = None
    for i, h in enumerate(headers):
        if "domain" in h.lower():
            domain_col = i
            break

    if domain_col is None:
        _die("No column with 'Domain' found in Company DB headers: " + str(headers))

    all_values = ws.get_all_values()
    domains = []
    for row in all_values[1:]:  # skip header
        if domain_col < len(row) and row[domain_col].strip():
            domains.append(row[domain_col].strip().lower())

    _output({"domains": sorted(set(domains)), "count": len(set(domains))})


def cmd_companydb_excluded_domains():
    """Return domains that should be EXCLUDED from search.

    A company is excluded if:
    - "Prospected" column is non-empty (any value: "Processed", "Trash", "Yes ...", etc.)
    - OR "Search Results" column contains the word "excluded" (case-insensitive)

    Companies with empty Prospected AND no "excluded" in Search Results are available for search.
    """
    ws = _open_companydb()
    headers = ws.row_values(1)

    # Find required columns
    domain_col = None
    prospected_col = None
    search_results_col = None

    for i, h in enumerate(headers):
        h_lower = h.lower().strip()
        if domain_col is None and "domain" in h_lower:
            domain_col = i
        if "prospected" in h_lower:
            prospected_col = i
        if "search result" in h_lower:
            search_results_col = i

    if domain_col is None:
        _die("No column with 'Domain' found in Company DB headers: " + str(headers))

    all_values = ws.get_all_values()
    excluded = []
    available = []

    for row in all_values[1:]:  # skip header
        domain = row[domain_col].strip().lower() if domain_col < len(row) else ""
        if not domain:
            continue

        prospected = row[prospected_col].strip() if prospected_col is not None and prospected_col < len(row) else ""
        search_results = row[search_results_col].strip() if search_results_col is not None and search_results_col < len(row) else ""

        is_excluded = bool(prospected) or ("excluded" in search_results.lower())

        if is_excluded:
            excluded.append(domain)
        else:
            available.append(domain)

    _output({
        "excluded_domains": sorted(set(excluded)),
        "excluded_count": len(set(excluded)),
        "available_domains": sorted(set(available)),
        "available_count": len(set(available)),
    })


def cmd_companydb_append_rows(json_file: str):
    """Append rows from JSON file to Company DB."""
    data = _read_json_file(json_file)
    if not isinstance(data, list):
        _die("JSON file must contain a list of objects")

    ws = _open_companydb()
    headers = ws.row_values(1)

    rows = []
    for item in data:
        row = [str(item.get(col, "")) for col in headers]
        rows.append(row)

    if rows:
        _append_rows_with_retry(ws, rows)

    _output({"status": "ok", "rows_appended": len(rows)})


# ---------------------------------------------------------------------------
# Setup Commands
# ---------------------------------------------------------------------------

def cmd_setup_crm(sheet_id: str):
    """Initialize a Google Sheet as CRM: create 'Leads' sheet with headers."""
    gc = _get_client()
    try:
        ss = gc.open_by_key(sheet_id)
    except gspread.exceptions.SpreadsheetNotFound:
        _die(f"Spreadsheet not found: {sheet_id}")

    # Create or get Leads worksheet
    try:
        ws = ss.worksheet(CRM_SHEET_NAME)
        existing = ws.row_values(1)
        if existing == CRM_EXPECTED_HEADERS:
            _output({"status": "already_initialized", "sheet_name": CRM_SHEET_NAME})
            return
    except gspread.exceptions.WorksheetNotFound:
        ws = ss.add_worksheet(title=CRM_SHEET_NAME, rows=1000, cols=len(CRM_EXPECTED_HEADERS))

    ws.update([CRM_EXPECTED_HEADERS], value_input_option="USER_ENTERED")
    ws.format("A1:N1", {"textFormat": {"bold": True}})
    _output({"status": "initialized", "sheet_name": CRM_SHEET_NAME, "columns": len(CRM_EXPECTED_HEADERS)})


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _read_json_file(path: str) -> dict | list:
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        _die(f"JSON file not found: {path}")
    except json.JSONDecodeError as e:
        _die(f"Invalid JSON in {path}: {e}")


# ---------------------------------------------------------------------------
# Normalization Commands
# ---------------------------------------------------------------------------

OWNERSHIP_VALUES = ["Private", "Public", "State", "Non-profit", "Tribal", "Unknown"]
PROSPECTED_VALUES = ["Processed", "Failed", "Win", "Error", "Trash"]
BUSINESS_DOMAIN_VALUES = ["Betting", "iGaming", "Adult", "Services", "Crypto", "Land", "Other"]


def normalize_ownership(raw: str) -> str:
    """Normalize a free-text ownership value to one of OWNERSHIP_VALUES."""
    v = raw.strip()
    if not v:
        return "Unknown"
    low = v.lower()
    if low.startswith("private"):
        return "Private"
    if low.startswith("public"):
        return "Public"
    if any(x in low for x in ["state", "govt", "government", "federal"]):
        return "State"
    if "non-profit" in low or "nonprofit" in low or "mutual" in low:
        return "Non-profit"
    if "tribal" in low:
        return "Tribal"
    return "Unknown"


def cmd_companydb_normalize_ownership():
    """Normalize the Ownership column in Company DB. Reports changes, applies in-place."""
    ws = _open_companydb()
    headers = ws.row_values(1)
    if "Ownership" not in headers:
        _die("No 'Ownership' column found in Company DB")

    col_idx = headers.index("Ownership")  # 0-indexed
    col_letter = chr(ord("A") + col_idx)

    all_values = ws.get_all_values()
    updates = []
    changes = []

    for i, row in enumerate(all_values[1:], start=2):
        old = row[col_idx].strip() if col_idx < len(row) else ""
        new = normalize_ownership(old)
        if old != new:
            updates.append({"range": f"{col_letter}{i}", "values": [[new]]})
            changes.append({"row": i, "old": old, "new": new})

    if updates:
        ws.batch_update(updates, value_input_option="USER_ENTERED")

    _output({"status": "ok", "changes": len(changes), "details": changes})


def normalize_business_domain(raw: str) -> str:
    """Normalize a free-text business domain to one of BUSINESS_DOMAIN_VALUES.

    Categories:
        Betting  — online sportsbook, sports betting, fantasy sports
        iGaming  — online casino, slots, poker, lottery, bingo
        Adult    — porn, dating, erotic, 18+, ai dating/character
        Services — VPN, proxy, ad blocker, payments, adtech
        Crypto   — web3, crypto, defi, nft, mining
        Land     — offline-only: land-based casino, integrated resort, scratch cards, state lottery (no online)
        Other    — B2B, affiliate, tech provider, platform, unclassified
    """
    v = raw.strip()
    low = v.lower()
    if not low:
        return "Other"
    # Already normalized — pass through
    if v in BUSINESS_DOMAIN_VALUES:
        return v
    # B2B / platform / affiliate → Other
    if any(x in low for x in ["b2b", "tech provider", "data provider", "game studio",
                                "platform provider", "marketplace", "affiliate",
                                "performance marketing"]):
        return "Other"
    # Adult
    if any(x in low for x in ["adult", "porn", "dating", "erotic", "18+"]):
        return "Adult"
    # Crypto / Web3
    if any(x in low for x in ["crypto", "web3", "defi", "nft", "mining"]):
        return "Crypto"
    # Services
    if any(x in low for x in ["vpn", "proxy", "ad block", "adtech", "payment", "privacy"]):
        return "Services"
    # Land-based only (no online indicators)
    land_kw = ["land-based", "integrated resort", "tavern gaming", "distributed gaming",
               "video gaming terminal", "vgt", "horse racing pool"]
    online_kw = ["online", "igaming", "icasino", "sports betting", "casino",
                 "betting", "lottery", "bingo", "poker", "fantasy", "esport"]
    is_land = any(x in low for x in land_kw)
    is_online = any(x in low for x in online_kw)
    if is_land and not is_online:
        return "Land"
    # State/national lottery without online presence
    if any(x in low for x in ["umbrella", "state lottery", "national lottery",
                                "scratch card", "lotto", "toto", "4d"]):
        if not any(x in low for x in ["online", "internet", "digital",
                                       "sports betting", "casino"]):
            return "Land"
    # iGaming (casino, slots, poker, lottery, bingo)
    casino_kw = ["casino", "slots", "poker", "bingo", "igaming", "egames", "gaming machine"]
    lottery_kw = ["lottery", "lotto", "scratch", "4d", "toto"]
    if any(x in low for x in casino_kw) or any(x in low for x in lottery_kw):
        return "iGaming"
    # Betting
    betting_kw = ["sports betting", "sportsbook", "sports data", "betting infrastructure",
                  "horse racing", "football betting", "racing", "fantasy"]
    if any(x in low for x in betting_kw):
        return "Betting"
    # Catch remaining gaming-like
    if "gaming" in low:
        return "iGaming"
    return "Other"


def cmd_companydb_normalize_business_domain():
    """Normalize the Business Domain column in Company DB."""
    ws = _open_companydb()
    headers = ws.row_values(1)
    if "Business Domain" not in headers:
        _die("No 'Business Domain' column found in Company DB")

    col_idx = headers.index("Business Domain")
    col_letter = chr(ord("A") + col_idx)

    all_values = ws.get_all_values()
    updates = []
    changes = []

    for i, row in enumerate(all_values[1:], start=2):
        old = row[col_idx].strip() if col_idx < len(row) else ""
        new = normalize_business_domain(old)
        if old != new:
            updates.append({"range": f"{col_letter}{i}", "values": [[new]]})
            changes.append({"row": i, "old": old, "new": new})

    if updates:
        ws.batch_update(updates, value_input_option="USER_ENTERED")

    _output({"status": "ok", "changes": len(changes), "details": changes})


# ---------------------------------------------------------------------------
# CLI dispatcher
# ---------------------------------------------------------------------------

COMMANDS = {
    "crm-read-all": (cmd_crm_read_all, 0),
    "crm-read-headers": (cmd_crm_read_headers, 0),
    "crm-append-rows": (cmd_crm_append_rows, 1),
    "crm-dedup-set": (cmd_crm_dedup_set, 0),
    "crm-validate-headers": (cmd_crm_validate_headers, 0),
    "crm-row-count": (cmd_crm_row_count, 0),
    "companydb-read-all": (cmd_companydb_read_all, 0),
    "companydb-domains": (cmd_companydb_domains, 0),
    "companydb-excluded-domains": (cmd_companydb_excluded_domains, 0),
    "companydb-append-rows": (cmd_companydb_append_rows, 1),
    "setup-crm": (cmd_setup_crm, 1),
    "companydb-normalize-ownership": (cmd_companydb_normalize_ownership, 0),
    "companydb-normalize-business-domain": (cmd_companydb_normalize_business_domain, 0),
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print("Usage: sheets_helper.py <command> [args]")
        print("\nCommands:")
        for name in sorted(COMMANDS):
            print(f"  {name}")
        sys.exit(0)

    cmd_name = sys.argv[1]
    if cmd_name not in COMMANDS:
        _die(f"Unknown command: {cmd_name}. Run with --help for list.")

    func, nargs = COMMANDS[cmd_name]
    args = sys.argv[2:]
    if len(args) < nargs:
        _die(f"Command '{cmd_name}' requires {nargs} argument(s), got {len(args)}.")

    func(*args[:nargs])


if __name__ == "__main__":
    main()
