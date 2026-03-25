# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
```

## Running the Pipeline

```bash
# Standard run (filter by BD manager)
python main.py --manager Sergey

# Ignore saved state, reprocess all leads
python main.py --manager Sergey --fresh

# Test with first N leads only
python main.py --manager Sergey --fresh --limit 20
```

The pipeline requires `.env` and `credentials.json` in the project root. After a successful run, `results.json` is written for local analysis.

## Architecture

3-step sequential enrichment pipeline per Telegram lead:

```
Google Sheet (source) → deduplicate by handle
  → Step 1: Message analysis (LLM) + deterministic fit scoring — classify role, extract signals, compute fit_score from YAML weights
  → Step 2: Prioritization → segment (pure Python, no external calls)
  → Step 3: Playbook selection + draft pitch generation (LLM) [Hot/Warm/Cold only]
→ scored_{SOURCE_SHEET_NAME} sheet (same spreadsheet) + auto-generated "Легенда" legend sheet
```

**Short-circuit rules:**
- Trash after Step 1 → skip Steps 2–3
- Irrelevant after Step 1 → mark Exclude, skip Steps 2–3
- Defer after Step 2 → skip Step 3 (too cold for pitch)

**Dedup against scored sheet** — on each run, handles already present in `scored_` sheet are skipped. Use `--fresh` to clear and reprocess from scratch.

## Key Design Decisions

**Business logic is never hardcoded.** All thresholds, segment boundaries, and advertiser matrix live in `business/*.yaml` and are loaded at startup via `config.BIZ`. Edit YAML files to tune prioritization — never put numbers in Python files.

**Fit scoring is deterministic.** Step 1 LLM extracts structured `fit_sub_signals` (vertical, role, ownership, etc.). Python then computes `fit_score` using weights from `business/fit_scoring.yaml`. This overrides the LLM's `fit_level` for Advertiser/Publisher roles. Agency/Unclear roles keep the LLM `fit_level`.

**Bio comes from the source sheet** column defined by `SOURCE_BIO_COLUMN`.

**LLM static context caching.** In `clients/llm.py`, pass niche/GEO lists and product description as `static_context` (goes into system prompt). DeepSeek caches repeated system prompts automatically.

**Playbooks are YAML-driven.** Each role has a playbook file in `business/playbooks/` defining pitch angle, talking points, and personalization variables. The LLM in Step 3 uses the selected playbook to generate a personalized draft pitch.

**SCORED_COLUMNS in `config.py`** is the single source of truth for scored sheet column order. Changing it requires clearing and re-initializing the scored sheet headers (`ensure_scored_headers()` handles this automatically).

## Adding/Modifying Features

- **Segment thresholds & role modifiers** → edit `business/prioritization.yaml`
- **Advertiser intent×readiness matrix** → edit `business/prioritization.yaml` → `advertiser_matrix`
- **Fit scoring weights & thresholds** → edit `business/fit_scoring.yaml`
- **Niche tiers** → edit `business/niches.yaml`
- **Playbooks (outreach templates)** → edit/add files in `business/playbooks/*.yaml`
- **LLM prompts** → edit `prompts/*.txt` (Jinja2 templates)
- **New scored column** → add to `SCORED_COLUMNS` and `COLUMN_DESCRIPTIONS` in `config.py`/`clients/sheets.py`

## Environment Setup

Copy `.env.example` → `.env` and fill in:
- `SOURCE_SHEET_ID` — Google Sheet ID (scored results written to `scored_{SOURCE_SHEET_NAME}` sheet in same spreadsheet)
- `GOOGLE_CREDENTIALS_PATH` — path to service account JSON (default: `credentials.json`)
- `DEEPSEEK_API_KEY`
