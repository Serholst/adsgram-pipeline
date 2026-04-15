#!/usr/bin/env python3
"""
File-based data handoff between pipeline agents.

Each agent writes its full output to data/pipeline/<agent>-output.json
and returns only lightweight metadata to the Orchestrator.

Usage from agents (via Bash tool):
    python3 tools/pipeline_io.py write <agent> <json_file>
    python3 tools/pipeline_io.py read <agent>
    python3 tools/pipeline_io.py status <agent>
    python3 tools/pipeline_io.py clean
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_DIR = _SCRIPT_DIR.parent
PIPELINE_DIR = Path(os.environ.get("PIPELINE_DATA_DIR", str(_PROJECT_DIR / "data" / "pipeline")))
STATE_FILE = PIPELINE_DIR / "pipeline-state.json"

KNOWN_AGENTS = {
    "pre-enricher",
    "searcher",
    "discoverer",
    "enricher",
    "crm-writer",
}

# Ordered pipeline steps for checkpoint/resume
PIPELINE_STEPS = [
    "exclusion",
    "companydb-write-1",
    "pre-enricher",
    "searcher",
    "discoverer",
    "checkpoint-1",
    "enricher",
    "assemble-crm",
    "crm-writer",
    "companydb-write-2",
    "outreach-writer",
    "gmail-drafter",
    "crm-update-drafts",
    "summary",
]


def ensure_dir():
    PIPELINE_DIR.mkdir(parents=True, exist_ok=True)


def _output_path(agent: str) -> Path:
    return PIPELINE_DIR / f"{agent}-output.json"


def _status_path(agent: str) -> Path:
    return PIPELINE_DIR / f"{agent}-status.json"


def _die(msg: str):
    print(json.dumps({"error": msg}), file=sys.stdout)
    sys.exit(1)


def _output(data):
    print(json.dumps(data, ensure_ascii=False, indent=2))


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_write(agent: str, json_file: str):
    """Save agent output and extract metadata for Orchestrator."""
    ensure_dir()

    if not Path(json_file).exists():
        _die(f"File not found: {json_file}")

    try:
        with open(json_file) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        _die(f"Invalid JSON in {json_file}: {e}")

    # Write full output
    out_path = _output_path(agent)
    with open(out_path, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # Extract and write lightweight status
    status = _extract_status(agent, data)
    with open(_status_path(agent), "w") as f:
        json.dump(status, f, ensure_ascii=False, indent=2)

    _output(status)


def cmd_read(agent: str):
    """Read full agent output from disk."""
    path = _output_path(agent)
    if not path.exists():
        _die(f"No output found for agent '{agent}'. Expected at {path}")

    with open(path) as f:
        data = json.load(f)
    _output(data)


def cmd_status(agent: str):
    """Read lightweight status for agent (what Orchestrator needs)."""
    path = _status_path(agent)
    if not path.exists():
        _die(f"No status found for agent '{agent}'. Has it completed?")

    with open(path) as f:
        data = json.load(f)
    _output(data)


def cmd_clean(keep_state: bool = False):
    """Remove all pipeline files. Call at the start of a new session.

    Args:
        keep_state: If True, preserve pipeline-state.json (for retry/resume).
    """
    if not PIPELINE_DIR.exists():
        _output({"status": "ok", "removed": 0})
        return

    removed = 0
    for f in PIPELINE_DIR.iterdir():
        if f.is_file() and f.suffix == ".json":
            if keep_state and f.name == "pipeline-state.json":
                continue
            f.unlink()
            removed += 1
    _output({"status": "ok", "removed": removed})


def cmd_list():
    """List all agent outputs currently on disk."""
    if not PIPELINE_DIR.exists():
        _output({"agents": []})
        return

    agents = []
    for f in sorted(PIPELINE_DIR.glob("*-output.json")):
        name = f.stem.replace("-output", "")
        size = f.stat().st_size
        agents.append({"agent": name, "file": str(f), "size_bytes": size})
    _output({"agents": agents})


# ---------------------------------------------------------------------------
# State management — checkpoint / resume for autonomous mode
# ---------------------------------------------------------------------------

def _read_state() -> dict:
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def _write_state(state: dict):
    ensure_dir()
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def cmd_checkpoint(step: str):
    """Record that a pipeline step completed successfully."""
    if step not in PIPELINE_STEPS:
        _die(f"Unknown step: {step}. Valid steps: {', '.join(PIPELINE_STEPS)}")

    state = _read_state()
    completed = state.get("steps_completed", [])
    if step not in completed:
        completed.append(step)
    state["steps_completed"] = completed
    state["last_completed_step"] = step
    if "started_at" not in state:
        state["started_at"] = datetime.now(timezone.utc).isoformat()
    _write_state(state)

    _output({"status": "ok", "step": step, "total_completed": len(completed)})


def cmd_resume():
    """Determine which step to resume from, or 'start' if no state."""
    state = _read_state()
    if not state or "last_completed_step" not in state:
        _output({"next_step": "start"})
        return

    last = state["last_completed_step"]
    try:
        idx = PIPELINE_STEPS.index(last)
    except ValueError:
        _output({"next_step": "start"})
        return

    if idx + 1 >= len(PIPELINE_STEPS):
        _output({"next_step": "done", "query": state.get("query", {}),
                 "completed": state.get("steps_completed", [])})
        return

    next_step = PIPELINE_STEPS[idx + 1]
    _output({
        "next_step": next_step,
        "query": state.get("query", {}),
        "completed": state.get("steps_completed", []),
        "last_completed": last,
    })


def cmd_set_query(json_str: str):
    """Save pipeline query parameters (vertical, geo) for resume."""
    try:
        query = json.loads(json_str)
    except json.JSONDecodeError as e:
        _die(f"Invalid JSON: {e}")

    state = _read_state()
    state["query"] = query
    if "started_at" not in state:
        state["started_at"] = datetime.now(timezone.utc).isoformat()
    _write_state(state)

    _output({"status": "ok", "query": query})


# ---------------------------------------------------------------------------
# Status extraction — returns only what Orchestrator needs for decisions
# ---------------------------------------------------------------------------

def _extract_status(agent: str, data: dict) -> dict:
    """Extract lightweight metadata from full agent output."""
    status = {
        "agent": agent,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "done",
    }

    if agent == "pre-enricher":
        meta = data.get("pre_enrichment_metadata", {})
        companies = data.get("companies", [])
        status["companies_processed"] = meta.get("companies_processed", len(companies))
        status["companies_enriched"] = meta.get("companies_enriched", 0)
        status["companies_failed"] = meta.get("companies_failed", 0)
        status["parent_companies_discovered"] = meta.get("parent_companies_discovered", 0)
        status["decision_makers_found"] = meta.get("decision_makers_found", 0)
        status["recommendation"] = meta.get("recommendation")
        # Orchestrator needs this to decide retry strategy
        status["company_domains"] = [c.get("company_domain") for c in companies if c.get("company_domain")]
        status["has_parent_companies"] = meta.get("parent_companies_discovered", 0) > 0
        status["has_person_names"] = meta.get("decision_makers_found", 0) > 0

    elif agent == "searcher":
        meta = data.get("search_metadata", {})
        leads = data.get("leads", [])
        status["total_leads"] = len(leads)
        status["domains_searched"] = meta.get("domains_searched", 0)
        status["credits_spent"] = meta.get("credits_spent", 0)
        status["recommendation"] = meta.get("recommendation")
        # Orchestrator needs domains_audit for retry decisions
        status["domains_audit"] = data.get("domains_audit", [])

    elif agent == "discoverer":
        meta = data.get("discoverer_metadata", {})
        status["total_processed"] = meta.get("total_processed", 0)
        status["ready"] = meta.get("ready", 0)
        status["needs_enrichment_count"] = meta.get("needs_enrichment_count", 0)
        status["skipped"] = meta.get("skipped", 0)
        status["verified"] = meta.get("verified", 0)
        status["partially_verified"] = meta.get("partially_verified", 0)

    elif agent == "enricher":
        meta = data.get("enricher_metadata", {})
        status["credits_spent"] = meta.get("credits_spent", 0)
        status["credits_remaining"] = meta.get("credits_remaining", 0)
        status["emails_found"] = meta.get("emails_found", 0)
        status["emails_not_found"] = meta.get("emails_not_found", 0)
        status["success_rate"] = meta.get("success_rate", 0)
        status["recommendation"] = meta.get("recommendation")

    elif agent == "crm-writer":
        # crm_writer.py output is already lightweight
        for key in ("rows_written", "rows_rejected", "rows_duplicate",
                     "company_db_updated", "companies_added", "escalation",
                     "recommendation"):
            if key in data:
                status[key] = data[key]
        status["status"] = data.get("status", "done")

    return status


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

COMMANDS = {
    "write": 2,       # agent, json_file
    "read": 1,        # agent
    "status": 1,      # agent
    "clean": 0,
    "list": 0,
    "checkpoint": 1,  # step_name
    "resume": 0,
    "set-query": 1,   # json_string
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print("Usage: pipeline_io.py <command> [args]")
        print("\nCommands:")
        print("  write <agent> <json_file>  — save agent output, return status")
        print("  read <agent>               — read full agent output")
        print("  status <agent>             — read lightweight status")
        print("  clean [--keep-state]       — remove pipeline files (optionally keep state)")
        print("  list                       — list all agent outputs on disk")
        print("  checkpoint <step>          — record completed step")
        print("  resume                     — get next step to execute")
        print("  set-query <json>           — save query params for resume")
        sys.exit(0)

    cmd = sys.argv[1]
    if cmd not in COMMANDS:
        _die(f"Unknown command: {cmd}")

    nargs = COMMANDS[cmd]
    args = sys.argv[2:]

    # Special handling for clean --keep-state
    if cmd == "clean":
        keep_state = "--keep-state" in args
        cmd_clean(keep_state=keep_state)
    elif len(args) < nargs:
        _die(f"Command '{cmd}' requires {nargs} argument(s), got {len(args)}")
    elif cmd == "write":
        cmd_write(args[0], args[1])
    elif cmd == "read":
        cmd_read(args[0])
    elif cmd == "status":
        cmd_status(args[0])
    elif cmd == "list":
        cmd_list()
    elif cmd == "checkpoint":
        cmd_checkpoint(args[0])
    elif cmd == "resume":
        cmd_resume()
    elif cmd == "set-query":
        cmd_set_query(args[0])


if __name__ == "__main__":
    main()
