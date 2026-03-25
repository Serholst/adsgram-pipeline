---
name: adsgram-prospector
version: 1.3.0
description: "AdsGram lead prospecting pipeline via Apollo. Finds decision-makers (Media Buyers, UA Managers, Growth Managers, Performance Marketing Managers) at iGaming and VPN companies, enriches their contact data, verifies top leads, and delivers a prioritized Excel report. Use this skill whenever the user mentions: finding leads for AdsGram, prospecting iGaming/VPN contacts, building an outreach list, searching Apollo for decision-makers, or anything related to AdsGram's sales pipeline. Also trigger when the user says 'найди лидов', 'поиск контактов', 'обогатить лиды', or mentions target companies from the iGaming/VPN verticals"
---

# AdsGram Lead Prospector


You are building an outbound prospecting pipeline for **AdsGram.ai** — a Telegram-native ad network. The goal is to find decision-makers at iGaming, VPN and crypto/web3 companies who buy traffic and could become AdsGram advertisers.

## AdsGram Context

AdsGram is a Telegram-native advertising platform. The value proposition for advertisers: access to Telegram's 950M+ user base through native ad formats (rewarded ads in mini-apps, sponsored messages) with wallet-based targeting and 100,000+ resources (channels, bots, groups, TMA). The target customer is someone who buys digital traffic — media buyers, UA managers, growth leads — at companies in verticals where Telegram audiences convert well: iGaming, VPN, Forex, Crypto, Adult.

### Pitch Angle for Advertiser Leads

Every lead found through this pipeline is a potential advertiser — someone who buys traffic for their product. When presenting leads or writing outreach notes, keep this framing in mind:

- **Pain point**: they need audience, traffic, UA for their project and are likely using Meta, Google, KOL, organic
- **AdsGram value**: Telegram as a new paid channel on top of their current mix — wallet-based targeting, CPM from $10, fast launch
- **If the lead is clearly buying traffic** (Media Buyer, UA Manager)
- **If the lead is in growth/marketing but unclear if they buy traffic**:

## Ideal Customer Profile (ICP)

### Target Verticals
- **Primary:** iGaming (online betting, casinos, sports betting), VPN services
- **Secondary:** crypto/web3

### Target Roles (in priority order)
1. Media Buyer / Traffic Manager
2. User Acquisition (UA) Manager
3. Performance Marketing Manager
4. Growth Manager / Growth Marketing Manager
5. Acquisition Marketing Manager
6. Digital Marketing Manager (with paid/performance focus)
7. Marketing Director (if no lower-level contacts available)
8. BD Manager / Sales Manager (fallback)

### Target Seniorities
- Manager, Senior, Director

### Exclusion Criteria: B2B Technology & Data Providers

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

### Target GEOs
- **LATAM:** Brazil, Mexico, Argentina, Colombia
- **Asia:** India, Singapore, Indonesia, Philippines, Vietnam
- **Europe:** Italy, Spain, CIS region.
- **Africa:** Nigeria, Ghana, Egypt, Kenya, South Africa, Tanzania, Uganda

## Workflow

The pipeline has 5 stages. Each stage requires explicit user approval before spending credits.

**Stage overview (v1.6.0 — "Focused Agents"):**
0a. **Pre-Enrichment** — company-level web recon: parent companies, decision maker names, email patterns, verified domains. Agent: **Pre-Enricher** (FREE)
1. **Intake** — load files, build exclusion/dedup sets, confirm scope
2. **Search** — Apollo people search, armed with Pre-Enricher context. Agent: **Searcher** (FREE)
0b. **Discovery** — for each lead: find contacts + verify role + assign bucket — all in ONE web search per person. Also discover new leads for 0-result companies. Agent: **Discoverer** (FREE)
3. **Enrich** — Apollo enrichment, ONLY for Bucket B leads. Agent: **Enricher** (PAID, selective)
4. **Report** — write to CRM, update company database. Agent: **CRM Writer**

**Qualifier agent eliminated in v1.5.0, Pre-Enricher split in v1.6.0.** Company-level web recon (Pre-Enricher) and person-level discovery (Discoverer) are now separate focused agents. Each has one input, one output, one purpose.

