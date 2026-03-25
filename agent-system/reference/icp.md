# Ideal Customer Profile (ICP)

## Target Verticals
- **Primary:** iGaming (online betting, casinos, sports betting), VPN services
- **Secondary:** crypto/web3

## Target Roles (in priority order)
1. Media Buyer / Traffic Manager
2. User Acquisition (UA) Manager
3. Performance Marketing Manager
4. Growth Manager / Growth Marketing Manager
5. Acquisition Marketing Manager
6. Digital Marketing Manager (with paid/performance focus)
7. Marketing Director (if no lower-level contacts available)
8. BD Manager / Sales Manager (fallback)

## Target Seniorities
- Manager, Senior, Director, VP

## Exclusion Criteria: B2B Technology & Data Providers

**Do NOT prospect at these types of companies — they are B2B service providers, not buyers of traffic:**

- **B2B Platform Providers**: Betting platform software, payment processors, game aggregators, sportsbook software, casino management systems, affiliate platforms
- **Data/Odds/Feed Providers**: Odds feeds, betting data providers, live statistics, sports data APIs, market data vendors
- **Software/Tech Vendors**: Payment gateways serving iGaming, KYC/AML compliance platforms, analytics vendors, fraud detection systems, CRM platforms, communications platforms targeting iGaming

**Why exclusion?** These companies SELL tools TO iGaming operators rather than BUY traffic. They have no budget for AdsGram media buying — their customers are operators (who do have budgets). Prospecting at B2B vendors wastes time and credits.

**Examples of excluded B2B vendors:**
- B2Tech (b2tech.com) — betting platform software
- DATA.BET (data.bet) — odds and data feeds
- Evoplay (evoplay.games) — casino game studio/provider
- Integration vendors, payment processors, compliance platforms, affiliate software

**Correct target:** The casino/betting operator using the software, not the software company itself. If a company's primary business is selling services to iGaming operators, exclude it.

## Target GEOs
- **LATAM:** Brazil, Mexico, Argentina, Colombia
- **Asia:** India, Singapore, Indonesia, Philippines, Vietnam
- **Europe:** Italy, Spain, CIS region
- **Africa:** Nigeria, Ghana, Egypt, Kenya, South Africa, Tanzania, Uganda

## Apollo Search Parameters

Derived from ICP above. Used by Searcher Agent.

### Recipe 1: Standard Search (first attempt)

```json
{
  "q_organization_domains_list": ["company.com"],
  "person_titles": ["media buyer", "traffic manager", "user acquisition",
    "performance marketing", "growth manager", "growth marketing",
    "acquisition marketing", "paid media", "digital marketing"],
  "person_seniorities": ["manager", "senior", "director", "vp"],
  "contact_email_status": ["verified", "likely to engage"],
  "per_page": 25
}
```

### Recipe 2: Broadened Search (fallback)

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

### Batch strategy

Group companies into batches of 3-4 domains per search call. Run batches in parallel (up to 4 simultaneous searches) for speed.

### Broadening rules

If Apollo returns few/no results, broaden the search: remove `contact_email_status` filter, add additional titles ("affiliate", "partnerships", "business development", "head of marketing", "CMO", "chief marketing"), remove `person_seniorities` filter. African and LATAM operators often have non-standard title naming.
