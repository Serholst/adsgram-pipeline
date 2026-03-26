# AdsGram Email Templates

## Product Context

**AdsGram.ai** sells ad slots in Telegram — text, video, and native banners placed inside channels, bots, and mini-apps across 60+ countries. 11M+ views/month with built-in anti-fraud filtering.

**Sender:** Sergo Holst, BD at AdsGram.ai

Every lead is an **Advertiser** — someone who buys traffic for their product. We position AdsGram as a new paid channel worth testing on top of their existing mix (Meta, Google, TikTok, affiliates, organic).

**Key selling points (in order of importance for iGaming/VPN leads):**
1. **Price** — CPM from $0.90 depending on geo, significantly cheaper than Meta/Google
2. **Native ad formats** — text, video, native banners inside Telegram resources (not interstitials or popups)
3. **New channel to test** — Telegram has 950M+ users, especially strong in Africa, Asia, CIS. Most advertisers haven't tried buying traffic there
4. **Anti-fraud** — built-in filtering against bot traffic and spam
5. **Test period** — we offer a test period so advertisers can check audience quality before committing

---

## Pattern Decision Matrix

Matrix for selecting the right outreach email pattern based on two binary inputs:
company signal and role pain awareness.

### Company Signal (binary: YES / NO)

Signal = YES only if ALL conditions met:
1. Signal is one of:
   - Expanding to a new geo
   - Launched a new product or brand
   - Looking for traffic (intent made)
2. Signal is ≤ 6 months old

Everything else (sponsorships, awards, conferences, PR news, general hiring, etc...) = NO.

### Role Pain (binary: YES / NO)

Pain = YES if at least one:
- LinkedIn headline contains specific focus (e.g., "Driving Profitable UA", "Scaling Growth in LatAm", "Managing $2M ad spend")
- Job description of current position is filled with concrete details (channels, KPIs, markets, metrics)

Pain = NO if:
- Headline is empty, generic, or just restates the title ("Media Buyer at Company X")
- No job description available

### Decision Matrix

```
                    | Signal = YES             | Signal = NO
                    | (≤6 months, one of three)|
--------------------|--------------------------|----------------------
                    |                          |
Role Pain = YES     |  A: Personalized Pitch   |  B: Product Card
(headline/JD        |     CTA = role pain +    |     + Role Pain
 with specifics)    |     company signal       |     tagline
                    |                          |
--------------------|--------------------------|----------------------
                    |                          |
Role Pain = NO      |  C: Personalized Pitch   |  D: Product Card
(generic title,     |     CTA = company        |     (generic)
 no headline)       |     signal only          |
                    |                          |
--------------------|--------------------------|----------------------
```

### Expected Conversion Priority

- A — hit both company moment and personal focus
- C — hit company moment, role is generic
- B — hit personal focus, but no timing trigger
- D — cold spray, lowest conversion, zero research cost

---

## Subject Line Rules

### Geo logic (applies to all cells)

Geo in subject = specific country ONLY if ALL three conditions met:
1. Country is determined (not unknown)
2. Country is NOT an offshore jurisdiction (Cyprus, Malta, Gibraltar, Curacao, Isle of Man)
3. Country is in AdsGram coverage (has data in benchmarks table)

If any condition fails → use vertical instead of geo.

### Cell A — Subject

Company signal + mirror keyword from lead's LinkedIn headline:

```
[company] [signal в 2-3 словах] — [keyword from headline] with Telegram ✅
```

Example (geo expansion): `Exness enters LATAM — Profitable UA with Telegram ✅`
Example (new product): `Stake launches Stake.us — Scaling Growth with Telegram ✅`
Example (traffic intent): `Betano needs traffic — Performance Marketing with Telegram ✅`

Company signal is IN the subject (not in P.S.).

### Cell B — Subject

Mirror pattern — we know the role pain, use it:

```
[keyword from headline] with Telegram — [geo | vertical] ✅
```

