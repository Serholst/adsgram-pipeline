#!/usr/bin/env python3
"""
Unified exclusion gate: collects exclusion data from Company DB and CRM
in a single call instead of 3 separate ones.

Usage:
    python3 tools/exclusion_gate.py

Returns JSON to stdout:
    {
        "excluded_domains": [...],
        "crm_companies": [...],
        "crm_emails": [...],
        "reason_map": {"domain.com": "companydb", "email@x.com": "crm"}
    }

Note: Apollo contacts are NOT included — that's a separate API call, not sheets.
"""

import json
import subprocess
import sys


def _run_sheets_cmd(command: str):
    """Run a sheets_helper.py command and return parsed JSON."""
    result = subprocess.run(
        ["python3", "tools/sheets_helper.py", command],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"WARNING: {command} failed: {result.stderr.strip()}", file=sys.stderr)
        return {}
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"WARNING: {command} returned invalid JSON", file=sys.stderr)
        return {}


def main():
    # 1. Company DB excluded domains
    companydb_data = _run_sheets_cmd("companydb-excluded-domains")
    excluded_domains = companydb_data.get("excluded_domains", [])

    # 2. CRM dedup set (emails + name×company pairs)
    crm_data = _run_sheets_cmd("crm-dedup-set")
    crm_emails = crm_data.get("emails", [])
    crm_companies = crm_data.get("name_company_pairs", [])

    # Build reason map
    reason_map = {}
    for domain in excluded_domains:
        reason_map[domain] = "companydb"
    for email in crm_emails:
        reason_map[email] = "crm"
    for pair in crm_companies:
        reason_map[pair] = "crm"

    output = {
        "excluded_domains": excluded_domains,
        "crm_companies": crm_companies,
        "crm_emails": crm_emails,
        "reason_map": reason_map,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
