"""
AdsGram Outreach Pipeline — main entry point.

Usage:
    python main.py [--manager NAME] [--fresh] [--limit N]
"""

import argparse
import json
import logging
import sys
from collections import defaultdict
from datetime import datetime, timezone

# Import config first — fails fast on missing secrets or broken YAMLs
import config
import gspread.exceptions
from openai import APIStatusError, APITimeoutError, APIConnectionError
from clients.sheets import SheetsClient
from clients.llm import LLMClient
from pipeline import step1_message, step2_prioritize, step3_pitch

MAX_CONSECUTIVE_ERRORS = 10

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pre-processing
# ---------------------------------------------------------------------------

def get_manager(args) -> str:
    if args.manager:
        return args.manager
    default = config.BD_MANAGER_DEFAULT
    try:
        choice = input(f"BD Manager filter [{default}]: ").strip()
    except (EOFError, KeyboardInterrupt):
        choice = ""
    return choice or default


import re

_EMOJI_RE = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map
    "\U0001F1E0-\U0001F1FF"  # flags
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "\U0001f900-\U0001f9FF"  # supplemental
    "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF"
    "\U00002600-\U000026FF"
    "\U0000FE00-\U0000FE0F"  # variation selectors
    "\U0000200D"              # ZWJ
    "\U0000200B-\U0000200F"  # zero-width
    "]+",
    flags=re.UNICODE,
)


def _normalize(text: str) -> str:
    """Collapse whitespace for dedup comparison."""
    return " ".join(text.split()).lower()


def _clean_bio(bio: str, max_len: int = 200) -> str:
    """Strip emoji, collapse whitespace, truncate."""
    text = _EMOJI_RE.sub("", bio)
    text = " ".join(text.split()).strip()
    if len(text) > max_len:
        text = text[:max_len].rsplit(" ", 1)[0] + "…"
    return text


def deduplicate_by_handle(rows: list[dict], manager: str) -> list[dict]:
    """
    Group rows by Telegram handle, merge messages, count sources.
    Rows with no handle are skipped (logged).
    """
    by_handle: dict[str, dict] = {}
    skipped_no_handle = 0

    for row in rows:
        handle = row.get(config.SOURCE_HANDLE_COLUMN, "").strip()
        if not handle:
            skipped_no_handle += 1
            continue

        if handle not in by_handle:
            by_handle[handle] = {
                "handle": handle,
                "profile_bio_sheet": row.get(config.SOURCE_BIO_COLUMN, ""),
                "reason": row.get(config.SOURCE_REASON_COLUMN, ""),
                "offer_suggestion": row.get(config.SOURCE_OFFER_COLUMN, ""),
                "bd_manager": manager,
                "_messages": [],
                "_msg_seen": set(),
                "_chat_names": [],
                "source_count": 0,
            }

        msg = row.get(config.SOURCE_MESSAGE_COLUMN, "").strip()
        if msg:
            norm = _normalize(msg)
            if norm not in by_handle[handle]["_msg_seen"]:
                by_handle[handle]["_msg_seen"].add(norm)
                by_handle[handle]["_messages"].append(msg)
        chat_name = row.get(config.SOURCE_CHAT_COLUMN, "").strip()
        if chat_name and chat_name not in by_handle[handle]["_chat_names"]:
            by_handle[handle]["_chat_names"].append(chat_name)
        by_handle[handle]["source_count"] += 1

    if skipped_no_handle:
        logger.warning("Skipped %d rows with no Telegram handle", skipped_no_handle)

    leads = []
    for data in by_handle.values():
        messages = data.pop("_messages")
        data.pop("_msg_seen")
        chat_names = data.pop("_chat_names")
        bio = _clean_bio(str(data.get("profile_bio_sheet", "")))
        parts = []
        if bio:
            parts.append(f"[BIO] {bio}")
        if messages:
            parts.extend(messages)
        combined = "\n---\n".join(parts)
        if data["source_count"] > 1:
            combined += f"\n\n[{data['source_count']} msgs found]"
        data["messages_combined"] = combined
        data["chat_names_combined"] = " | ".join(chat_names) if chat_names else ""
        leads.append(data)

    return leads


# ---------------------------------------------------------------------------
# Pipeline runner
# ---------------------------------------------------------------------------

def _record_error(stats: dict) -> bool:
    """Increment error counters. Returns True if should abort (too many consecutive errors)."""
    stats["errors"] += 1
    stats["consecutive_errors"] += 1
    return stats["consecutive_errors"] >= MAX_CONSECUTIVE_ERRORS


def _zero_fill_new_fields(lead: dict):
    """Fill step 2-3 fields with None for leads that short-circuit early."""
    for key in ("segment", "playbook", "subtype", "pitch_variables", "draft_pitch"):
        lead.setdefault(key, None)


