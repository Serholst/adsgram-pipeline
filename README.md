# AdsGram BD System

Multi-agent BD prospecting system for [AdsGram.ai](https://adsgram.ai) — Telegram-native advertising platform.

## Architecture

```
agent-system/             — Claude multi-agent pipeline
  agents/                   Agent role definitions (AGENT.md)
  skills/                   Instruction sets (SKILL.md)
  contracts/                JSON schemas for inter-agent data contracts
  config/                   Shared agent configuration

telegram-scoring/         — Python: Telegram chat lead scoring & pitch generation
tools/                    — Shared utilities (Google Sheets CLI)
media/                    — Case study images for pitches
logs/                     — Session logs, feedback, retrospectives
```

## Agent Pipeline

7-agent system orchestrated by Claude Code:

1. **Pre-Enricher** — Company-level web recon (parent companies, decision makers, email patterns)
2. **Searcher** — Apollo people search armed with Pre-Enricher context
3. **Discoverer** — Per-lead: LinkedIn + role verification + bucket assignment (Ready/Skip + needs_enrichment flag)
4. **Enricher** — Apollo paid enrichment for leads needing enrichment (1 credit/lead, checkpoint approval)
5. **CRM Writer** — Validate & write to Google Sheets CRM + Company DB
6. **Outreach Writer** — Personalized cold emails with CPM/CTR benchmarks
7. **Orchestrator** — Chains all stages, manages credits, writes retrospectives

## Telegram Scoring

Standalone Python pipeline for scoring leads from BD Telegram chats:

```bash
python telegram-scoring/main.py --manager Sergey [--fresh] [--limit 20]
```

## Setup

```bash
cp .env.example .env
# Fill in: APOLLO_API_KEY, CRM_SHEET_ID, COMPANYDB_SHEET_ID, GOOGLE_CREDENTIALS_PATH
```

## Target Verticals

iGaming, VPN, Crypto, Adult — decision-makers (Media Buyers, UA Managers, Growth/Performance Marketing).

## CRM

Production CRM lives in Google Sheets (not in this repo). See `data/README.md`.