### Cell C — Subject

Metric-driven — check company intent for metrics (CPA, CPM, CTR),
always substitute with our values:

**Step 1:** Scan company intent for metric keywords (CPA, CPM, CTR).

**Step 2:** Build subject with found metrics + our values:
- Found CPA: `Telegram ads (paid & native) — [geo | vertical] CPA ✅`
- Found CPM: `Telegram ads (paid & native) — [geo | vertical] CPM $0.90 ✅`
- Found CTR: `Telegram ads (paid & native) — [geo | vertical] CTR 1.7% ✅`
- Found 2: `Telegram ads (paid & native) — [geo | vertical] CPM $0.90 | CTR 1.7% ✅`
- Found 0 (fallback): `Telegram ads (paid & native) — [geo | vertical] users from $0.90 CPM ✅`

Max 2 metrics in subject. ✅ always present.

Company signal goes into P.S.

### Cell D — Subject

Current Product Card subject with ✅:

```
Telegram ads (paid & native) — [vertical], [geo] ✅
```

---

## Cell Definitions

### Cell A — Maximum data (confirmed)

Product Card format with two additions:
1. Role Pain tagline (from headline) — first line in body (visible in preview)
2. Company signal — already in subject, NOT duplicated in P.S.
3. P.S. — geo stats as example from the region (if worldwide but region known)

**Tagline priority when headline contains multiple signals:**
```
Profitable/ROI/CPA > UA/Acquisition > Performance > Scale/Growth > Affiliate > Budget > Geo
```
Pick the signal closest to money. Use geo data to concretize numbers.

```
Subject: [company] [signal] — [keyword from headline] with Telegram ✅

[Role Pain tagline — see tagline table]

Formats: [per vertical]
Placements: TG channels, bots, mini-apps, groups and closed communities
11M+ views/month, CTR 1.7% – @moslender, built-in anti-fraud
[Work with line if applicable]

Sergo,
Telegram: https://t.me/moslender
WhatsApp: +55 81 985688828

adsgram.ai - Tier 1 ads network in telegram.

P.S. As example: [N] views/month in [country], CPM $[X]
```

P.S. rules:
- Company signal is in subject — never duplicate in P.S.
- P.S. = geo-specific data as example from the lead's region
- If single market → direct geo stats (no "as example")
- If worldwide but region known → `As example: [stats from one country in that region]`
- If no geo data → omit P.S.

#### Cell A Example — iGaming, Exness, Brazil, headline "Driving Profitable UA across LatAm"

```
Subject: Exness enters LATAM — Profitable UA with Telegram ✅

CPM from $0.90, CTR 1.7%, built-in anti-fraud

Formats: text, video, native banners
Placements: TG channels, bots, mini-apps, groups and closed communities
11M+ views/month, CTR 1.7% – @moslender, built-in anti-fraud
Work with: 1xBet

Sergo,
Telegram: https://t.me/moslender
WhatsApp: +55 81 985688828

adsgram.ai - Tier 1 ads network in telegram.

P.S. As example: 80K views/month in Brazil, CPM $2.50
```

### Cell B — Role-aware, no trigger (confirmed)

Product Card with Role Pain tagline as first line (visible in email preview).
No company signal → P.S. is geo-specific only (if single market).

```
Subject: [keyword from headline] with Telegram — [geo | vertical] ✅

[Role Pain tagline — see table below]

Formats: [per vertical]
Placements: TG channels, bots, mini-apps, groups and closed communities
11M+ views/month, CTR 1.7% – @moslender, built-in anti-fraud
[Work with line if applicable]

Sergo,
Telegram: https://t.me/moslender
WhatsApp: +55 81 985688828

adsgram.ai - Tier 1 ads network in telegram.

P.S. [geo stats if single market]
```

#### Role Pain Tagline Table

Tagline is dry, factual, synergizes with the lead's headline. No selling language.