Two key design principles:
1. **Pre-enrich before Apollo search (Stage 0A).** Apollo has systematic blind spots: misattributed org records, post-acquisition org changes, industries where employees hide employers on LinkedIn. Pre-Enricher discovers correct parent companies, verified domains, and decision maker names.
2. **One search per lead, three outputs (Stage 0B).** A single `"[Name]" "[Company]" LinkedIn` search produces: (a) LinkedIn URL = contact channel, (b) current employer = role verification, (c) enough data for bucket A/B/Skip assignment. Discoverer is the ONLY agent that does person-level free web research.

### Stage 0: Pre-Enrichment — Company-Level Web Recon (FREE)

**This stage runs BEFORE any Apollo search.** Its purpose is to gather intelligence about target companies through open web sources, so that Apollo searches in Stage 2 are more accurate and complete.

**Why this stage exists (v1.3.0):** In the adult/gambling session, Apollo returned 0 leads for 5 companies due to: misattributed org records (LiveJasmin mapped to wrong entity), post-acquisition org changes (Gamma Entertainment acquired by Byborg), and employees not listing adult employers on LinkedIn. Pre-enrichment discovers these issues upfront.

**The Pre-Enricher agent handles this stage.** See `agents/pre-enricher/AGENT.md` for the full 10-step pipeline. Key outputs that feed into Stage 2:

1. **Parent company discovery** — if a brand operates under a parent corp (LiveJasmin → Byborg Enterprises), Searcher will search BOTH brand domain and parent domain
2. **Decision maker names** — names found via press, conferences, BBB allow Searcher to do Apollo People Search by person name (bypasses broken org_id mappings)
3. **Verified domains** — the correct domain for Apollo `q_organization_domains_list`
4. **Email patterns** — discovered via ZoomInfo/RocketReach snippets, applied to all leads from that domain
5. **Company contacts** — general/press/partnership emails, phones, social links collected directly from web

**Sources (in priority order):**

1. Web search (general) — `"[company] team leadership founder CEO"`
2. Company website — /about, /contact, /team, /press, /affiliates
3. BBB + ZoomInfo + RocketReach snippets — officers, masked emails, phones
4. Social profiles — LinkedIn, X/Twitter, Instagram, Telegram
5. Press releases + PR agencies — spokesperson names, media contacts
6. Job postings — hiring manager names, recruiter emails, tech stack
7. Conference speaker lists — vertical-specific (SBC/ICE for iGaming, AVN/XBIZ for adult)
8. Industry media interviews — vertical-specific publications
9. Corporate registries — OpenCorporates, Companies House, local filings
10. Domain WHOIS — registrant organization, registrant email

**Output:** `contracts/pre-enricher-output.json` — passed to Orchestrator, who extracts `search_vectors_for_apollo` and feeds them to Searcher alongside the standard search request.

**When to skip Stage 0:** If the user provides well-known companies with strong Apollo coverage (e.g., bet365, DraftKings), Pre-Enrichment adds little value. The Orchestrator may skip this stage if all companies are already in Company DB with previous search results showing good Apollo coverage.

### Company Database (Google Sheet: "Top iGaming Operators")

**This file serves two purposes and MUST be read at the start of every prospecting session:**

1. **Exclusion list** — every domain in this file is excluded from search by default, regardless of whether column I ("Prospected") is filled or empty. The file contains ~175+ known iGaming/VPN companies. If the user explicitly names a specific domain that happens to be in the file, warn them ("Эта компания уже есть в базе Top_iGaming_Operators") and proceed only after their confirmation.
2. **Search results log** — after prospecting, ADD newly searched companies to this file and record results.

**File structure (columns):**
- A: # (row number)
- B: Company name
- C: Country
- D: Company Domain ← **use this to build exclusion set**
- E: Business Domain (description)
- F: Est. Revenue 2024 ($M)
- G: Public / Private
- H: Ticker
- I: Prospected ← **"Yes (YYYY-MM-DD)" if searched, empty if not**
- J: Search Results ← **summary: leads found, roles, quality, flags**

**How to load exclusion domains — run this FIRST, before any company selection:**

```bash
python3 tools/sheets_helper.py companydb-domains
```

Returns JSON: `{"domains": [...], "count": N}`. Store `domains` as `exclusion_domains` — you'll need it throughout the session.

**How to update after prospecting — MANDATORY for ALL searched companies, including those with 0 results:**

Save new companies to `/tmp/companies_batch.json` and append:

```bash
python3 tools/sheets_helper.py companydb-append-rows /tmp/companies_batch.json
```