def run_pipeline(lead: dict, llm: LLMClient) -> dict:
    """Run all 3 steps on a lead. Returns enriched lead dict."""

    # Step 1 — Message analysis + fit scoring
    lead = step1_message.run(lead, llm)
    if lead.get("msg_role") == "Trash":
        lead["segment"] = "Trash"
        _zero_fill_new_fields(lead)
        return lead

    # Irrelevant filter (was in step3_reconcile)
    if lead.get("adsgram_relevant") == "irrelevant":
        lead["segment"] = "Exclude"
        _zero_fill_new_fields(lead)
        return lead

    # Step 2 — Prioritization (pure Python)
    lead = step2_prioritize.run(lead)

    # Defer short-circuit: too cold for pitch generation
    if lead.get("segment") in config.SKIP_SEGMENTS:
        _zero_fill_new_fields(lead)
        return lead

    # Step 3 — Playbook + Pitch (LLM; only Hot/Warm/Cold reach here)
    lead["sender_name"] = config.SENDER_NAME
    lead = step3_pitch.run(lead, llm)

    return lead


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="AdsGram Outreach Pipeline — score and segment Telegram publishers"
    )
    parser.add_argument(
        "--manager", help="BD Manager filter value (default: from .env BD_MANAGER_DEFAULT)"
    )
    parser.add_argument(
        "--status", nargs="*", default=None,
        help="Filter by source 'status' column. Use 'empty' for blank cells. Example: --status empty interested"
    )
    parser.add_argument(
        "--fresh", action="store_true",
        help="Clear scored sheet and reprocess all leads from scratch"
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Process only the first N leads (for testing)"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    manager = get_manager(args)
    logger.info("BD Manager filter: %s", manager)

    # Initialize clients
    sheets = SheetsClient()
    if args.fresh:
        sheets.clear_scored_sheet()
    sheets.ensure_scored_headers()
    sheets.ensure_legend_sheet()

    # Load + filter + dedup source rows
    all_rows = sheets.read_source_rows()
    filtered = [r for r in all_rows if str(r.get(config.BD_MANAGER_COLUMN, "")).strip() == manager]

    # Status filter
    if args.status is not None:
        status_values = set()
        allow_empty = False
        for s in args.status:
            if s.lower() == "empty":
                allow_empty = True
            else:
                status_values.add(s.lower())

        def _status_match(row):
            val = str(row.get(config.SOURCE_STATUS_COLUMN, "")).strip()
            if not val:
                return allow_empty
            return val.lower() in status_values

        before_status = len(filtered)
        filtered = [r for r in filtered if _status_match(r)]
        logger.info("Status filter %s: %d → %d rows", args.status, before_status, len(filtered))

    deduped = deduplicate_by_handle(filtered, manager)

    # Skip handles already in scored sheet (unless --fresh)
    already_scored = sheets.read_scored_handles() if not args.fresh else set()
    if already_scored:
        before = len(deduped)
        deduped = [lead for lead in deduped if lead["handle"] not in already_scored]
        logger.info("Skipped %d already-scored handles", before - len(deduped))

    logger.info(
        "Source: %d total → %d after filters → %d after dedup → %d to process",
        len(all_rows), len(filtered), len(deduped) + len(already_scored), len(deduped),
    )

    if not deduped:
        print(f"\nNo new leads to process for BD Manager: '{manager}'")
        sys.exit(0)

    if args.limit is not None:
        deduped = deduped[:args.limit]
        logger.info("--limit %d applied: processing first %d leads", args.limit, len(deduped))

    # Stats counters
    stats: dict[str, int] = defaultdict(int)
    results_log: list[dict] = []

    llm = LLMClient()

    for idx, lead in enumerate(deduped):
        handle = lead.get("handle", f"row_{idx}")
        logger.info("[%d/%d] Processing: %s", idx + 1, len(deduped), handle)

        try:
            lead = run_pipeline(lead, llm)

            lead["processed_at"] = datetime.now(timezone.utc).isoformat()

            sheets.write_scored_row(lead)
            stats["processed"] += 1

            # Track segment and role distribution
            seg = lead.get("segment") or lead.get("msg_role") or "Unknown"
            stats[f"seg_{seg}"] += 1
            role = lead.get("msg_role") or "Unknown"
            stats[f"role_{role}"] += 1

            # Append to in-memory results log (written at end of run)
            results_log.append(lead)
            stats["consecutive_errors"] = 0

        except KeyboardInterrupt:
            logger.info("\nInterrupted by user at lead %d/%d.", idx + 1, len(deduped))
            break
        except Exception as e:
            if isinstance(e, (gspread.exceptions.APIError,
                              APIStatusError, APITimeoutError, APIConnectionError)):
                logger.warning("API error processing %s (will continue): %s", handle, e)
            else:
                logger.error("Unexpected error processing %s: %s", handle, e, exc_info=True)
            if _record_error(stats):
                logger.error("Aborting: %d consecutive errors.", stats["consecutive_errors"])
                break

    # Write results log to file for local analysis
    results_file = config.BASE_DIR / "results.json"
    results_file.write_text(
        json.dumps(results_log, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    logger.info("Results written to %s (%d leads)", results_file, len(results_log))

    # End-of-run summary
    print("\n" + "=" * 40)
    print("=== Run Complete ===")
    print(f"Processed : {stats['processed']}")
    print(
        f"Hot: {stats.get('seg_Hot', 0)}  |  "
        f"Warm: {stats.get('seg_Warm', 0)}  |  "
        f"Cold: {stats.get('seg_Cold', 0)}  |  "
        f"Defer: {stats.get('seg_Defer', 0)}  |  "
        f"Exclude: {stats.get('seg_Exclude', 0)}  |  "
        f"Trash: {stats.get('seg_Trash', 0)}"
    )
    # Dynamic role distribution
    role_counts = {k.removeprefix("role_"): v for k, v in stats.items() if k.startswith("role_")}
    if role_counts:
        role_parts = [f"{role}: {count}" for role, count in sorted(role_counts.items())]
        print(f"Roles — {' | '.join(role_parts)}")
    if stats["errors"]:
        print(f"Errors     : {stats['errors']}")
    print(f"Written to : {config.SOURCE_SHEET_ID} — {config.SCORED_SHEET_NAME}")
    print("=" * 40)


if __name__ == "__main__":
    main()