| Headline signal | Pain (боль) | Pain relief (tagline) |
|---|---|---|
| UA / Acquisition | Выгорание каналов, нет нового инвентаря | `Telegram UA inventory — 11M+ views/month, 60+ geos` |
| Scale / Growth | Упёрся в потолок текущих каналов | `950M+ Telegram users — most advertisers aren't buying here yet` |
| Profitable / ROI / ROAS | Дорогой трафик, фрод | `CPM from $0.90, CTR 1.7%, built-in anti-fraud` |
| CPA / CPI / Unit economics | Непредсказуемая экономика канала | `CPM from $0.90, CTR 1.7%, CPA — negotiable` |
| Specific geo (e.g. LatAm) | Нет охвата в нужном регионе | `[N] views/month in [country], CPM $[X]` |
| Affiliate / Traffic | Нужен объём, новые источники | `11M+ views/month — new traffic source, test period available` |
| Performance / Paid | Нужны измеримые каналы | `Paid placements in Telegram — CPM from $0.90, CPA available` |
| Budget / Spend | Диверсификация, зависимость от Meta/Google | `New ad inventory outside Meta/Google — 11M+ views/month` |

**Fallback** (headline present but no pattern match):
`Telegram ad placements — 11M+ views/month, 60+ geos`

### Cell C — Company trigger, generic role (confirmed)

Product Card with Signal Relief as first line (visible in email preview).
No headline → no role pain tagline. Company signal drives the first line instead.
No P.S. — signal relief already contains geo data.

#### Company Signal Relief Table

Signal relief is dry, factual — shows our solution for their situation. No selling language.

| Company signal | Что это значит | Signal relief (первая строка) |
|---|---|---|
| Expanding to a new geo | Нужен трафик в новом регионе | `Ad inventory in [region] — [N] views/month, CPM $[X]` |
| Launched a new product/brand | Нужно продвижение нового продукта | `950M+ Telegram users — new audience for [product/brand]` |
| Looking for traffic (intent) | Активно ищут каналы | `11M+ views/month, CPM from $0.90 — new traffic source` |

```
Subject: Telegram ads (paid & native) — [geo | vertical] [metric + our value] ✅

[Signal relief — see table above]

Formats: [per vertical]
Placements: TG channels, bots, mini-apps, groups and closed communities
11M+ views/month, CTR 1.7% – @moslender, built-in anti-fraud
[Work with line if applicable]

Sergo,
Telegram: https://t.me/moslender
WhatsApp: +55 81 985688828

adsgram.ai - Tier 1 ads network in telegram.
```

#### Cell C Example — iGaming, Exness expanding to LatAm, headline "Media Buyer at Exness"

```
Subject: Telegram ads (paid & native) — Brazil CPM $0.90 ✅

Ad inventory in LatAm — 80K views/month in Brazil, CPM $2.50

Formats: text, video, native banners
Placements: TG channels, bots, mini-apps, groups and closed communities
11M+ views/month, CTR 1.7% – @moslender, built-in anti-fraud
Work with: 1xBet

Sergo,
Telegram: https://t.me/moslender
WhatsApp: +55 81 985688828

adsgram.ai - Tier 1 ads network in telegram.
```

### Cell D — Minimum data (confirmed)

Current generic Product Card as-is. No tagline, no signal relief. See Base: Product Card (v3) section and Examples 1-3.

---

## Base: Product Card (v3)

This is an **anti-cold-email**. No greeting, no "I'm Sergo", no storytelling. Just a product spec sheet with contacts. The subject line acts as a filter — the recipient decides in 2 seconds if this is relevant.

**⚠️ CRITICAL: The `@moslender` in the CTR line is INTENTIONAL.**
The CTR line reads `CTR 1.7% – @moslender` — the Telegram handle is embedded after the dash, creating a clickable contact point. **Never remove the handle. Never replace it with a number.**

### Formats — variable by vertical