- Add each newly searched company (even if zero leads were found)
- Set column I to "Yes (YYYY-MM-DD)"
- Set column J to a summary: "N leads found: [roles]. [quality notes]. [flags like CATCHALL, weak coverage, etc.]"
- If zero results: "0 relevant leads. [reason: weak Apollo coverage / only BD roles / etc.]"
- **This is a hard requirement.** Every company that was sent to Apollo people search MUST be recorded, regardless of outcome.

### Stage 1: Intake — Understand the Request

Parse what the user wants. They might provide:
- A list of specific company domains to search
- A vertical + GEO combination ("find leads in iGaming in Brazil")
- A vague request ("найди ещё лидов")

**Step 1a: Load the exclusion set.** If you haven't already loaded the Company DB in this session, do it now:

```bash
python3 tools/sheets_helper.py companydb-domains
```

Store `domains` as `exclusion_domains` — you'll need it throughout the session.

**Step 1b: Load the CRM — contact dedup set AND company exclusion set.** If you haven't already loaded the CRM in this session, do it now:

```bash
python3 tools/sheets_helper.py crm-dedup-set
```

Returns JSON with `emails`, `name_company` (format: `"name|||company"`), and `total_rows`. Extract `crm_companies` from `name_company` by splitting on `|||` and collecting unique company names.

**Keep these sets in memory for the entire session.** They serve THREE purposes:

1. **Company-level exclusion (Stage 1, Step 1d):** If a candidate company already exists in CRM, it is blocked from search. This is a SECOND exclusion filter alongside `exclusion_domains` from Company DB. Both sources serve as exclusion lists — if a company appears in EITHER, do not search it.
2. **Lead-level dedup (Stage 4):** Filter out individual leads whose email or name+company already exist in CRM. This prevents wasting credits on re-enrichment.
3. **Final dedup (Stage 5):** Before writing to CRM to prevent duplicate rows.

If a lead from Apollo search matches CRM by name+company, mark it as `ALREADY IN CRM` in the results table and exclude from enrichment. If the user explicitly asks to re-enrich a known contact, warn them and proceed only after confirmation.

**Step 1c: Build your candidate list.** Where the candidates come from depends on the request type:
- **User provides specific domains** → use those, but check each one against `exclusion_domains` (see Step 1d)
- **Vertical/GEO combination** → use Apollo Organization Search (FREE) to discover companies, then filter
- **Vague request ("найди ещё лидов")** → use Apollo Organization Search with relevant vertical keywords to discover NEW companies not in the exclusion set. Do not cherry-pick from the Top_iGaming file.

**Step 1d: Validation gate — run before ANY Apollo people search.** This is a hard requirement. After assembling your candidate list, check each one against **BOTH** exclusion sources:

1. Check domain against `exclusion_domains` (from `companydb-domains`)
2. Check company name against `crm_companies` (from `crm-dedup-set`)

For each candidate:
- If domain in `exclusion_domains` → BLOCKED by Company DB
- Else if company name in `crm_companies` → BLOCKED by CRM (already have leads)
- Else → APPROVED for search

Only APPROVED companies may be sent to Apollo. Inform the user which companies were filtered out and which source blocked them.

This dual gate exists because in previous sessions the exclusion check only covered the operators file, and companies that were already in CRM were accidentally re-searched.

Always confirm the final approved search scope with the user before proceeding to Stage 2.

**Step 1e: Load Apollo contacts set.** If you haven't already loaded Apollo contacts in this session, do it now. Use `apollo_contacts_search` to pull existing contacts and build a dedup set. Run a broad search (no keywords) to get all contacts, paginating if needed:

```python
apollo_contact_emails = set()
apollo_contact_names = set()
# After calling apollo_contacts_search (paginate through all pages):
for contact in all_apollo_contacts:
    if contact.get('email'):
        apollo_contact_emails.add(contact['email'].strip().lower())
    first = contact.get('first_name', '') or ''
    last = contact.get('last_name', '') or ''
    name = f"{first} {last}".strip()
    org = contact.get('organization_name', '') or ''
    if name and org:
        apollo_contact_names.add((name.strip().lower(), org.strip().lower()))

print(f"Apollo contacts loaded: {len(apollo_contact_emails)} emails, {len(apollo_contact_names)} name+company pairs")
```

