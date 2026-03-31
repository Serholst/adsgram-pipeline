#!/usr/bin/env python3
"""
Merge Discoverer + Enricher + Pre-Enricher outputs into crm-writer-input.json.

Replaces the Orchestrator's 80-line "Сборка пакета для CRM Writer" section.
Reads from /tmp/pipeline/ files, applies field mapping per contracts,
writes /tmp/pipeline/crm-writer-input.json.

Usage:
    python3 tools/assemble_crm_package.py \
        --vertical "iGaming" \
        --session-query "iGaming Brazil"

Input:
    /tmp/pipeline/discoverer-output.json  (required)
    /tmp/pipeline/enricher-output.json    (optional — absent if no leads needed enrichment)
    /tmp/pipeline/pre-enricher-output.json (required)

Output:
    /tmp/pipeline/crm-writer-input.json
    stdout: JSON summary
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PIPELINE_DIR = Path("/tmp/pipeline")
DISCOVERER_PATH = PIPELINE_DIR / "discoverer-output.json"
ENRICHER_PATH = PIPELINE_DIR / "enricher-output.json"
PRE_ENRICHER_PATH = PIPELINE_DIR / "pre-enricher-output.json"
OUTPUT_PATH = PIPELINE_DIR / "crm-writer-input.json"

# verification_status → lead_status mapping (from Orchestrator AGENT.md)
VERIFICATION_TO_LEAD_STATUS = {
    "VERIFIED": "Verified",
    "PARTIALLY_VERIFIED": "Partially verified",
    "NOT_VERIFIED": "Not verified",
    "ROLE_DISCREPANCY": "Not verified",
    "LEFT_COMPANY": "Skip",
    "SKIP": "Skip",
}


def _die(msg: str):
    print(json.dumps({"error": msg}))
    sys.exit(1)


def _load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        _die(f"Invalid JSON in {path}: {e}")


def _build_pe_lookup(pre_enricher: dict) -> dict:
    """Build company_domain → {company_contacts, industry_signals} lookup."""
    lookup = {}
    for company in pre_enricher.get("companies", []):
        domain = company.get("company_domain")
        if domain:
            lookup[domain] = {
                "company_contacts": company.get("company_contacts"),
                "industry_signals": company.get("industry_signals", []),
            }
    return lookup


def _contacts_field(lead: dict, field: str):
    """Get field from contacts_found, falling back to top-level."""
    contacts = lead.get("contacts_found", {})
    val = contacts.get(field)
    if val is not None:
        return val
    return lead.get(field)


def _assemble_ready(lead: dict, enriched: dict | None, pe_lookup: dict, vertical: str | None) -> dict:
    """Assemble CRM Writer input for a READY lead (with or without enrichment)."""
    contacts = lead.get("contacts_found", {})
    domain = lead.get("company_domain", "")
    pe_data = pe_lookup.get(domain, {})

    if enriched:
        enrichment_flags = enriched.get("enrichment_flags", [])
        email_source = "enricher_apollo"
        if "FREE_PATH_USED" in enrichment_flags:
            email_source = "enricher_free_path"
        return {
            "apollo_person_id": enriched.get("apollo_person_id"),
            "first_name": enriched.get("first_name", ""),
            "last_name": enriched.get("last_name", ""),
            "title": enriched.get("title", ""),
            "company": enriched.get("company", ""),
            "company_domain": domain,
            "country": enriched.get("country"),
            "seniority": enriched.get("seniority"),
            "vertical": vertical,
            "source_bucket": "READY",
            "verification_status": enriched.get("verification_status", ""),
            "verification_note": enriched.get("verification_note", ""),
            "lead_status": VERIFICATION_TO_LEAD_STATUS.get(enriched.get("verification_status", ""), "Not verified"),
            "headline": enriched.get("headline"),
            "role_description": enriched.get("role_description"),
            "email": enriched.get("email"),
            "email_status": enriched.get("email_status"),
            "email_source": email_source if enriched.get("email") else None,
            "phone": enriched.get("phone") or contacts.get("phone"),
            "linkedin_url": enriched.get("linkedin_url") or contacts.get("linkedin_url"),
            "twitter": contacts.get("twitter"),
            "instagram": contacts.get("instagram"),
            "telegram_handle": contacts.get("telegram_handle"),
            "whatsapp": contacts.get("whatsapp"),
            "conference_appearances": contacts.get("conference_appearances", []),
            "contact_sources": contacts.get("sources", []),
            "enrichment_flags": enrichment_flags,
            "enrichment_note": enriched.get("enrichment_note"),
            "flags": enriched.get("flags", []),
            "company_contacts": pe_data.get("company_contacts"),
            "industry_signals": pe_data.get("industry_signals", []),
        }

    return {
        "apollo_person_id": lead.get("apollo_person_id"),
        "first_name": lead.get("first_name", ""),
        "last_name": lead.get("last_name", ""),
        "title": lead.get("title", ""),
        "company": lead.get("company", ""),
        "company_domain": domain,
        "country": lead.get("country"),
        "seniority": lead.get("seniority"),
        "vertical": vertical,
        "source_bucket": "READY",
        "verification_status": lead.get("verification_status", ""),
        "verification_note": lead.get("verification_note", ""),
        "lead_status": VERIFICATION_TO_LEAD_STATUS.get(lead.get("verification_status", ""), "Not verified"),
        "headline": lead.get("headline"),
        "role_description": lead.get("role_description"),
        "email": contacts.get("email_pattern"),
        "email_status": "unverified" if contacts.get("email_pattern") else None,
        "email_source": "discoverer_pattern" if contacts.get("email_pattern") else None,
        "phone": contacts.get("phone"),
        "linkedin_url": contacts.get("linkedin_url"),
        "twitter": contacts.get("twitter"),
        "instagram": contacts.get("instagram"),
        "telegram_handle": contacts.get("telegram_handle"),
        "whatsapp": contacts.get("whatsapp"),
        "conference_appearances": contacts.get("conference_appearances", []),
        "contact_sources": contacts.get("sources", []),
        "enrichment_flags": [],
        "enrichment_note": None,
        "flags": lead.get("flags", []),
        "company_contacts": pe_data.get("company_contacts"),
        "industry_signals": pe_data.get("industry_signals", []),
    }


def _assemble_skip(lead: dict, pe_lookup: dict, vertical: str | None) -> dict:
    """Assemble CRM Writer input for a SKIP lead."""
    contacts = lead.get("contacts_found", {})
    domain = lead.get("company_domain", "")
    pe_data = pe_lookup.get(domain, {})

    return {
        "apollo_person_id": lead.get("apollo_person_id"),
        "first_name": lead.get("first_name", ""),
        "last_name": lead.get("last_name", ""),
        "title": lead.get("title", ""),
        "company": lead.get("company", ""),
        "company_domain": domain,
        "country": lead.get("country"),
        "seniority": lead.get("seniority"),
        "vertical": vertical,
        "source_bucket": "SKIP",
        "verification_status": lead.get("verification_status", "SKIP"),
        "verification_note": lead.get("verification_note", ""),
        "lead_status": "Skip",
        "headline": lead.get("headline"),
        "role_description": lead.get("role_description"),
        "email": contacts.get("email_pattern"),
        "email_status": "unverified" if contacts.get("email_pattern") else None,
        "email_source": "discoverer_pattern" if contacts.get("email_pattern") else None,
        "phone": contacts.get("phone"),
        "linkedin_url": contacts.get("linkedin_url"),
        "twitter": contacts.get("twitter"),
        "instagram": contacts.get("instagram"),
        "telegram_handle": contacts.get("telegram_handle"),
        "whatsapp": contacts.get("whatsapp"),
        "conference_appearances": contacts.get("conference_appearances", []),
        "contact_sources": contacts.get("sources", []),
        "enrichment_flags": [],
        "enrichment_note": None,
        "flags": lead.get("flags", []),
        "company_contacts": pe_data.get("company_contacts"),
        "industry_signals": pe_data.get("industry_signals", []),
    }


def main():
    parser = argparse.ArgumentParser(description="Assemble CRM Writer input from pipeline outputs")
    parser.add_argument("--vertical", type=str, default=None, help="Vertical (iGaming/VPN/Crypto/Adult)")
    parser.add_argument("--session-query", type=str, required=True, help="Original user query")
    args = parser.parse_args()

    # Load inputs
    discoverer = _load_json(DISCOVERER_PATH)
    if discoverer is None:
        _die(f"Discoverer output not found: {DISCOVERER_PATH}")

    pre_enricher = _load_json(PRE_ENRICHER_PATH)
    if pre_enricher is None:
        _die(f"Pre-Enricher output not found: {PRE_ENRICHER_PATH}")

    enricher = _load_json(ENRICHER_PATH)  # May be None if no leads needed enrichment

    # Build pre-enricher lookup
    pe_lookup = _build_pe_lookup(pre_enricher)

    # Build enricher lookup (by apollo_person_id for matching)
    enricher_leads = {}
    if enricher:
        for lead in enricher.get("leads", []):
            pid = lead.get("apollo_person_id")
            if pid:
                enricher_leads[pid] = lead

    # Process discoverer leads
    assembled = []
    counts = {"ready": 0, "skip": 0}

    for lead in discoverer.get("leads", []):
        bucket = lead.get("bucket", "SKIP")

        if bucket == "READY":
            pid = lead.get("apollo_person_id")
            enriched = enricher_leads.get(pid) if pid and lead.get("needs_enrichment") else None
            assembled.append(_assemble_ready(lead, enriched, pe_lookup, args.vertical))
            counts["ready"] += 1

        else:  # SKIP
            assembled.append(_assemble_skip(lead, pe_lookup, args.vertical))
            counts["skip"] += 1

    output = {
        "write_metadata": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_leads": len(assembled),
            "from_ready": counts["ready"],
            "from_skip": counts["skip"],
            "session_query": args.session_query,
        },
        "leads": assembled,
    }

    PIPELINE_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    summary = {
        "status": "ok",
        "total_leads": len(assembled),
        "ready": counts["ready"],
        "skip": counts["skip"],
        "output_file": str(OUTPUT_PATH),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
