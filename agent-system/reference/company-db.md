# Company Database & Exclusion/Dedup Gates

## Company Database (Google Sheet: "Top iGaming Operators")

This file serves two purposes and MUST be read at the start of every prospecting session:

1. **Exclusion list** — companies are excluded from search if their "Prospected" column is non-empty (any value: "Processed", "Trash", "Yes ...", etc.) OR if their "Search Results" column contains the word "excluded". Companies with empty Prospected AND no "excluded" in Search Results remain available for search.
2. **Search results log** — after prospecting, ADD newly searched companies to this file and record results.

### File structure (columns)

- A: # (row number)
- B: Company name
- C: Country
- D: Company Domain ← **use this to build exclusion set**
- E: Business Domain (description)
- F: Est. Revenue 2024 ($M)
- G: Public / Private
- H: Ticker
- I: Prospected ← **non-empty = excluded from search** ("Processed", "Trash", "Yes YYYY-MM-DD", etc.)
- J: Search Results ← **if contains "excluded" → company excluded from search**
- K: Company Contacts ← JSON с контактами компании (phone, emails, socials, address, employees, linkedin). Пустые поля не включаются.

### How to load exclusion domains

Run this FIRST, before any company selection:

```bash
python3 tools/sheets_helper.py companydb-excluded-domains
```

Returns JSON:

```json
{
  "excluded_domains": [...],
  "excluded_count": N,
  "available_domains": [...],
  "available_count": N
}
```

Store `excluded_domains` as `exclusion_domains` — you'll need it throughout the session.

### How to update: TWO writes per session

Company DB is updated TWICE during a pipeline session:

#### Write 1: BEFORE Apollo People Search (Step 1d-post)

Immediately after the validation gate approves companies and BEFORE any Apollo People Search, write all approved companies to Company DB:

```bash
python3 tools/sheets_helper.py companydb-append-rows /tmp/companies_pre.json
```

- Set column I to "Yes (YYYY-MM-DD)"
- Set column J to "Searching..." (placeholder)
- **Why before search?** If the pipeline crashes mid-search, these companies are already marked as prospected. This prevents re-searching them in the next session.

#### Write 2: AFTER enrichment (final update)

After all enrichment is complete, update the same rows with search results:

```bash
python3 tools/sheets_helper.py companydb-update-cells /tmp/companies_post.json
```

- Update column J with: "N leads found: [roles]. [quality notes]. [flags like CATCHALL, weak coverage, etc.]"
- If zero results: "0 relevant leads. [reason: weak Apollo coverage / only BD roles / etc.]"
- Update column K ("Company Contacts") with JSON containing all company-level contacts (see section below)
- **This is a hard requirement.** Every company that was sent to Apollo people search MUST have its Search Results updated.

JSON file format for `companydb-update-cells`:

```json
[
  {
    "company": "Superbet",
    "updates": {
      "Search Results": "3 leads found: Growth Manager, UA Manager, Media Buyer. 2 verified.",
      "Company Contacts": "{\"phone\":\"+40213100100\",\"general_email\":\"info@superbet.com\",\"address\":\"Bucharest, Romania\",\"employees\":3500,\"linkedin\":\"https://linkedin.com/company/superbet\"}"
    }
  }
]
```

### Company-level contacts from Apollo enrichment

Apollo `people_match` responses include `organization` data. For each UNIQUE company encountered during enrichment, extract and store in column K ("Company Contacts") as a JSON string.

Fields to extract from Apollo `organization` object:

- `organization.phone` → `"phone"` in JSON
- `organization.raw_address` → `"address"` in JSON
- `organization.organization_revenue_printed` → `"revenue"` in JSON (also update column F if empty)
- `organization.linkedin_url` → `"linkedin"` in JSON
- `organization.estimated_num_employees` → `"employees"` in JSON

Additionally, merge Pre-Enricher `company_contacts` into the same JSON:

- `company_contacts.general_email` → `"general_email"`
- `company_contacts.press_email` → `"press_email"`
- `company_contacts.partnerships_email` → `"partnerships_email"`
- `company_contacts.phone` → `"phone"` (Pre-Enricher value; Apollo overwrites if available)
- `company_contacts.social_links.*` → `"twitter"`, `"instagram"`, `"telegram"`, `"tiktok"`, etc.

Omit null/empty fields from JSON for compactness. Example:

```json
{"phone": "+40213100100", "general_email": "info@superbet.com", "partnerships_email": "partners@superbet.com", "address": "Bucharest, Romania", "employees": 3500, "linkedin": "https://linkedin.com/company/superbet", "twitter": "@superbet", "instagram": "@superbet"}
```

**Do NOT discard organization data.** It is the only source of company-level contacts for companies where all individual emails are unavailable (e.g., OnlyFans, XVideos, BangBros in the Adult session).

---

## Exclusion & Dedup Gates

These gates run at the START of every prospecting session, BEFORE any Apollo search.

### Step 1a: Load Company DB exclusion set

```bash
python3 tools/sheets_helper.py companydb-excluded-domains
```

Store `excluded_domains` as `exclusion_domains`.

### Step 1b: Load CRM dedup set

```bash
python3 tools/sheets_helper.py crm-dedup-set
```

Returns JSON with `emails`, `name_company` (format: `"name|||company"`), and `total_rows`. Extract `crm_companies` from `name_company` by splitting on `|||` and collecting unique company names.

**Keep these sets in memory for the entire session.** They serve THREE purposes:

1. **Company-level exclusion (Step 1d):** If a candidate company already exists in CRM, it is blocked from search. This is a SECOND exclusion filter alongside `exclusion_domains` from Company DB. Both sources serve as exclusion lists — if a company appears in EITHER, do not search it.
2. **Lead-level dedup (before enrichment):** Filter out individual leads whose email or name+company already exist in CRM. This prevents wasting credits on re-enrichment.
3. **Final dedup (before CRM write):** Before writing to CRM to prevent duplicate rows.

### Step 1c: Build candidate list

Where the candidates come from depends on the request type:
- **User provides specific domains** → use those, but check each one against `exclusion_domains` (see Step 1d)
- **Vertical/GEO combination** → use Apollo Organization Search (FREE) to discover companies, then filter
- **Vague request ("найди ещё лидов")** → use Apollo Organization Search with relevant vertical keywords to discover NEW companies not in the exclusion set.

### Step 1d: Validation gate

**Run before ANY Apollo people search.** This is a hard requirement.

After assembling your candidate list, check each one against BOTH exclusion sources:

1. Check domain against `exclusion_domains` (from `companydb-excluded-domains`)
2. Check company name against `crm_companies` (from `crm-dedup-set`)

For each candidate:
- If domain in `exclusion_domains` → BLOCKED by Company DB
- Else if company name in `crm_companies` → BLOCKED by CRM (already have leads)
- Else → APPROVED for search

Only APPROVED companies may be sent to Apollo. Inform the user which companies were filtered out and which source blocked them.

This dual gate exists because in previous sessions the exclusion check only covered the operators file, and companies that were already in CRM were accidentally re-searched.

Always confirm the final approved search scope with the user before proceeding.

### Step 1e: Load Apollo contacts set

Use `apollo_contacts_search` to pull existing contacts and build a dedup set. Run a broad search (no keywords) to get all contacts, paginating if needed:

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

**Keep `apollo_contact_emails` and `apollo_contact_names` in memory for the entire session.** If a lead is already an Apollo contact, mark it as `ALREADY IN APOLLO CONTACTS` and skip enrichment (re-querying already-revealed contacts by email is free if data recovery is needed later).