| Vertical | Formats line |
|---|---|
| iGaming | `Formats: text, video, native banners` |
| Adult | `Formats: video, native banners, adult ai-engagement` |
| VPN | `Formats: text, video, native banners` |
| Other | `Formats: text, video, native banners` |

### Work with — variable by vertical

| Vertical | Work with line |
|---|---|
| iGaming | `Work with: 1xBet, [add more when available]` |
| Adult | *omit this line entirely until client names are available* |
| VPN | *omit this line entirely until client names are available* |

### P.S. — geo-specific data (CONDITIONAL)

**P.S. is shown ONLY when the lead's market = a specific single country.** If the lead is worldwide (2+ markets, offshore HQ) → **NO P.S.**

```
P.S. [views/month] views/month in [country], CPM $[X]
```

**Variables:**
- **views/month** — calculated from benchmarks table: `225.8M / 20 × traffic_share_%`
- **CPM** — from benchmarks table by country
- **Country** — the lead's primary market. Determined by: (1) company's main market from LinkedIn/Apollo profile, (2) if HQ = Cyprus, Malta, Gibraltar, offshore → worldwide → no P.S.

**If country is not in the table** → use regional average, write "across [region]".

### Product Card Examples

#### Example 1 — iGaming, single market (Nigeria) — Cell D

```
Subject: Telegram ads (paid & native) — iGaming, Nigeria ✅

Formats: text, video, native banners
Placements: TG channels, bots, mini-apps, groups and closed communities
11M+ views/month, CTR 1.7% – @moslender, built-in anti-fraud
Work with: 1xBet

Sergo,
Telegram: https://t.me/moslender
WhatsApp: +55 81 985688828

adsgram.ai - Tier 1 ads network in telegram.

P.S. 1.5M views/month in Nigeria, CPM $1.20
```

#### Example 2 — iGaming, worldwide (Cyprus HQ) — Cell D

```
Subject: Telegram ads (paid & native) — iGaming, 60+ countries ✅

Formats: text, video, native banners
Placements: TG channels, bots, mini-apps, groups and closed communities
11M+ views/month, CTR 1.7% – @moslender, built-in anti-fraud
Work with: 1xBet

Sergo,
Telegram: https://t.me/moslender
WhatsApp: +55 81 985688828

adsgram.ai - Tier 1 ads network in telegram.
```

No P.S. — worldwide company, geo-specific data not applicable.

#### Example 3 — Adult, worldwide — Cell D

```
Subject: Telegram ads (paid & native) — adult, 60+ countries ✅

Formats: video, native banners, adult ai-engagement
Placements: TG channels, bots, mini-apps, groups and closed communities
11M+ views/month, CTR 1.7% – @moslender, built-in anti-fraud

Sergo,
Telegram: https://t.me/moslender
WhatsApp: +55 81 985688828

adsgram.ai - Tier 1 ads network in telegram.
```

No Work with line (no adult client names available yet). No P.S. (worldwide).

#### Example 4 — Cell B, iGaming, Brazil, headline "Profitable UA"

```
Subject: Profitable UA with Telegram — Brazil ✅

CPM from $0.90, anti-fraud filtering, 11M+ views/month

Formats: text, video, native banners
Placements: TG channels, bots, mini-apps, groups and closed communities
11M+ views/month, CTR 1.7% – @moslender, built-in anti-fraud
Work with: 1xBet

Sergo,
Telegram: https://t.me/moslender
WhatsApp: +55 81 985688828

adsgram.ai - Tier 1 ads network in telegram.

P.S. 80K views/month in Brazil, CPM $2.50
```

---

## Base: Personalized Pitch (v2)

Use this structure for Cells A and C — when a company signal is available.

### Message Structure

Every cold email has three paragraphs:

```
[Paragraph 1 — WHO: Product intro (no "I'm Sergo")]

[Paragraph 2 — WHY YOU: Personalized observation + "have you tried Telegram?" + test period offer]

[Paragraph 3 — CTA: Offer to send details, soft ask]
```

