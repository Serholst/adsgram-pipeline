---
name: adsgram-autopipeline
version: 3.0.0
description: "Automated AdsGram prospecting pipeline: takes a vertical+GEO, runs demand-side discovery to find companies with active acquisition budgets, then delegates to the Orchestrator agent which runs the full 7-agent chain (Pre-Enricher → Searcher → Discoverer → Enricher → CRM Writer → Outreach Writer) with two checkpoints. Trigger when user says: 'автопоиск', 'autopipeline', 'запусти пайплайн', 'автопроспектинг', 'pipeline iGaming Brazil', 'найди лидов автоматом', or any prospecting request. Also trigger on: 'найди лидов', 'поиск контактов', 'prospecting', 'find leads'. Input MUST be vertical+GEO format (e.g. 'iGaming Brazil', 'VPN Turkey'). Domain lists are not supported."
---

# AdsGram Auto-Pipeline

This skill is a thin entry point that delegates to the **Orchestrator agent** for the full prospecting → outreach cycle. The Orchestrator manages all 7 agents, retry logic, data routing, and checkpoints internally.

## Step 0 → REQUEST CLASSIFICATION

Before spawning any agents, classify the user's request:

### Type A: Outreach only
Triggers: «напиши письмо», «подготовь аутрич», «write outreach», «сделай питч», or any request that only asks to write/send emails for existing leads.
→ **Skip this skill entirely.** Delegate to the `adsgram-outreach` skill instead. Do NOT ask clarifying questions — the user just wants to write emails.

### Type B: Full pipeline (prospecting + outreach)
Triggers: «найди лидов», «autopipeline», «prospecting», «запусти пайплайн», vertical+GEO request, or any request that involves finding new leads.
→ **Proceed to Step 0.5: Confirm understanding.**

## Step 0.5 → CONFIRM UNDERSTANDING

Before launching the pipeline, confirm the request with the user. Present a brief summary:

```
Запускаю пайплайн:
- Вертикаль: [vertical]
- Регион: [GEO — list specific countries if ambiguous]
- Что ищем: компании с активным бюджетом на привлечение пользователей
- Целевые роли: Media Buyer, UA Manager, Growth, Performance Marketing
- Исключения: [companies already in CRM/CompanyDB for this vertical+GEO]

Всё верно?
```

**When to ask clarifying questions (before the summary):**
- Vertical missing or ambiguous → «Какая вертикаль? iGaming / VPN / Crypto / Adult»
- GEO missing or too broad → «Какой регион? Конкретные страны?»
  - "Europe" is broad — clarify: Western Europe? Nordics? CIS? Specific countries?
  - "LATAM" is acceptable (defined in ICP: Brazil, Mexico, Argentina, Colombia)
  - "Asia" is acceptable (defined in ICP: India, Singapore, Indonesia, Philippines, Vietnam)
- GEO not in ICP → warn: «[X] не в нашем ICP. Продолжить?»
- Vertical + GEO combo already heavily prospected → warn: «В базе уже N компаний по [vertical] [GEO]. Искать новые?»

**Do NOT ask clarifying questions when:**
- Request is clear: "VPN Europe", "iGaming Brazil", "crypto LATAM"
- User explicitly says to proceed: "запусти", "go", "давай"

Wait for user confirmation before proceeding to Step 1.

## Step 1 → PREFLIGHT (silent, no user interaction)

Before spawning the Orchestrator, run infrastructure checks automatically.
The user should NOT see or confirm any of this — it happens silently.

```bash
# Load .env so all tools have credentials
set -a && source .env && set +a

# Run preflight — checks credentials, Gmail token, Apollo
python3 tools/preflight.py --json
```

**If preflight passes** → proceed to Step 2 silently. Do not mention preflight to the user.

**If preflight fails** → analyze which checks failed:

| Failed check | Action |
|---|---|
| `env_file` | Stop. Tell user: «Не найден .env или отсутствуют переменные: [list]. Настрой .env по .env.example» |
| `google_credentials` | Stop. Tell user: «Google credentials не найдены или невалидны. Проверь GOOGLE_CREDENTIALS_PATH в .env» |
| `gmail_token` | **Warning only, don't stop.** Pipeline can run without Gmail — drafts just won't be created at the end. Tell user: «Gmail token не найден — черновики не будут созданы. Продолжить поиск без Gmail?» |
| `telegram_bot` | **Skip silently in interactive mode.** TG bot needed only for autonomous. |
| `pipeline_mode` | **Set automatically:** `export PIPELINE_MODE=interactive`. Not an error. |
| `apollo_credits` | **Warning if 0 credits.** Tell user: «Apollo credits = 0. Enrichment будет недоступен. Продолжить?» If API unreachable (403/timeout) — **skip silently**, Apollo works via MCP in interactive mode. |

**Key principle:** In interactive mode, the only preflight failures that stop the pipeline are missing .env and missing Google credentials. Everything else is either auto-fixed, warned, or skipped.

## Step 2 → ORCHESTRATOR

Spawn the Orchestrator agent:

```
Read agent-system/agents/orchestrator/AGENT.md.
Read agent-system/config/agent-config.md.
Task: [user's request]
Run the full prospecting → outreach pipeline.
The Orchestrator will pause at two checkpoints:
  - CHECKPOINT 1: enrichment credit approval (after Discoverer)
  - CHECKPOINT 2: pitch approval (after Outreach Writer)
```

The Orchestrator internally runs:
Pre-Enricher → Searcher → Discoverer → [CP1] → Enricher → CRM Writer (Python script) → Outreach Writer → [CP2]

Data flows through files in `data/pipeline/`, not through Orchestrator context.
CRM Writer is a Python script (`tools/crm_writer.py`), not a Claude agent.

Wait for the Orchestrator to complete. It will return a SUMMARY with funnel metrics.

---

## Step 3 → GMAIL DRAFTER

After the Orchestrator completes and pitches are approved (CP2), spawn the Gmail Drafter:

```
Read the skill at agent-system/skills/gmail-drafter/SKILL.md.
Create Gmail drafts for approved pitches: [list with To, Subject, Body from Orchestrator output]
Return draft confirmations.
```

Drafts appear in Gmail for manual review. User sends manually.

---

## Step 4 → Summary

Print combined results:
- Orchestrator SUMMARY (funnel, credits, recommendations)
- Gmail Drafter results (drafts created, any failures)

---

## Language

Communicate with the user in Russian.
