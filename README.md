# AdsGram Pipeline

Automated lead prospecting, enrichment, and outreach pipeline for [AdsGram.ai](https://adsgram.ai) — Telegram-native advertising platform.

## Architecture

```
skills/           — Claude/OpenClaw skill definitions (SKILL.md)
agents/           — Agent role definitions (AGENT.md)
contracts/        — JSON schemas for inter-agent data contracts
apollo-cli/       — Python CLI for Apollo.io API (search, enrich, manage credits)
telegram-pipeline/— Telegram chat scoring & outreach pipeline (Python)
docs/             — ICP documents, BD rules, outreach frameworks
config/           — Agent configuration
media/            — Case study images for pitches
data/             — CRM data (gitignored — lives in Google Sheets)
logs/             — Session logs, feedback, retrospectives (templates in git)
```

## Pipeline Flow

1. **Prospector** — Apollo people search → web verification → enrichment
2. **Outreach Writer** — Personalized cold emails with CPM/CTR benchmarks
3. **Telegram Sender** — Score leads from BD chats → send pitches via Telegram
4. **Autopipeline** — Orchestrator that chains all stages with approval checkpoints

## Setup

```bash
cp .env.example .env
# Fill in: ANTHROPIC_API_KEY, APOLLO_API_KEY, TELEGRAM_BOT_TOKEN, GOOGLE_SHEETS_SPREADSHEET_ID
```

## Target Verticals

iGaming, VPN, Crypto, Adult — decision-makers (Media Buyers, UA Managers, Growth/Performance Marketing).

## CRM

Production CRM lives in Google Sheets (not in this repo). See `data/README.md`.
