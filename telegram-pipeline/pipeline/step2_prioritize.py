"""
Step 2 — Prioritization: Assign segment via YAML-driven tier lookups.

Pure Python logic — no external API calls.
ALL lookup tables live in BIZ.prioritization. Zero hardcoded logic.

Tier computation:
1. fit_level × intent_level → base_tier (from tier_matrix)
2. chat_type → promotion (from chat_promotion)
3. For Advertiser roles: adv_telegram_intent × adv_readiness → adv_tier
4. Final segment = max(promoted_tier, adv_tier)
"""

import logging
from config import BIZ

logger = logging.getLogger(__name__)

# Ordered from lowest to highest for comparison
TIER_ORDER = {"Defer": 0, "Cold": 1, "Warm": 2, "Hot": 3}
TIER_BY_RANK = {v: k for k, v in TIER_ORDER.items()}


def _tier_rank(tier: str) -> int:
    """Convert tier name to numeric rank for comparison."""
    return TIER_ORDER.get(tier, 0)


def _promote(tier: str, steps: int) -> str:
    """Promote a tier by N steps (capped at Hot)."""
    rank = _tier_rank(tier)
    new_rank = min(rank + steps, 3)
    return TIER_BY_RANK.get(new_rank, tier)


def _max_tier(a: str, b: str) -> str:
    """Return the higher of two tiers."""
    return a if _tier_rank(a) >= _tier_rank(b) else b


def run(lead: dict) -> dict:
    """
    Step 2: Look up segment from fit/intent/chat tiers.
    Updates lead in-place and returns it.
    """
    msg_role = lead.get("msg_role", "")
    cfg = BIZ.prioritization

    # Note: Trash role and irrelevant leads are already filtered in main.py
    # before this step is called. No need to check here.

    # --- 1. Base tier from fit_level × intent_level ---
    fit = lead.get("fit_level", "low") or "low"
    intent = lead.get("intent_level", "low") or "low"
    tier_matrix = cfg.get("tier_matrix", {})
    base_tier = tier_matrix.get(f"{fit}_{intent}", "Defer")

    # --- 2. Chat relevance promotion ---
    chat_rel = lead.get("chat_type", "general") or "general"
    chat_promo = cfg.get("chat_promotion", {})
    promo_steps = chat_promo.get(chat_rel, 0)
    promoted_tier = _promote(base_tier, promo_steps)

    # --- 3. Advertiser override ---
    if msg_role == "Advertiser":
        adv_intent = lead.get("adv_telegram_intent") or "none"
        adv_readiness = lead.get("adv_readiness") or "passive"
        adv_matrix = cfg.get("advertiser_tier_matrix", {})
        adv_tier = adv_matrix.get(f"{adv_intent}_{adv_readiness}", "Defer")
        segment = _max_tier(promoted_tier, adv_tier)
    else:
        segment = promoted_tier

    lead["segment"] = segment

    logger.debug(
        "Step2 @%s: role=%s fit=%s intent=%s base=%s chat=%s→%s final=%s",
        lead.get("handle"), msg_role, fit, intent,
        base_tier, chat_rel, promoted_tier, segment,
    )
    return lead
