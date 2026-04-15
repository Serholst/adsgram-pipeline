# Аудит текущего состояния AdsGram Pipeline

**Дата:** 2026-04-05
**Версия пайплайна:** v1.7.0
**Цель:** Оценить готовность к автономной работе на VPS

---

## Диаграммы

- [Sequence Diagram — взаимодействие компонентов](sequence-pipeline.puml)
- [Activity Diagram — бизнес-шаги](activity-pipeline.puml)

---

## 1. Текстовый отчёт аудита

### 1.1 Компоненты и их роли

| Компонент | Тип | Назначение | Headless-ready? |
|---|---|---|---|
| **Autopipeline** | SKILL.md (entry point) | Точка входа, делегирует Orchestrator | Да |
| **Orchestrator** | AGENT.md (Claude agent) | Координация цепочки, checkpoints, retry | **Нет** — 3 checkpoint'а ждут человека |
| **Pre-Enricher** | AGENT.md (Claude agent) | Web-разведка по компаниям | Да |
| **Searcher** | AGENT.md (Claude agent) | Apollo People Search + fallback | Да |
| **Discoverer** | AGENT.md (Claude agent) | LinkedIn верификация, bucket assignment | Да |
| **Enricher** | AGENT.md (Claude agent) | Apollo Enrichment (платно) | Да |
| **CRM Writer** | Python script | Валидация + запись в Google Sheets | Да |
| **Outreach Writer** | AGENT.md (Claude agent) | Персонализированные email-питчи | Да |
| **Gmail Drafter** | Python script | Создание черновиков в Gmail | Да |
| **sheets_helper.py** | Python utility | CLI для Google Sheets | Да |
| **pipeline_io.py** | Python utility | Межагентная передача данных через файлы | Да |
| **exclusion_gate.py** | Python utility | Unified exclusion/dedup check | Да |

### 1.2 Что блокирует автономную работу

#### Блокер 1: Checkpoints требуют человека

**Текущее поведение:**
- **CP1** (enrichment): Orchestrator показывает стоимость и ждёт "да/нет"
- **CP2** (pitches): Orchestrator показывает питчи и ждёт одобрения
- **CP2.5** (sample draft): Orchestrator показывает 1 черновик и ждёт "ок"

**Что нужно для автономии:**
- CP1 → Telegram bot: отправить запрос, ждать ответа (или timeout → skip enrichment)
- CP2 → Убрать. Питчи создаются автоматически, оператор ревьюит в Gmail drafts
- CP2.5 → Убрать. Черновики создаются автоматически

#### Блокер 2: Нет error recovery с сохранением состояния

**Текущее поведение:**
- Orchestrator делает max 2 retry для Searcher, 1 для Enricher
- При crash данные в `data/pipeline/` сохраняются, но нет механизма resume
- Нет уведомлений об ошибках

**Что нужно для автономии:**
- Retry с exponential backoff (30 мин окно)
- Telegram-уведомления при ошибках
- Resume с последнего успешного шага (pipeline_io.py уже хранит state)

#### Блокер 3: Нет headless entry point

**Текущее поведение:**
- Запуск через интерактивный Claude Code: `/autopipeline iGaming Brazil`
- Orchestrator пишет в чат, ждёт ответа в чате

**Что нужно для автономии:**
- Shell-скрипт обёртка для `claude -p`
- Режим "autonomous" в Orchestrator AGENT.md
- Конфиг вертикалей/GEO по расписанию

#### Блокер 4: Gmail auth требует браузер

**Текущее поведение:**
- `create_drafts.py` использует OAuth2 Desktop App flow
- Первичная авторизация требует браузер

**Что нужно для автономии:**
- Перенести `token.json` с Mac на VPS
- Token refresh автоматический (если scope не менялся)
- Мониторинг: если token expired → уведомление в TG

#### Блокер 5: Нет CLAUDE.md / .claude/ в репо

**Текущее поведение:**
- Claude Code на VPS не будет знать контекст проекта
- MCP серверы (Apollo) не сконфигурированы для этого репо

**Что нужно для автономии:**
- Создать `.claude/settings.json` с конфигурацией MCP
- Создать `CLAUDE.md` с базовыми инструкциями для headless-режима

### 1.3 Что уже готово к автономной работе

1. **Межагентная передача данных** — файлы в `data/pipeline/`, не контекст Claude. Это хорошо для headless.
2. **Python-скрипты** (crm_writer, assemble_*, exclusion_gate) — полностью автономны, вызываются через CLI.
3. **Агенты** (Pre-Enricher, Searcher, Discoverer, Enricher, Outreach Writer) — каждый работает независимо, читает вход с диска.
4. **Google Sheets** — service account auth, не требует браузер.
5. **Apollo API** — через MCP, stateless.
6. **Логирование** — `logs/` с сессиями, feedback, ретроспективами.

### 1.4 Зависимости для VPS

| Зависимость | Источник | Как перенести |
|---|---|---|
| Google Service Account JSON | `./credentials.json` | scp на VPS |
| Gmail OAuth token | `~/Documents/ai_data/gmail_credentials.json` + `token.json` | scp, auto-refresh |
| Apollo API key | `.env` | scp |
| Telegram Bot Token | ещё не создан | создать через @BotFather |
| Claude Code CLI | нет на VPS | `curl -fsSL https://claude.ai/install.sh \| bash` |
| Python 3 + gspread + google-auth | системные | `apt + pip` |
| Apollo MCP server | Claude Code MCP config | настроить `.claude/settings.json` |

### 1.5 Риски

| Риск | Вероятность | Влияние | Митигация |
|---|---|---|---|
| Claude Max rate limit при ежедневных прогонах | Средняя | Pipeline не запустится | Мониторинг в TG, запуск в off-peak |
| OAuth token expiry (Gmail) | Низкая | Черновики не создадутся | Auto-refresh + TG alert |
| Apollo API down | Низкая | Searcher/Enricher fail | Retry 30 мин + skip enrichment |
| Google Sheets quota | Низкая | CRM write fail | Retry с backoff |
| VPS downtime | Низкая | Прогон пропущен | Cron запустит на следующий день |

---

## 2. Вывод

Pipeline **архитектурно готов** к автономной работе — данные передаются через файлы, агенты независимы, Python-скрипты stateless.

**Главные изменения** для перехода к автономному режиму:

1. **Переработать Orchestrator** — добавить autonomous mode (auto-approve CP2/CP2.5, TG bot для CP1)
2. **Добавить Telegram bot** — для финансовых approvals и уведомлений
3. **Добавить retry + state recovery** — exponential backoff 30 мин
4. **Создать shell wrapper** — `run_pipeline.sh` для cron
5. **Создать CLAUDE.md + .claude/settings.json** — контекст для headless Claude Code