**Keep `apollo_contact_emails` and `apollo_contact_names` in memory for the entire session.** These are checked before enrichment (Stage 4) alongside CRM dedup — if a lead is already an Apollo contact, mark it as `ALREADY IN APOLLO CONTACTS` and skip enrichment (re-querying already-revealed contacts by email is free if data recovery is needed later).

### Stage 2: Search — Find People (FREE)

Use `apollo_mixed_people_api_search` — this costs zero credits.

**Search parameters to use:**
- `q_organization_domains_list`: company domains from user
- `person_titles`: ["media buyer", "traffic manager", "user acquisition", "performance marketing", "growth manager", "growth marketing", "acquisition marketing", "paid media", "digital marketing"]
- `person_seniorities`: ["manager", "senior", "director", "vp"]
- `contact_email_status`: ["verified", "likely to engage"]
- `per_page`: 25

**Batch strategy:** Group companies into batches of 3-4 domains per search call. Run batches in parallel (up to 4 simultaneous searches) for speed.

**If Apollo returns few/no results**, broaden the search: remove `contact_email_status` filter, add additional titles ("affiliate", "partnerships", "business development", "head of marketing", "CMO", "chief marketing"), remove `person_seniorities` filter. African and LATAM operators often have non-standard title naming.

**Present results to user as a table:**
- Name (last name will be partially hidden — this is normal for Apollo search)
- Title
- Company
- Country
- Email available: Yes/No
- Seniority match: Yes/No

Flag any quality concerns:
- Retail/offline roles (e.g., "Retail Sales Manager" ≠ digital marketing)
- Interns or associates
- People in unrelated departments

### Stage 3: ELIMINATED (v1.5.0)

**The Qualifier agent and Stage 3 have been eliminated.** All three responsibilities (contact discovery, role verification, bucket sort) are now performed by Pre-Enricher Этап B in a single web search pass.

See `agents/pre-enricher/AGENT.md` → Этап B for:
- Role verification (via LinkedIn search — same search that finds the profile URL)
- Bucket assignment (A/B/Skip — based on contacts found + verification status)
- 0-result company lead discovery

The output of Pre-Enricher Этап B is `qualifier-output.json` (same schema, same contract — downstream agents are unaffected).

This step uses web search only — zero Apollo credits.

### Stage 4: Enrich — Get Contact Details (PAID, SELECTIVE)

**CRITICAL: This stage is now selective.** Only enrich leads that meet ALL of these criteria:
1. No verified work email found in Stage 3
2. Role is relevant (not Skip)
3. Person is verified or partially verified (not "left company" or "NOT VERIFIED")
4. Not already in CRM or Apollo contacts

**The user decides which leads to enrich** based on the Stage 3 table. Present the enrichment candidates with a clear recommendation:
- 🟢 **Recommend enrichment** — verified role, no email found, high ICP fit
- 🟡 **Optional** — partially verified, might yield email
- 🔴 **Skip enrichment** — already has contact channels (LinkedIn + Twitter sufficient), or not verified, or low ICP fit

**Step 4a: CRM + Apollo contacts dedup filter.** Before presenting the enrichment list to the user, filter out contacts already in CRM **and** already in Apollo contacts:

```python
leads_to_enrich = []
leads_skipped_crm = []
leads_skipped_apollo = []
for lead in enrichment_candidates:
    name_key = (lead['name'].strip().lower(), lead['company'].strip().lower())
    if name_key in crm_names:
        leads_skipped_crm.append(lead)
    elif name_key in apollo_contact_names:
        leads_skipped_apollo.append(lead)
    else:
        leads_to_enrich.append(lead)

if leads_skipped_crm:
    print(f"SKIPPED — already in CRM ({len(leads_skipped_crm)}):")
    for s in leads_skipped_crm:
        print(f"  ✗ {s['name']} @ {s['company']}")
if leads_skipped_apollo:
    print(f"SKIPPED — already in Apollo contacts ({len(leads_skipped_apollo)}):")
    for s in leads_skipped_apollo:
        print(f"  ✗ {s['name']} @ {s['company']}")
```

Inform the user which leads were filtered and why (separately for CRM and Apollo contacts). Only present the remaining leads for enrichment approval.

**Step 4b: Confirm enrichment cost.**

Format: "Обогащение N лидов будет стоить N кредитов Apollo. Текущий баланс: X кредитов. Подтверждаете?"

Only proceed after explicit user approval.

**Enrich all approved leads in one batch** — do not split into multiple confirmation rounds. The user has approved the list; execute it.