### Paragraph 1 — Product introduction

The recipient should understand within 5 seconds what's being offered. **Do NOT start with "I'm Sergo from..."** — the sender name is already in the email header.

**Template:**
```
AdsGram.ai — ad slots in Telegram (text, video, native)
across channels, bots, and mini-apps in 60+ countries.
11M+ views/month with built-in anti-fraud filtering.
```

### Paragraph 2 — Personalization + Telegram question + test period

This paragraph connects the research signal to our offer. It has three beats:

1. **Observation** — what we found about their company (one fact, recent)
2. **Telegram question** — "have you tried Telegram as an acquisition channel?" attached to the observation with a dash
3. **Test period** — we're offering a test period to check audience quality

**Template:**
```
I see [observation about company] — have you tried Telegram
as a paid channel? We're offering a test period right now
to check audience quality for your markets.
```

**How the observation adapts to different signal types:**

| Signal type | Example observation |
|---|---|
| Digital/paid activity | `I see you're running paid across Google, Meta, TikTok for [Company]` |
| Sponsorship/partnership | `I see [Company] sponsored [event/deal]` |
| Market expansion | `I see [Company] is scaling across [region] — [specific detail]` |
| Ambassador/brand deal | `I see [Company] signed [person] as brand ambassador` |
| Hiring | `I see [Company] is hiring for UA/marketing roles in [region]` |
| Product launch | `I see [Company] just launched [product/feature]` |
| Award/recognition | `I see [Company] was named [award]` |
| No strong signal | `I see [Company] is active across [N] markets in [region]` |

**What NOT to do after the observation:**
- Don't add evaluations: "That's a huge story" / "big brand push" / "impressive growth"
- Don't add bridges: "That's a lot of new audience to reach"
- Don't make claims: "but you're not buying Telegram traffic yet"

Just: fact → dash → question → test period.

### Paragraph 3 — CTA

Soft CTA that asks for interest, not commitment.

**Available CTAs:**

| CTA | When to use |
|---|---|
| `Want me to send the details?` | Default — simplest |
| `I can send the breakdown.` | For performance leads |
| `I can share a test case from [vertical] — interested?` | When a relevant case study exists |
| `Happy to share what's working for [vertical] advertisers in [region].` | When no case study but vertical experience exists |

**Banned CTAs:**
- `Worth a shot to test?` — cheap
- `Happy to show you` — servile
- `Got 15 min this week?` — pushy, too early for first touch
- `Open to a quick chat?` — weak
- `Want to set up a test campaign?` — premature
- `Feel free to reach me` — template phrase

### Signature

Always end with:
```
Sergo
```

No "Sergo, BD at AdsGram.ai" in the body — that's in the email client signature. Exception: if the email is sent via LinkedIn or a channel without signatures, add "Sergo, BD at AdsGram.ai".

### Subject Line (Personalized Pitch)

Generate **two subject line variants** (A/B) for testing. Each must be:
- Under 40 characters
- Contains the company name or a specific number
- No clickbait, no ALL CAPS, no exclamation marks

**Two patterns:**

| Pattern | Example |
|---|---|
| **A — Product-first** | `Telegram ads (paid & native) — [vertical], [geo]` |
| **B — Data-first** | `$1.20 CPM for [Company] in Telegram` |

---

## Role-Based CTA (for Personalized Pitch)

When writing a Personalized Pitch, adapt the CTA angle to the lead's role.
Use data from CRM columns **Notes** (contains `Headline:` and `Role desc:`)
and **Sources & Signals** (contains `Hiring:` signals).

### Step 1: Determine Role Tier

