#!/usr/bin/env python3
"""
Merge company contact data from Pre-Enricher and Enricher outputs.

Reads pre-enricher-output.json and enricher-output.json from the pipeline
directory, merges contact information per company, and outputs JSON
suitable for sheets_helper.py companydb-update-cells.

Merge rules:
  - Enricher data supplements Pre-Enricher data
  - If both sources have "phone", Enricher (Apollo) wins (more accurate)
  - Null/empty fields are excluded from output
  - Pre-Enricher provides: general_email, press_email, partnerships_email,
    social_links (twitter, instagram, telegram, tiktok)
  - Enricher provides: phone, raw_address, linkedin_url,
    estimated_num_employees, revenue_printed

Usage:
    python3 tools/merge_company_contacts.py
    python3 tools/merge_company_contacts.py --dry-run
    python3 tools/merge_company_contacts.py --save data/pipeline/companies_post.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from pipeline_io import PIPELINE_DIR


def _die(msg: str):
    print(json.dumps({"error": msg}))
    sys.exit(1)


def _load_json(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        _die(f"Invalid JSON in {path}: {e}")


def _build_pe_contacts(pre_enricher: dict) -> dict:
    """Build domain -> company_contacts lookup from Pre-Enricher output."""
    lookup = {}
    for company in pre_enricher.get("companies", []):
        domain = company.get("company_domain")
        if not domain:
            continue
        cc = company.get("company_contacts") or {}
        social = cc.get("social_links") or {}
        lookup[domain] = {
            "company_name": company.get("company_name") or company.get("brand_name", ""),
            "general_email": cc.get("general_email"),
            "press_email": cc.get("press_email"),
            "partnerships_email": cc.get("partnerships_email"),
            "phone": cc.get("phone"),
            "twitter": social.get("twitter"),
            "instagram": social.get("instagram"),
            "telegram": social.get("telegram"),
            "tiktok": social.get("tiktok"),
        }
    return lookup


def _build_enricher_org_data(enricher: dict) -> dict:
    """Build domain -> organization_data lookup from Enricher output."""
    org_data = enricher.get("organization_data", {})
    # organization_data is keyed by domain
    if isinstance(org_data, dict):
        return org_data
    return {}


def merge_contacts(pre_enricher: dict, enricher: Optional[dict]) -> list[dict]:
    """Merge company contacts from both sources.

    Returns list of dicts ready for companydb-update-cells:
    [{"company": "...", "updates": {"Company Contacts": "...", ...}}]
    """
    pe_contacts = _build_pe_contacts(pre_enricher)
    enricher_orgs = _build_enricher_org_data(enricher) if enricher else {}

    # Collect all domains from both sources
    all_domains = set(pe_contacts.keys()) | set(enricher_orgs.keys())

    results = []
    for domain in sorted(all_domains):
        pe = pe_contacts.get(domain, {})
        eo = enricher_orgs.get(domain, {})

        company_name = pe.get("company_name") or eo.get("name", "")
        if not company_name:
            continue

        # Build Company Contacts string
        contact_parts = []

        # Enricher organization_data fields
        # Phone: Enricher wins if both have it
        phone = eo.get("phone") or pe.get("phone")
        if phone:
            contact_parts.append(f"Phone: {phone}")

        address = eo.get("raw_address")
        if address:
            contact_parts.append(f"Address: {address}")

        employees = eo.get("estimated_num_employees")
        if employees:
            contact_parts.append(f"Employees: {employees}")

        linkedin = eo.get("linkedin_url")
        if linkedin:
            contact_parts.append(f"LinkedIn: {linkedin}")

        # Pre-Enricher company_contacts fields
        for field in ("general_email", "press_email", "partnerships_email"):
            val = pe.get(field)
            if val:
                label = field.replace("_", " ").title()
                contact_parts.append(f"{label}: {val}")

        # Social links from Pre-Enricher
        for field in ("twitter", "instagram", "telegram", "tiktok"):
            val = pe.get(field)
            if val:
                contact_parts.append(f"{field.title()}: {val}")

        if not contact_parts:
            continue

        company_contacts_str = " | ".join(contact_parts)

        updates = {"Company Contacts": company_contacts_str}

        # Revenue: update only if Enricher has it (Orchestrator checks if cell is empty)
        revenue = eo.get("revenue_printed")
        if revenue:
            updates["Est. Revenue 2024 ($M)"] = revenue

        # Marketing Intel supplement from Enricher
        intel_parts = []
        if employees:
            intel_parts.append(f"Apollo: {employees} employees")
        if revenue:
            intel_parts.append(f"Revenue: {revenue}")
        if intel_parts:
            updates["Marketing Intel (Apollo)"] = " | ".join(intel_parts)

        results.append({
            "company": company_name,
            "domain": domain,
            "updates": updates,
        })

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Merge company contacts from Pre-Enricher and Enricher outputs"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print merge result without saving"
    )
    parser.add_argument(
        "--save", type=str, default=None,
        help="Save output to file (default: stdout only)"
    )
    args = parser.parse_args()

    # Load inputs
    pe_path = PIPELINE_DIR / "pre-enricher-output.json"
    enricher_path = PIPELINE_DIR / "enricher-output.json"

    pre_enricher = _load_json(pe_path)
    if pre_enricher is None:
        _die(f"Pre-Enricher output not found: {pe_path}")

    enricher = _load_json(enricher_path)  # May be None

    # Merge
    batch = merge_contacts(pre_enricher, enricher)

    if not batch:
        result = {"status": "empty", "companies": 0, "message": "No company contacts to merge"}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    # Save if requested
    if args.save and not args.dry_run:
        save_path = Path(args.save)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, "w") as f:
            json.dump(batch, f, ensure_ascii=False, indent=2)

    # Output
    output = {
        "status": "ok",
        "companies": len(batch),
        "batch": batch,
    }
    if args.dry_run:
        output["dry_run"] = True

    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