Use `apollo_people_match` with the person's Apollo ID (from search results) for reliable enrichment. For leads discovered via web search (no Apollo ID), use full identifying details: first_name + last_name + domain + organization_name.

This returns:
- Full name
- Verified email address
- Phone numbers
- LinkedIn URL
- Company details (revenue, employee count, industry)
- Employment history

**Technical note:** `apollo_people_bulk_match` with just first_name + domain is unreliable and returns nulls. Always use `apollo_people_match` with the person's Apollo ID or full identifying details.

After enrichment, immediately flag:
- **No email returned** (email: null) — 1 credit wasted, note this
- **Catchall domain** (email_domain_catchall: true) — email may not be individually verified. Known catchall domains: betwinneraffiliates.com, betwinner.com, accessbet.com, nairabet.com
- **Possible job change** — if employment_history shows a newer role at a different company, or headline contains "Ex-"
- **Unverified email** — if email_status is not "verified"

**Re-querying already-revealed contacts by email does not consume additional credits.** Use this to recover lost data if needed.

### Stage 5: Report — Deliver Results

**Primary output: append leads to the CRM file.**

The CRM lives in Google Sheets (access via `tools/sheets_helper.py`).

Read existing data and append new leads. The CRM has these columns:

Company | Vertical | Country | Name | Title | Email | Email Status | Web Search | Lead Status | Stage | First Contact Date | Last Activity Date | Suggested CTA | Notes

**Column definitions:**
- **Web Search**: All contact channels found during Stage 3 discovery. Format: `LinkedIn: [url] | Twitter: @handle | WhatsApp: +number | IG: @handle | Source: [Apollo/Web/Conference]`. This replaces the old "LinkedIn" column — LinkedIn URLs are now stored here alongside all other web-discovered contacts.
- **Email Status**: "verified", "verified (CATCHALL)", "personal", "unavailable"
- **Lead Status**: Set based on Stage 3 verification results (Verified/Partially verified/Not verified/Needs review/Skip)
- **Stage**: leave empty (will be filled during outreach)
- **First Contact Date**: leave empty
- **Last Activity Date**: leave empty
- **Suggested CTA**: leave empty

**ALL leads must be written to CRM, including SKIP leads.** This ensures the CRM is a complete record of every person evaluated, preventing re-enrichment in future sessions.

**SKIP leads (no email, irrelevant role, left company, etc.) are also written to CRM with:**
- **Lead Status**: "Skip"
- **Notes**: MUST include the skip reason. Examples:
  - "SKIP. No email returned from enrichment. No web contacts found."
  - "SKIP. Irrelevant role — Retail Sales Manager, not digital marketing."
  - "SKIP. Left company — LinkedIn shows new employer since 2025."
  - "SKIP. Role discrepancy — Apollo says Media Buyer, actually Administrative Analyst."
  - "SKIP. Duplicate — same person found under different Apollo record."
- **Email**: fill if available (even for skipped leads — useful for future dedup)
- **Web Search**: fill with any discovered channels (even for skipped leads)
- All other fields (Stage, dates, CTA): leave empty

**Stage column values:**
- `1st letter sent` — initial outreach sent
- `ghosting` — no response after follow-up
- `declined` — explicitly said no
- `interested` — positive response received
- `started working` — deal in progress
- `other` — specify in Notes

Priority sorting for new leads (within the batch being appended):
1. Director/VP roles first
2. Growth/UA/Media Buyer roles next
3. Generic Marketing/Sales roles last
4. Within each tier, larger companies first

If Google Sheets is not accessible, fall back to creating a standalone JSON report in the outputs directory and notify the user. Do NOT create a separate report alongside the CRM — the CRM is the single deliverable.

**After writing CRM, update Company DB** via `python3 tools/sheets_helper.py companydb-append-rows`:
- Add each newly searched company (if not already in the file) with search results summary
- Mark column I as "Yes (YYYY-MM-DD)" and column J with leads found, roles, and quality notes

**Additionally, print a summary in chat:**
- Companies searched vs. companies with results
- Leads added to CRM, leads with verified email
- Credits spent and remaining balance
- Countries/companies with zero results and why

## Credit Management Rules

This is extremely important — the user has explicitly asked for careful credit management.

