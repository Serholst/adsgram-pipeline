# AdsGram Multi-Agent System

## Архитектура

```
Пользователь (только чекпойнты)
    │
    ▼
Orchestrator ── управляет потоком данных через Agent tool
    │
    ├─→ Searcher        → JSON → Orchestrator
    ├─→ Qualifier        → JSON → Orchestrator
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
agents/
├── README.md
├── orchestrator/
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

skills/
├── adsgram-prospector/
│   └── SKILL.md
├── adsgram-outreach/
│   └── SKILL.md
└── adsgram-autopipeline/
    └── SKILL.md

contracts/
├── searcher-output.json
├── qualifier-output.json
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
| **AGENT.md** | agents/{name}/ | Человек | Агент при запуске |
| **SKILL.md** | .skills/skills/ | Человек | Агент при запуске |
| **Контракт** | contracts/ | Человек | Агенты (вход/выход) |
| **Лог сессии** | logs/sessions/ | Агент | Тот же агент в следующий раз |
| **Feedback** | logs/feedback/ | Агент | Другой агент |
| **Ретроспектива** | logs/retrospectives/ | Оркестратор | Оркестратор + человек |

## Связь агентов со скиллами

| Агент | Скилл-источник | Секции |
|-------|---------------|--------|
| Searcher | `skills/adsgram-prospector/SKILL.md` | Stage 1 (Intake), Stage 2 (Search) |
| Qualifier | `skills/adsgram-prospector/SKILL.md` | Stage 3 (Discover & Verify) |
| Enricher | `skills/adsgram-prospector/SKILL.md` | Stage 4 (Enrich), Credit Management |
| CRM Writer | `skills/adsgram-prospector/SKILL.md` | Stage 5 (Report) |
| Outreach Writer | `skills/adsgram-outreach/SKILL.md` | Целиком |
| Orchestrator | `skills/adsgram-autopipeline/SKILL.md` | Архитектура, Checkpoints |

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
1. Searcher      →  contracts/searcher-output.json
2. Qualifier     →  contracts/qualifier-output.json
3. Enricher      →  contracts/enricher-output.json   (CHECKPOINT: одобрение кредитов)
4. CRM Writer    →  запись в Excel (принимает данные от Qualifier и Enricher)
5. Outreach Writer → письма                          (CHECKPOINT: одобрение питчей)
```

**Особенность:** Outreach Writer не получает JSON-контракт. Он читает
лидов напрямую из CRM (Excel), фильтруя по Lead Status = "Verified" /
"Partially verified" и пустому Stage. Это значит, что CRM Writer
должен отработать до запуска Outreach Writer.
