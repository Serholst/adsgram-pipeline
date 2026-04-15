# AdsGram Pipeline

## Что это
Мультиагентный пайплайн B2B-prospecting + cold outreach через Apollo API + Gmail.
Вертикали: iGaming, VPN, Crypto, Adult. Работает автономно на VPS по cron-расписанию.

## Режимы работы
- **autonomous** (`PIPELINE_MODE=autonomous`) — VPS/cron, решения по финансам через Telegram-бот, CP2/CP2.5 пропускаются
- **interactive** (по умолчанию) — оператор в чате Claude Code, все checkpoints ручные

## Entry points
- `run_pipeline.sh <vertical> <geo>` — shell wrapper для cron: lockfile, retry с exp. backoff (30 мин окно), TG-нотификации
- `run_pipeline.sh --scheduled` — читает `schedule.conf` по дню недели
- `/autopipeline <vertical> <geo>` — интерактивный запуск через skill

## Архитектура
Orchestrator (`agent-system/agents/orchestrator/AGENT.md`) координирует цепочку агентов.
Данные между агентами — файлы в `data/pipeline/` (через `tools/pipeline_io.py`).
Python-скрипты вызываются через Bash. Apollo API — через MCP tools.

### Цепочка агентов
```
Pre-Enricher → Searcher → Discoverer → [Enricher] → CRM Writer → Outreach Writer → Gmail Drafter
```

### Ключевые скрипты
- `tools/pipeline_io.py` — межагентный I/O, checkpoints, resume
- `tools/tg_approval.py` — TG: approval/notify/error (env: TG_BOT_TOKEN, TG_OPERATOR_CHAT_ID)
- `tools/crm_writer.py` — валидация + запись в Google Sheets CRM
- `tools/assemble_enricher_input.py` — сборка входа для Enricher
- `tools/assemble_crm_package.py` — мерж данных всех агентов для CRM
- `tools/exclusion_gate.py` — дедупликация и exclusion check

## Checkpoints
- **CP1** (enrichment credits) — в autonomous: `tg_approval.py approval`, timeout = skip enrichment
- **CP2** (pitches) — в autonomous: пропускается, оператор ревьюит черновики в Gmail
- **CP2.5** (draft preview) — в autonomous: пропускается

## Resume
При crash: `pipeline_io.py` хранит state в `data/pipeline/`. Shell wrapper делает retry,
Orchestrator проверяет `pipeline_io.py resume` и продолжает с последнего checkpoint.

## Правила
- НЕ тратить Apollo credits без одобрения (CP1 обязателен даже в autonomous)
- Gmail черновики ТОЛЬКО через `create_drafts.py`, НИКОГДА через MCP gmail_create_draft
- В autonomous mode все уведомления через Telegram
- Логи: `logs/runs/` (shell), `logs/retrospectives/` (агент)
- Env vars: см. `.env.example`
