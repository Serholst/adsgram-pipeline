---
name: apollo-search-patterns
version: 1.0.0
description: "Apollo API search failure patterns, fallback strategies, and search parameter recipes. Read by Searcher, Pre-Enricher, and Orchestrator agents. Created after adult/gambling session revealed 5 systematic failure modes."
---

# Apollo Search Patterns & Fallback Strategies

## Когда читать этот документ

- **Searcher**: перед каждым поиском — выбор стратегии + fallback при 0 результатах
- **Pre-Enricher**: паттерны 1-2 (что именно Searcher ожидает от pre-enrichment)
- **Orchestrator**: при retry решениях (какой паттерн сработал → какой retry имеет смысл)

## Золотое правило

**Никогда не используй `q_keywords` как основной search vector.**

`q_keywords` search ("Bella French ManyVids", "Bree Mills Gamma") возвращает 0 даже для известных CEO. Всегда используй:
1. `organization_ids` (если знаешь Apollo org_id)
2. `q_organization_domains_list` (если знаешь домен)

`q_keywords` — только как последний fallback для поиска конкретного человека по имени, когда org_id и домен не работают.

## 5 паттернов отказа

### Pattern 1: Wrong Org Mapping

**Обнаружение:** Apollo company search по домену возвращает организацию с неправильным названием (не совпадает с брендом).

**Пример:** `livejasmin.com` → Apollo org "SaG Stiftung" (shell entity). People search по этому org_id → 0 результатов. Но `byborgenterprises.com` → 352 сотрудника.

**Причина:** Apollo маппит домен на юрлицо-регистранта, а не на операционную компанию.

**Fallback:**
1. Pre-Enricher ищет parent company через веб
2. Searcher ищет людей по parent domain вместо brand domain
3. Если Pre-Enricher нашёл `alternative_domains` → искать по всем

**Детекция в Searcher:**
- Company search вернул org с названием, не похожим на бренд
- People search по org_id → 0, но компания реально существует (>50 сотрудников на LinkedIn)

### Pattern 2: Brand ≠ Employer

**Обнаружение:** People search по brand domain возвращает 0 или только junior/CS roles. Сотрудники числятся под parent corp.

**Пример:** `adulttime.com` → 0 decision makers. Но `entertainmentgamma.com` (parent: GAMMA ENTERTAINMENT LTD.) → 12 людей. Bree Mills (CCO) числится под Gamma, не под Adult Time.

**Причина:** LinkedIn employees указывают юрлицо-работодателя, а не бренд продукта.

**Fallback:**
1. Pre-Enricher обнаруживает parent corp (M&A, Crunchbase, пресс-релизы)
2. Searcher ищет по ОБОИМ: brand domain + parent domain
3. Объединяет результаты, помечает source

**Детекция в Searcher:**
- Brand domain: 0 или <3 результатов
- Pre-Enricher предоставил `search_vectors_for_apollo.search_by_parent: true`

### Pattern 3: Seniority Filter Kills Results

**Обнаружение:** Поиск с `person_seniorities: ["manager", "senior", "director", "vp"]` возвращает 0, но без фильтра есть люди.

**Пример:** Bella French (CEO ManyVids) не имеет seniority тега в Apollo. Поиск с seniority filter → 0. Без filter → 21 человек (но все creators, см. Pattern 4).

**Причина:** В adult, crypto, малом бизнесе founders/CEOs часто не имеют стандартных seniority tags.

**Fallback:**
1. Первый поиск: С seniority filter
2. Если <3 результатов → retry БЕЗ seniority filter
3. Фильтруй результаты по title вручную (ищи Director, VP, CEO, Head of, Manager в title)

**Детекция в Searcher:**
- Результатов с фильтром <3, компания не ghost entity

### Pattern 4: Platform Users ≠ Employees

**Обнаружение:** People search возвращает людей, но все titles — "Model", "Content Creator", "Entertainer", "Cam Model".

**Пример:** ManyVids → 21 человек, все cam models и content creators. Ни одного реального сотрудника (CEO, CTO, COO не в Apollo).

**Причина:** Платформы (ManyVids, OnlyFans, Chaturbate) индексируют пользователей как "сотрудников" в Apollo, потому что пользователи указывают платформу как workplace на LinkedIn.

**Fallback:**
1. Отфильтруй titles: исключи "Model", "Content Creator", "Entertainer", "Cam", "Performer", "Star", "Webcam", "Streamer"
2. Если после фильтрации 0 → компания непрозрачна, передай в Qualifier для web discovery (Stage 3c)
3. Pre-Enricher может найти реальных executives через BBB, пресс-релизы

**Title exclusion list:**
```
PLATFORM_USER_TITLES = [
    "model", "content creator", "entertainer", "cam",
    "performer", "star", "webcam", "streamer", "influencer",
    "creator", "artist", "photographer's assistant",
    "mv star", "fetish model", "actress", "actor"
]
```

Если title содержит любое из этих слов (case-insensitive) → флаг `PLATFORM_USER`, не считать как lead.

