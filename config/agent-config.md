# Общий конфиг мультиагентной системы

Этот файл читают ВСЕ агенты. Здесь — параметры, которые не привязаны к конкретному агенту.

---

## Пути к файлам

Все пути относительно корня проекта (`adsgram/`).

| Файл | Путь | Назначение |
|------|------|------------|
| CRM | `apollo/data/AdsGram_CRM.xlsx` | Основная база лидов (лист "Leads") |
| Company DB | `apollo/data/Top_iGaming_Operators.xlsx` | Exclusion list + лог поисков |
| Контракты | `contracts/` | JSON-схемы между агентами |
| Логи | `logs/` | Сессии, feedback, ретроспективы |

## Скиллы — пути

Все пути относительно корня проекта (`adsgram/`).

| Скилл | Путь |
|-------|------|
| Prospector | `skills/adsgram-prospector/SKILL.md` |
| Outreach | `skills/adsgram-outreach/SKILL.md` |
| Autopipeline | `skills/adsgram-autopipeline/SKILL.md` |
| Gmail Drafter | `skills/gmail-drafter/SKILL.md` |

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
- Excel-заголовки: **английский**
- Excel-заметки: **русский** где уместно
