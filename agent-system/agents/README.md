# AdsGram Multi-Agent System

## Архитектура

```
Пользователь (только чекпойнты)
    │
    ▼
Orchestrator ── управляет потоком данных через Agent tool
    │
    ├─→ Pre-Enricher    → JSON → Orchestrator (company-level web recon)
    ├─→ Searcher        → JSON → Orchestrator (armed with Pre-Enricher context)
    ├─→ Discoverer      → JSON → Orchestrator (contacts + verify + bucket sort)
    │   ══ CHECKPOINT 1: одобрение кредитов ══
    ├─→ Enricher         → JSON → Orchestrator
    ├─→ CRM Writer       ← объединённый пакет от Orchestrator
    ├─→ Outreach Writer  ← читает CRM напрямую
    │   ══ CHECKPOINT 2: одобрение питчей ══
    └─→ Summary
```

Пользователь не участвует в передаче данных между агентами.
Orchestrator парсит JSON каждого агента и передаёт нужную
часть следующему. Единственные паузы — чекпойнты.

## Что делает каждого участника агентом, а не скриптом

Каждый агент имеет три слоя поверх скилла:

1. **Стратегии оптимизации** — адаптивное поведение (fallback-и, приоритизация, бесплатные пути до платных)
2. **Рефлексия** — после выполнения агент оценивает результат и решает: достаточно, доработать, или спросить
3. **Память** — читает логи прошлых сессий и обратную связь от других агентов перед работой; пишет свой лог после

## Структура директории

```
agent-system/agents/
├── README.md
├── orchestrator/
│   └── AGENT.md
├── pre-enricher/
│   └── AGENT.md
├── discoverer/
│   └── AGENT.md
├── searcher/
│   └── AGENT.md
├── qualifier/
│   └── AGENT.md
├── enricher/
│   └── AGENT.md
├── crm-writer/
│   └── AGENT.md
└── outreach-writer/
    └── AGENT.md

agent-system/skills/
├── adsgram-prospector/
│   └── SKILL.md
├── adsgram-outreach/
│   └── SKILL.md
└── adsgram-autopipeline/
    └── SKILL.md

agent-system/contracts/
├── pre-enricher-output.json
├── searcher-output.json
├── discoverer-output.json
├── enricher-output.json
└── crm-writer-input.json

config/
└── agent-config.md

logs/
├── sessions/              ← лог каждого запуска агента
│   └── _template.json
├── feedback/              ← обратная связь между агентами
│   └── _template.json
└── retrospectives/        ← ретроспектива полного цикла (от оркестратора)
    └── _template.md
```

## Три типа артефактов

| Артефакт | Где живёт | Кто пишет | Кто читает |
|----------|-----------|-----------|------------|
| **AGENT.md** | agent-system/agents/{name}/ | Человек | Агент при запуске |
| **SKILL.md** | .agent-system/skills/agent-system/skills/ | Человек | Агент при запуске |
| **Контракт** | agent-system/contracts/ | Человек | Агенты (вход/выход) |
| **Лог сессии** | logs/sessions/ | Агент | Тот же агент в следующий раз |
| **Feedback** | logs/feedback/ | Агент | Другой агент |
| **Ретроспектива** | logs/retrospectives/ | Оркестратор | Оркестратор + человек |

## Связь агентов со скиллами

| Агент | Скилл-источник | Секции |
|-------|---------------|--------|
| Pre-Enricher | `agent-system/skills/adsgram-prospector/SKILL.md` | Stage 0 (Pre-Enrichment) |
|  | `agent-system/skills/adsgram-prospector/apollo-search-patterns.md` | Patterns 1-2 (what Searcher expects) |
| Searcher | `agent-system/skills/adsgram-prospector/SKILL.md` | Stage 1 (Intake), Stage 2 (Search) |
|  | `agent-system/skills/adsgram-prospector/apollo-search-patterns.md` | 5 failure patterns, fallback ladder, recipes |
| Discoverer | `agent-system/skills/adsgram-prospector/SKILL.md` | Discovery (contacts + verify + bucket sort) |
|  | `agent-system/skills/adsgram-prospector/apollo-search-patterns.md` | domains_audit for 0-result company discovery |
| ~~Qualifier~~ | ELIMINATED v1.5.0 — absorbed into Discoverer | — |
| Enricher | `agent-system/skills/adsgram-prospector/SKILL.md` | Stage 4 (Enrich), Credit Management |
| CRM Writer | `agent-system/skills/adsgram-prospector/SKILL.md` | Stage 5 (Report) |
| Outreach Writer | `agent-system/skills/adsgram-outreach/SKILL.md` | Целиком |
| Orchestrator | `agent-system/skills/adsgram-autopipeline/SKILL.md` | Архитектура, Checkpoints |

## Система памяти

Агенты накапливают опыт через три механизма:

**Логи сессий** — после каждого запуска агент записывает: что сработало,
что нет, какие паттерны обнаружены, рекомендации. Перед следующим запуском
читает последние 3 лога и адаптирует стратегию.

**Обратная связь** — если агент обнаруживает несоответствие в данных
предыдущего агента (Enricher видит что VERIFIED лид ушёл из компании),
он записывает feedback. Целевой агент читает его перед работой.

**Ретроспективы** — оркестратор после полного цикла собирает метрики
от всех агентов и генерирует ретроспективу: воронка, ресурсы,
что сработало, что нет, рекомендации. Если паттерн повторяется 3+ раз
в логах — переносится в Common Pitfalls в SKILL.md.

## Порядок вызова

```
0a. Pre-Enricher A →  agent-system/contracts/pre-enricher-output.json       (company-level web recon)
1.  Searcher       →  agent-system/contracts/searcher-output.json           (Apollo search with Pre-Enricher context)
0b. Discoverer      →  agent-system/contracts/discoverer-output.json          (contacts + verify + bucket sort)
3. Enricher      →  agent-system/contracts/enricher-output.json   (CHECKPOINT: одобрение кредитов)
4. CRM Writer    →  запись в Google Sheets (принимает данные от Discoverer и Enricher)
5. Outreach Writer → письма                          (CHECKPOINT: одобрение питчей)
```

**Особенность:** Outreach Writer не получает JSON-контракт. Он читает
лидов напрямую из CRM (Excel), фильтруя по Lead Status = "Verified" /
"Partially verified" и пустому Stage. Это значит, что CRM Writer
должен отработать до запуска Outreach Writer.
