"""
Step 3 — Playbook selection + Draft pitch generation (LLM).

Selects appropriate playbook based on msg_role, then generates
a personalized draft pitch using LLM with subtype determination.

Only runs for Hot, Warm, Cold segments. Defer/Trash/Exclude skip this step.
"""

import json
import logging
from pathlib import Path

import yaml
from jinja2 import Template

from clients.llm import LLMClient
from config import BIZ, SKIP_SEGMENTS, PITCH_ROLES

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "pitch_generation.txt"
PLAYBOOK_DIR = Path(__file__).parent.parent / "business" / "playbooks"

LLM_EXPECTED_KEYS = ["playbook", "subtype", "pitch_variables", "draft_pitch"]


# ---------------------------------------------------------------------------
# Playbook loading (once at module import)
# ---------------------------------------------------------------------------

def _load_playbooks() -> dict[str, dict]:
    """Load all playbook YAML files from business/playbooks/."""
    playbooks: dict[str, dict] = {}
    for path in PLAYBOOK_DIR.glob("*.yaml"):
        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            role_key = data.get("role", path.stem)
            playbooks[role_key] = data
        except Exception as e:
            logger.warning("Failed to load playbook %s: %s", path, e)
    return playbooks


_PLAYBOOKS = _load_playbooks()
_PROMPT_TEMPLATE = Template(PROMPT_PATH.read_text(encoding="utf-8"))

# Static context for LLM caching: product info + ALL playbook YAMLs
# All playbooks are included so the system prompt stays stable across leads.
_ALL_PLAYBOOKS_YAML = yaml.dump(
    {pb.get("role", "unknown"): pb for pb in _PLAYBOOKS.values()},
    allow_unicode=True, default_flow_style=False, sort_keys=False,
)
_STATIC_CONTEXT = (
    f"Product: {BIZ.product.get('short_description', '')}\n\n"
    f"All available playbooks:\n{_ALL_PLAYBOOKS_YAML}"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _select_playbook(msg_role: str) -> dict:
    """Select playbook by role. Falls back to 'default'."""
    role_key = msg_role if msg_role in PITCH_ROLES else "default"
    return _PLAYBOOKS.get(role_key, _PLAYBOOKS.get("default", {}))


def _playbook_yaml_for_prompt(playbook: dict) -> str:
    """Serialize selected playbook to YAML for the user prompt."""
    return yaml.dump(playbook, allow_unicode=True, default_flow_style=False, sort_keys=False)


# ---------------------------------------------------------------------------
# Main step
# ---------------------------------------------------------------------------

def run(lead: dict, llm: LLMClient) -> dict:
    """
    Step 3: Select playbook and generate draft pitch via LLM.
    Updates lead in-place and returns it.
    Only called for Hot/Warm/Cold segments (skip logic is in main.py).
    """
    msg_role = lead.get("msg_role", "")
    playbook = _select_playbook(msg_role)
    lead["playbook"] = playbook.get("name", "General Introduction")

    # Build user prompt with all available context
    user_prompt = _PROMPT_TEMPLATE.render(
        msg_role=msg_role,
        segment=lead.get("segment", ""),
        message_text=lead.get("messages_combined", ""),
        profile_bio=lead.get("profile_bio_sheet", ""),
        niche_signal=lead.get("msg_niche_signal") or "",
        geo_signal=lead.get("msg_geo_signal") or "",
        channel_handle=lead.get("msg_channel_handle") or "",
        adsgram_relevant=lead.get("adsgram_relevant", ""),
        adv_telegram_intent=lead.get("adv_telegram_intent") or "",
        adv_readiness=lead.get("adv_readiness") or "",
        sender_name=lead.get("sender_name", ""),
        playbook_yaml=_playbook_yaml_for_prompt(playbook),
    )

    result = llm.analyze(
        user_prompt, LLM_EXPECTED_KEYS,
        static_context=_STATIC_CONTEXT,
        max_tokens=1024,
    )

    # --- Subtype handling ---
    subtype = result.get("subtype") or ""
    if subtype not in ("A", "B", "C"):
        subtype = playbook.get("default_subtype", "B")
    lead["subtype"] = subtype

    # Serialize pitch_variables as JSON string for sheet output
    pv = result.get("pitch_variables")
    if isinstance(pv, dict):
        lead["pitch_variables"] = json.dumps(pv, ensure_ascii=False)
    elif pv:
        lead["pitch_variables"] = str(pv)
    else:
        lead["pitch_variables"] = None

    lead["draft_pitch"] = result.get("draft_pitch")

    logger.debug(
        "Step3 @%s: playbook=%s subtype=%s pitch_len=%d",
        lead.get("handle"),
        lead.get("playbook"),
        lead.get("subtype"),
        len(lead.get("draft_pitch") or ""),
    )
    return lead
