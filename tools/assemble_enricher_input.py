#!/usr/bin/env python3
"""
Extract needs_enrichment leads from discoverer-output.json → enricher-input.json.

Replaces the Orchestrator's manual extraction of enrichment-needed leads
(Orchestrator AGENT.md "Сборка пакета для Enricher" section).

Usage:
    python3 tools/assemble_enricher_input.py \
        --approved-budget 20 \
        --current-balance 45 \
        --session-query "iGaming Brazil"

Input:  data/pipeline/discoverer-output.json
Output: data/pipeline/enricher-input.json
Stdout: JSON summary
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from pipeline_io import PIPELINE_DIR
DISCOVERER_OUTPUT = PIPELINE_DIR / "discoverer-output.json"
ENRICHER_INPUT = PIPELINE_DIR / "enricher-input.json"

# Fields to copy from discoverer lead to enricher input
PASSTHROUGH_FIELDS = [
    "apollo_person_id", "first_name", "last_name", "title",
    "company", "company_domain", "country", "seniority",
    "verification_status", "verification_note",
]


def _die(msg: str):
    print(json.dumps({"error": msg}))
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Assemble enricher input from discoverer output")
    parser.add_argument("--approved-budget", type=int, required=True, help="Credits approved by user")
    parser.add_argument("--current-balance", type=int, required=True, help="Current Apollo credit balance")
    parser.add_argument("--session-query", type=str, required=True, help="Original user query")
    args = parser.parse_args()

    if not DISCOVERER_OUTPUT.exists():
        _die(f"Discoverer output not found: {DISCOVERER_OUTPUT}")

    try:
        with open(DISCOVERER_OUTPUT) as f:
            discoverer = json.load(f)
    except json.JSONDecodeError as e:
        _die(f"Invalid JSON in discoverer output: {e}")

    leads = discoverer.get("leads", [])
    needs_enrichment = [l for l in leads if l.get("bucket") == "READY" and l.get("needs_enrichment")]

    if not needs_enrichment:
        result = {"status": "empty", "total_needs_enrichment": 0, "message": "No leads need enrichment"}
        print(json.dumps(result, indent=2))
        return

    enricher_leads = []
    for lead in needs_enrichment:
        el = {}
        for field in PASSTHROUGH_FIELDS:
            el[field] = lead.get(field)

        # Extract linkedin_url to top level (Enricher uses as fallback)
        contacts = lead.get("contacts_found", {})
        el["linkedin_url"] = contacts.get("linkedin_url")

        # Passthrough contacts_found entirely
        el["contacts_found"] = contacts

        enricher_leads.append(el)

    output = {
        "enrichment_metadata": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_leads": len(enricher_leads),
            "approved_budget": args.approved_budget,
            "current_balance": args.current_balance,
            "session_query": args.session_query,
        },
        "leads": enricher_leads,
    }

    PIPELINE_DIR.mkdir(parents=True, exist_ok=True)
    with open(ENRICHER_INPUT, "w") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    summary = {
        "status": "ok",
        "total_needs_enrichment": len(enricher_leads),
        "output_file": str(ENRICHER_INPUT),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
