"""
Step 1 — LLM: Analyze message text, bio, and chat context.

Extracts role, channel handle, niche signal, GEO, fit/intent levels,
and chat relevance from the combined inputs. Short or non-textual
messages are marked Trash without an LLM call (saves tokens).
"""

import json
import re
import logging
from pathlib import Path
from docx import Document
from jinja2 import Template
from clients.llm import LLMClient, validate_enum
from config import BIZ, ROLES

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "message_analysis.txt"
EXPECTED_KEYS = [
    "msg_role", "adsgram_relevant", "msg_channel_handle", "msg_niche_signal", "msg_geo_signal",
    "fit_level", "intent_level", "fit_signals", "intent_signals", "chat_type",
    "adv_telegram_intent", "adv_readiness",
    # Agency/Dev Studio enrichment
    "agency_type", "agency_scale", "dev_studio_signals",
    # Fit sub-signals for deterministic scoring
    "fit_sub_signals",
]


def _is_trash_prefilter(text: str) -> bool:
    """True if message is too short or contains no meaningful text.

    Handles CJK (Chinese/Japanese/Korean) which has no spaces between words,
    so word-count heuristic alone would incorrectly reject valid messages.
    """
    stripped = text.strip()
    if len(stripped) < 15:
        return True
    # Count CJK characters (Chinese, Japanese Hiragana/Katakana)
    cjk_chars = len(re.findall(r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff]', stripped))
    if cjk_chars >= 5:
        return False  # enough CJK content — not trash
    # Latin/Cyrillic: require at least 5 whitespace-separated tokens
    if len(stripped.split()) < 5:
        return True
    # Require at least one meaningful 3+ letter word
    return not bool(re.search(r'[a-zA-Zа-яА-ЯёЁ]{3,}', stripped))


def _load_icp_text(filename: str) -> str:
    """Read text content from a .docx ICP document (returns empty string if missing)."""
    path = Path(__file__).parent.parent / filename
    if not path.exists():
        logger.warning("ICP file not found: %s", path)
        return ""
    doc = Document(str(path))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


# Build once at module load (static, never changes during a run)
_NICHE_LIST = ", ".join(n["name"] for n in BIZ.niches.get("niches", []))
_GEO_LIST = ", ".join(BIZ.prioritization.get("geo_codes", []))
_PROMPT_TEMPLATE = Template(PROMPT_PATH.read_text(encoding="utf-8"))
_ICP_ADVERTISER = _load_icp_text("AdsGram_ICP_Advertisers.docx")
_ICP_PUBLISHER = _load_icp_text("AdsGram_ICP_Publishers.docx")

# Static context → system prompt (DeepSeek caches repeated system prompts automatically).
# ICP docs are stable across leads, so including them here saves tokens vs. user prompt.
_STATIC_PARTS = [f"Available niches: {_NICHE_LIST}", f"Available GEO codes: {_GEO_LIST}"]
if _ICP_ADVERTISER:
    _STATIC_PARTS.append(f"--- ICP ADVERTISER (reference for fit assessment) ---\n{_ICP_ADVERTISER}")
if _ICP_PUBLISHER:
    _STATIC_PARTS.append(f"--- ICP PUBLISHER (reference for fit assessment) ---\n{_ICP_PUBLISHER}")
_STATIC_CONTEXT = "\n\n".join(_STATIC_PARTS)

_LEVEL_ALLOWED = {"high", "medium", "low"}

# Default values for all Step 1 output fields — used by trash prefilter.
# Single source of truth: if EXPECTED_KEYS changes, update this dict.
_TRASH_DEFAULTS: dict[str, str | None] = {
    "msg_role": "Trash",
    "adsgram_relevant": "irrelevant",
    "fit_level": "low",
    "intent_level": "low",
    "fit_signals": "[]",
    "intent_signals": "[]",
    "chat_type": "general",
    "msg_channel_handle": None,
    "msg_niche_signal": None,
    "msg_geo_signal": None,
    "adv_telegram_intent": None,
    "adv_readiness": None,
    "agency_type": None,
    "agency_scale": None,
    "dev_studio_signals": "[]",
    "fit_sub_signals": "{}",
    "fit_score": None,
    "fit_scoring": None,
}


def _validate_signals_list(value) -> list[str]:
    """Ensure fit_signals / intent_signals is a list of strings."""
    if isinstance(value, list):
        return [str(s) for s in value if s]
    if isinstance(value, str):
        # LLM might return a comma-separated string
        return [s.strip() for s in value.split(",") if s.strip()]
    return []


def _signals_to_json(raw) -> str:
    """Validate a signals list and serialize to JSON string."""
    return json.dumps(_validate_signals_list(raw), ensure_ascii=False)


# ---------------------------------------------------------------------------
# Fit scoring — deterministic score from LLM sub-signals + YAML weights
# ---------------------------------------------------------------------------

def _validate_fit_sub_signals(raw) -> dict:
    """Validate and normalize fit_sub_signals from LLM response."""
    defaults = {
        "vertical_name": None,
        "role_in_bio": None,
        "has_telegram_presence": False,
        "has_anti_icp": False,
        "anti_icp_reason": None,
        "ownership_strength": "none",
        "has_commercial_activity": False,
        "niche_tier": None,
    }
    if not isinstance(raw, dict):
        return defaults

    result = {}
    result["vertical_name"] = raw.get("vertical_name") or None
    result["role_in_bio"] = raw.get("role_in_bio") or None
    result["has_telegram_presence"] = bool(raw.get("has_telegram_presence"))
    result["has_anti_icp"] = bool(raw.get("has_anti_icp"))
    result["anti_icp_reason"] = raw.get("anti_icp_reason") or None
    result["ownership_strength"] = validate_enum(
        raw.get("ownership_strength"),
        {"explicit", "moderate", "weak", "none"},
        default="none",
    )
    result["has_commercial_activity"] = bool(raw.get("has_commercial_activity"))

    niche_tier = raw.get("niche_tier")
    if niche_tier in (1, 2, 3, "1", "2", "3"):
        result["niche_tier"] = int(niche_tier)
    else:
        result["niche_tier"] = None

    return result


def _score_to_level(score: int, thresholds: dict) -> str:
    """Convert numeric score to fit_level using YAML thresholds."""
    if score >= thresholds["high"]:
        return "high"
    if score >= thresholds["medium"]:
        return "medium"
    return "low"


def _lookup_score(value: str, score_map: dict) -> int:
    """Look up score from a YAML weight map: exact → case-insensitive → substring → default."""
    if not value:
        return score_map.get("default", 0)
    if value in score_map:
        return score_map[value]
    lower = value.lower()
    for key, val in score_map.items():
        if key != "default" and key.lower() == lower:
            return val
    for key, val in score_map.items():
        if key != "default" and key.lower() in lower:
            return val
    return score_map.get("default", 0)


def _compute_fit_score(msg_role: str, sub_signals: dict, chat_type: str) -> dict | None:
    """
    Compute deterministic fit_score from sub-signals using YAML weights.
    Returns dict with details/total/max/fit_level, or None for non-scored roles.
    """
    cfg = BIZ.fit_scoring
    details = []

    if msg_role == "Publisher":
        pub_cfg = cfg["publisher"]

        ownership = sub_signals.get("ownership_strength", "none")
        ownership_score = pub_cfg["ownership_strength"].get(ownership, 0)
        details.append({"signal": "ownership_strength", "value": ownership, "score": ownership_score})

        niche_tier = sub_signals.get("niche_tier")
        niche_key = f"tier_{niche_tier}" if niche_tier else "default"
        niche_score = pub_cfg["niche"].get(niche_key, pub_cfg["niche"].get("default", 0))
        details.append({"signal": "niche", "value": niche_key, "score": niche_score})

        comm_score = pub_cfg["commercial_activity"] if sub_signals.get("has_commercial_activity") else 0
        details.append({"signal": "commercial_activity", "value": sub_signals.get("has_commercial_activity"), "score": comm_score})

        chat_score = pub_cfg["chat_context_boost"] if chat_type == "publisher" else 0
        details.append({"signal": "chat_context_boost", "value": chat_type, "score": chat_score})

        total = ownership_score + niche_score + comm_score + chat_score
        max_score = pub_cfg["max_score"]

    elif msg_role == "Advertiser":
        adv_cfg = cfg["advertiser"]

        if sub_signals.get("has_anti_icp"):
            details.append({"signal": "anti_icp", "value": sub_signals.get("anti_icp_reason"), "score": 0})
            return {
                "details": details,
                "total": 0,
                "max": adv_cfg["max_score"],
                "fit_level": _score_to_level(0, cfg["thresholds"]),
            }

        vertical = sub_signals.get("vertical_name") or ""
        vertical_map = adv_cfg["vertical"]
        vertical_score = _lookup_score(vertical, vertical_map)
        details.append({"signal": "vertical", "value": vertical, "score": vertical_score})

        role = sub_signals.get("role_in_bio") or ""
        role_map = adv_cfg["role_seniority"]
        role_score = _lookup_score(role, role_map)
        details.append({"signal": "role_seniority", "value": role, "score": role_score})

        tg_score = adv_cfg["telegram_presence"] if sub_signals.get("has_telegram_presence") else 0
        details.append({"signal": "telegram_presence", "value": sub_signals.get("has_telegram_presence"), "score": tg_score})

        total = vertical_score + role_score + tg_score
        max_score = adv_cfg["max_score"]

    else:
        return None

    fit_level = _score_to_level(total, cfg["thresholds"])
    return {
        "details": details,
        "total": total,
        "max": max_score,
        "fit_level": fit_level,
    }


def run(lead: dict, llm: LLMClient) -> dict:
    """
    Step 1: Analyze message text, bio, and chat context with LLM.
    Updates lead in-place and returns it.
    """
    message = lead.get("messages_combined", "").strip()

    if _is_trash_prefilter(message):
        logger.info("Step1 pre-filter Trash: @%s (too short/no text)", lead.get("handle"))
        lead.update(_TRASH_DEFAULTS)
        return lead

    user_prompt = _PROMPT_TEMPLATE.render(
        message_text=message,
        profile_bio=lead.get("profile_bio_sheet", "") or "",
        chat_name=lead.get("chat_names_combined", "") or "",
        niche_list=_NICHE_LIST,
        geo_list=_GEO_LIST,
        icp_advertiser="",  # now in _STATIC_CONTEXT (system prompt, cached)
        icp_publisher="",   # now in _STATIC_CONTEXT (system prompt, cached)
    )

    result = llm.analyze(user_prompt, EXPECTED_KEYS, static_context=_STATIC_CONTEXT)
    result["msg_role"] = validate_enum(
        result.get("msg_role"),
        ROLES,
        default="Unclear",
    )
    result["adsgram_relevant"] = validate_enum(
        result.get("adsgram_relevant"),
        {"relevant", "irrelevant", "unclear"},
        default="unclear",
    )
    result["fit_level"] = validate_enum(
        result.get("fit_level"), _LEVEL_ALLOWED, default="low",
    )
    result["intent_level"] = validate_enum(
        result.get("intent_level"), _LEVEL_ALLOWED, default="low",
    )
    result["chat_type"] = validate_enum(
        result.get("chat_type"),
        {"ad_traffic", "publisher", "agency", "general"},
        default="general",
    )
    # Normalize signal lists to JSON strings for sheet output
    result["fit_signals"] = _signals_to_json(result.get("fit_signals"))
    result["intent_signals"] = _signals_to_json(result.get("intent_signals"))
    result["adv_telegram_intent"] = validate_enum(
        result.get("adv_telegram_intent"),
        {"direct", "indirect", "none"},
        default=None,
    )
    result["adv_readiness"] = validate_enum(
        result.get("adv_readiness"),
        {"active", "exploring", "passive"},
        default=None,
    )
    # Validate agency/dev studio enrichment fields
    result["agency_type"] = validate_enum(
        result.get("agency_type"),
        {"kol_network", "media_buying", "dev_studio", "general_marketing", "unknown"},
        default=None,
    )
    result["agency_scale"] = validate_enum(
        result.get("agency_scale"),
        {"large", "medium", "small", "unknown"},
        default=None,
    )
    result["dev_studio_signals"] = _signals_to_json(result.get("dev_studio_signals"))
    lead.update(result)
    # Force null for non-Advertiser roles (LLM may hallucinate values)
    if lead.get("msg_role") != "Advertiser":
        lead["adv_telegram_intent"] = None
        lead["adv_readiness"] = None
    # Null agency fields for non-Agency roles
    if lead.get("msg_role") not in ("Agency",):
        lead["agency_type"] = None
        lead["agency_scale"] = None
        lead["dev_studio_signals"] = "[]"

    # --- Fit sub-signals validation and scoring ---
    sub_signals = _validate_fit_sub_signals(result.get("fit_sub_signals"))
    scoring_result = _compute_fit_score(
        lead.get("msg_role", "Unclear"),
        sub_signals,
        lead.get("chat_type", "general"),
    )
    if scoring_result is not None:
        lead["fit_level"] = scoring_result["fit_level"]
        lead["fit_score"] = scoring_result["total"]
        lead["fit_scoring"] = json.dumps(scoring_result, ensure_ascii=False)
    else:
        lead["fit_score"] = None
        lead["fit_scoring"] = None
    lead["fit_sub_signals"] = json.dumps(sub_signals, ensure_ascii=False)

    if "llm_error" in result:
        logger.warning(
            "Step1 LLM error for @%s — check API key/quota. llm_error=%s",
            lead.get("handle"), result.get("llm_error"),
        )
    else:
        logger.debug("Step1 result for @%s: role=%s", lead.get("handle"), lead.get("msg_role"))
    return lead