| Tier | Roles | Default CTA angle |
|------|-------|-------------------|
| 1 | Media Buyer, Traffic Manager, UA Manager | CPM от $0.90, новый инвентарь, anti-fraud, цифры по гео |
| 2 | Affiliate Manager, Growth Manager, Performance Marketing | Новый источник трафика, объём 11M+ views, тест-период |
| 3 | CMO, Marketing Director, Head of Marketing | 950M+ аудитория Telegram, новый канал, конкуренты ещё не здесь |
| 4 | BD Manager, Partnerships, C-level (CEO, COO, Founder) | Стратегическое партнёрство, низкий барьер входа |

### Step 2: Refine with Headline

Read `Headline:` from Notes. If it gives a more specific signal than the title alone — use it to sharpen the CTA.

| Headline signal | CTA refinement |
|-----------------|----------------|
| Contains "UA" or "Acquisition" | Focus on new inventory + CPM numbers for their geo |
| Contains "Growth" or "Scale" | Focus on untapped channel + audience size |
| Contains "Profitable" or "ROI" or "ROAS" | Lead with CPM numbers + anti-fraud |
| Contains region name (e.g. "LatAm", "Africa") | Add geo-specific data from benchmarks |
| Contains "Affiliate" or "Traffic" | Focus on volume (11M+ views) + test period |

### Step 3: Check Hiring Signals

Read `Hiring:` from Sources & Signals. If the company is hiring for ICP roles:

- **Hiring in a specific region** → company is expanding there → mention Telegram inventory in that region
- **Hiring UA/Media Buyer roles** → team is growing → position AdsGram as a channel worth adding to the mix
- **Multiple hiring signals** → rapid expansion → emphasize scale and 60+ countries

### Step 4: Compose CTA

Priority order:
1. If headline gives a precise signal → use headline-driven CTA
2. If hiring signal matches the region → use expansion-driven CTA
3. Otherwise → use default CTA angle from Role Tier table

**Example combinations:**

| Title | Headline | Hiring signal | CTA |
|-------|----------|---------------|-----|
| Media Buyer | "Scaling UA in LatAm" | Hiring: UA Manager, São Paulo | "CPM $2.50 in Brazil, 80K views/month — untapped by most UA teams" |
| CMO | "Building [Company] into #1 operator" | — | "950M+ Telegram users, most iGaming advertisers haven't tested it yet" |
| Affiliate Manager | — | Hiring: Media Buyer, LATAM | "11M+ views/month, test period available — new source for your expanding team" |
| Growth Manager | "Driving Growth via Paid & Organic" | — | "New paid channel to test: Telegram. CPM from $0.90, built-in anti-fraud" |

**Fallback:** If headline and hiring signals are both empty — use the default CTA angle from the Role Tier table. This is still better than a generic CTA because it's matched to the role.

---

## Data Sources

| Input | Source | Pipeline stage |
|-------|--------|----------------|
| Company signal: expanding to new geo | Web search in Pre-Enricher | Pre-Enricher |
| Company signal: new product/brand | Web search in Pre-Enricher | Pre-Enricher |
| Company signal: looking for traffic | Job postings, affiliate chats, LinkedIn posts | Pre-Enricher |
| Signal freshness (≤6 months) | Date from source | Pre-Enricher |
| Role pain: headline | Apollo `headline` field | Searcher / Enricher |
| Role pain: job description | Apollo `employment_history[current=true].description` | Searcher / Enricher |

## Open Items

- [x] Role Pain tagline table — done (8 signals with Pain + Pain relief)
- [x] Company Signal relief table — done (3 signals)
- [x] Cell A — confirmed (tagline + signal in subject + P.S. as example)
- [x] Cell B — confirmed (tagline + geo-only P.S.)
- [x] Cell C — confirmed (signal relief + metric-driven subject)
- [x] Cell D — confirmed (generic Product Card as-is)
- [x] ~~Define "headline with specifics" vs "generic"~~ — not needed, tagline table keywords serve as classifier
- [x] Integrate matrix into Outreach Writer AGENT.md — done (process steps, CELL in output format)
- [x] Update pipeline contracts to pass headline and job description through to CRM — done (all 4 contracts + 5 agents updated)
