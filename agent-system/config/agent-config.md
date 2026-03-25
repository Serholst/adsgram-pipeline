# Общий конфиг мультиагентной системы

Этот файл читают ВСЕ агенты. Здесь — параметры, которые не привязаны к конкретному агенту.

---

## Пути к файлам

Все пути относительно корня проекта (`adsgram-pipeline/`).

| Файл | Путь | Назначение |
|------|------|------------|
| CRM | Google Sheet (ID в `.env`: `CRM_SHEET_ID`), лист "Leads" | Основная база лидов |
| Company DB | Google Sheet (ID в `.env`: `COMPANYDB_SHEET_ID`), лист "Top iGaming Operators" | Exclusion list + лог поисков |
| Sheets Helper | `tools/sheets_helper.py` | CLI для взаимодействия с Google Sheets |
| Контракты | `agent-system/contracts/` | JSON-схемы между агентами |
| Логи | `logs/` | Сессии, feedback, ретроспективы |

### Sheets Helper — команды

Все агенты используют `python3 tools/sheets_helper.py <command>` через Bash tool:

| Команда | Описание |
|---------|----------|
| `crm-read-all` | Все строки CRM → JSON |
| `crm-read-headers` | Заголовки CRM → JSON |
| `crm-append-rows <json-file>` | Добавить строки в CRM из JSON-файла |
| `crm-dedup-set` | Dedup sets: emails + name×company пары |
| `crm-validate-headers` | Проверка структуры CRM (16 колонок: Company, Vertical, Country, Name, Title, Email, Email Status, Socials, Alt Contacts, Sources & Signals, Lead Status, Stage, First Contact Date, Last Activity Date, Suggested CTA, Notes) |
| `crm-row-count` | Количество строк в CRM |
| `companydb-read-all` | Все строки Company DB → JSON |
| `companydb-domains` | ВСЕ домены компаний (без фильтрации) |
| `companydb-excluded-domains` | Домены для exclusion (Prospected непустой ИЛИ Search Results содержит "excluded") + доступные домены |
| `companydb-append-rows <json-file>` | Добавить компании в DB из JSON-файла |

## Скиллы — пути

Все пути относительно корня проекта (`adsgram-pipeline/`).

| Скилл | Путь |
|-------|------|
| Prospector | `agent-system/skills/prospector/SKILL.md` |
| Outreach | `agent-system/skills/outreach/SKILL.md` |
| Autopipeline | `agent-system/skills/autopipeline/SKILL.md` |
| Gmail Drafter | `agent-system/skills/gmail-drafter/SKILL.md` |

## ICP (Ideal Customer Profile)

### Вертикали
- **Primary:** iGaming (online betting, casinos, sports betting), VPN
- **Secondary:** crypto/web3

### Целевые роли (по приоритету)
1. Media Buyer / Traffic Manager
2. User Acquisition (UA) Manager
3. Performance Marketing Manager
4. Growth Manager / Growth Marketing Manager
5. Acquisition Marketing Manager
6. Digital Marketing Manager (с фокусом на paid/performance)
7. Marketing Director (если нет нижестоящих контактов)
8. BD Manager / Sales Manager (fallback)

### Целевые seniorities
- Manager, Senior, Director, VP

### Целевые GEO
- **LATAM:** Brazil, Mexico, Argentina, Colombia
- **Asia:** India, Singapore, Indonesia, Philippines, Vietnam
- **Europe:** Italy, Spain, CIS region
- **Africa:** Nigeria, Ghana, Egypt, Kenya, South Africa, Tanzania, Uganda

## Лимиты

| Параметр | Значение |
|----------|----------|
| Soft credit limit (за сессию) | 20 |
| Daily credit limit (Apollo API) | 500 |
| Rate limit (Apollo API) | 50 RPM |

## Язык

- Общение с пользователем: **русский**
- JSON-контракты между агентами: **английский**
- Google Sheets заголовки: **английский**
- Google Sheets заметки: **русский** где уместно