### Pattern 5: Ghost Entity

**Обнаружение:** Company search находит org record, но people search → 0 при любых фильтрах. Pre-Enricher тоже ничего не нашёл.

**Пример:** Adult Film Media (adultfilmmedia.com) — Apollo org exists, но 0 людей, 0 web presence, 0 BBB, 0 everywhere.

**Причина:** Домен зарегистрирован, LinkedIn page создана, но реальной компании нет (holding, placeholder, abandoned project).

**Детекция:**
- People search → 0 (с и без фильтров)
- Pre-Enricher: `enrichment_failed: true`
- Company headcount growth metrics: all null

**Действие:** Skip. Не тратить время. Пометить в логе как ghost entity для exclusion в будущих сессиях.

## Fallback Escalation Ladder

Для каждой компании Searcher следует этой лестнице:

```
Step 1: Search by brand domain + seniority + title filters
    │
    ├─ ≥3 results → DONE ✓
    │
    ▼ <3 results
Step 2: Search by brand domain WITHOUT seniority filter
    │
    ├─ ≥3 results → filter by title manually → DONE ✓
    ├─ Results are all platform users (Pattern 4) → filter → if 0 real → Step 4
    │
    ▼ <3 results
Step 3: Search by parent domain (if Pre-Enricher provided one)
    │
    ├─ ≥3 results → DONE ✓
    │
    ▼ <3 results
Step 4: Search by person names (if Pre-Enricher found decision makers)
    │   Use q_keywords with "FirstName LastName"
    │   + q_organization_domains_list with brand/parent domain
    │
    ├─ Found → DONE ✓
    │
    ▼ Not found
Step 5: Flag for web-only discovery
    │   Mark company as APOLLO_BLIND_SPOT in search_metadata
    │   Qualifier (Stage 3c) will handle via web search
    │
    └─ DONE (with recommendation)
```

## Apollo API Parameter Recipes

### Recipe 1: Standard Search (first attempt)

```json
{
  "q_organization_domains_list": ["company.com"],
  "person_titles": ["media buyer", "traffic manager", "user acquisition",
    "performance marketing", "growth manager", "growth marketing",
    "paid media", "digital marketing", "head of marketing", "CMO"],
  "person_seniorities": ["manager", "senior", "director", "vp"],
  "contact_email_status": ["verified", "likely to engage"],
  "per_page": 25
}
```

### Recipe 2: Broadened Search (Step 2)

```json
{
  "q_organization_domains_list": ["company.com"],
  "person_titles": ["media buyer", "traffic manager", "user acquisition",
    "performance marketing", "growth", "marketing", "affiliate",
    "partnerships", "business development", "head of marketing",
    "CMO", "chief marketing", "CEO", "founder", "managing director"],
  "per_page": 25
}
```
No `person_seniorities`, no `contact_email_status`.

### Recipe 3: Parent Company Search (Step 3)

```json
{
  "q_organization_domains_list": ["parent-company.com", "brand.com"],
  "person_titles": ["media buyer", "marketing", "growth", "acquisition",
    "partnerships", "business development", "CEO", "CMO", "COO"],
  "per_page": 50
}
```
Both domains, broadened titles, no seniority filter.

### Recipe 4: Person Name Search (Step 4)

```json
{
  "q_keywords": "FirstName LastName",
  "q_organization_domains_list": ["company.com", "parent.com"],
  "per_page": 5
}
```
Minimal filters. If this returns 0, the person is not in Apollo.

## Вертикально-специфичные особенности

### Adult Industry

- **Всегда** применяй Pattern 4 фильтр (platform users)
- **Всегда** ищи parent company (Pattern 2) — M&A в индустрии активная
- `q_keywords` поиск по имени → почти всегда 0 (сотрудники не аффилируются с adult на LinkedIn)
- Лучший source для decision makers: XBIZ, AVN, пресс-релизы (Pre-Enricher)

### Gambling / iGaming

- Pattern 2 частый (brand vs holding): 10bet → TechSolutions Group, Coolbet → SEGA SAMMY
- African operators: слабое Apollo покрытие, retail roles доминируют
- Лучший source: SBC/SiGMA/ICE speaker lists

### VPN / Crypto

- Pattern 5 частый (ghost entities, especially crypto)
- Founders часто единственный decision maker (Pattern 3)
- Лучший source: Crunchbase, Product Hunt, GitHub

## Метрики качества поиска

После завершения поиска по компании, оцени результат:

| Метрика | Хорошо | Приемлемо | Плохо |
|---------|--------|-----------|-------|
| Leads per company | ≥3 | 1-2 | 0 |
| Decision makers (Director+) | ≥1 | 0 but Manager+ | 0 |
| Leads with email | ≥50% | 25-50% | <25% |
| Platform users filtered | <20% of raw | 20-50% | >50% |
| Fallback steps used | 1-2 | 3 | 4-5 |

Если >30% компаний scored "Плохо" → запиши рекомендацию в search_metadata: вертикаль/регион с системно слабым покрытием.