1. **Always check balance** before any paid operation: `apollo_users_api_profile` with `include_credit_usage: true`
2. **Always state the cost** before enrichment: "Это будет стоить N кредитов"
3. **Wait for explicit approval** — never auto-enrich
4. **Report any wasted credits** — if enrichment returns no email, acknowledge it
5. **Summarize spend** at the end: "Потрачено X кредитов, осталось Y"
6. **Minimize waste** — Stage 3 web discovery should reduce the number of leads that need paid enrichment. If web search already found a verified email, skip Apollo enrichment for that lead.

## Language

The user communicates in Russian. Respond in Russian. Google Sheets uses English column headers but Russian notes where appropriate.

## Common Pitfalls

Based on experience with this pipeline:

- **Searching companies already in Company DB** — this happened when the exclusion set was loaded but company selection was done visually instead of programmatically. The fix: always run the validation gate in Step 1d. If you find yourself selecting companies by scrolling through a list and picking names, stop — you're about to repeat this mistake. Let the code do the filtering.
- **Searching companies already in CRM** — this happened when only Company DB was used as exclusion source, but CRM was only checked at the individual lead level before enrichment. Companies that already had leads in CRM were re-searched via Apollo people search, wasting time. The fix: Step 1b now also builds `crm_companies` set, and Step 1d validation gate checks candidates against BOTH `exclusion_domains` (operators file) AND `crm_companies` (CRM). Both files are exclusion sources at the company level.
- **Enriching contacts already in CRM** — wasted credits. The fix: always load CRM dedup set in Step 1b and check every lead against `crm_emails` and `crm_names` before enrichment.
- **Crypto casinos** (Stake, BC.Game, 1xBet) have almost zero Apollo coverage — they're deliberately private. Warn the user upfront.
- **VPN search with "cybersecurity" keyword** returns too many irrelevant results. Use only "VPN" as keyword tag. Focus on companies which provide VPN as a Service.
- **African operators** — many results are retail Sales Managers, not digital marketing roles. Filter carefully. Apollo coverage in Africa is extremely weak: in the Nigeria session, only 6 of 23 companies had any Apollo people results, and phone numbers returned 0 out of 17 enrichments. Always supplement with web search (Stage 3).
- **Apollo search shows `has_email: true`** but enrichment may return null — search metadata can be stale.
- **"Ex-" in headline** — the person may have left the company. Flag these. In the Nigeria session, George Mbam was listed under betBonanza but had actually moved to GinjaBet — caught during Stage 3 verification.
- **Catchall domains** — common at large enterprises (BetWinner, AccessBET, NairaBET). The email format is usually correct but can't be individually verified. Flag in Notes and Email Status.
- **bulk_match unreliable** — `apollo_people_bulk_match` with partial data (first_name + domain only) often returns null. Always use `apollo_people_match` with Apollo person ID for reliable enrichment.
- **Title inflation in Apollo** — Apollo titles may not match reality (e.g., "Executive Officer" vs actual "Executive Assistant"). Always verify via web search.
- **Re-query by email is free** — if you need to recover data for already-enriched contacts, query by email. No additional credits consumed.
- **Enriching contacts already in Apollo** — before this check was added, leads that had been enriched in previous sessions (but excluded from CRM as Skip) were re-enriched, wasting credits. The fix: always load Apollo contacts in Step 1e and check every lead against `apollo_contact_emails` and `apollo_contact_names` before enrichment.
- **Not recording SKIP leads in CRM** — leads marked Skip (no email, irrelevant role, left company) were not written to CRM, causing them to be re-found and re-enriched in future sessions. The fix: ALL leads including Skips are now written to CRM with a reason in Notes. This makes the CRM the single source of truth for dedup.
- **Creating duplicate output files** — do NOT create a separate "session report" xlsx alongside the CRM. The CRM is the single deliverable. Summary stats and session metadata go in chat, not in extra files.
- **Enriching leads that already have web-discovered contacts** — in v1.1.0, enrichment happened before web search, so all leads were enriched blindly. In v1.2.0, web search (Stage 3) happens first. If a lead already has a verified email from web discovery, skip Apollo enrichment. This saved ~5-7 credits in the Nigeria session.
- **Too-narrow Apollo search filters** — initial searches with strict title + seniority + email_status filters may return very few results (especially in Africa/LATAM). If a batch returns <3 results, re-run with broader filters: remove email_status, expand titles (add "affiliate", "partnerships", "business development", "head of marketing", "CMO"), remove seniority filter.
