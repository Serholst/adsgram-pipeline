# Outreach Rules, Checklists & Output Format

## Pre-Pitch Research (mandatory)

Before writing any pitch, do TWO things:

### 1. Verify the lead is still current

Apollo data goes stale — people change jobs, get promoted, or leave companies.

**Run a web search:**
- Query: `"[Full Name]" "[Company]" LinkedIn 2026`
- Check if they still work at the stated company in a matching role

**Based on results:**
- **Confirmed** → proceed to write pitch
- **Role changed** → adjust pitch angle accordingly
- **Left company** → skip the pitch, recommend Lead Status → "Skip"
- **Cannot verify** → warn the user, suggest sending anyway but flagging risk

### 2. Find a personalization signal (for Personalized Pitch structure only)

Search for something specific and recent about the lead or their company:
- Company expanding to new markets
- Recent sponsorship deals or partnerships
- Hiring activity (posting UA/marketing roles)
- Awards or industry recognition
- New product launches
- Conference appearances
- Their specific ad channels (what platforms they run paid on)

**Search queries to try:**
- `"[Company]" 2025 2026 expansion marketing`
- `"[Company]" sponsorship partnership`
- `"[Full Name]" [Company] marketing`

**Signal search order:**
1. First check Sources & Signals column in CRM — signal may already be there
2. If not → web search: `"[Company]" 2025 2026 expansion marketing`
3. If not → web search: `"[Name]" "[Company]" speaker OR conference`
4. If not → use company data (vertical, country, size) for generic-but-relevant signal. Mark as weak signal.

---

## Language Rules

**Detect the lead's native language based on their country and write the email in that language.** The goal is to sound natural to the recipient, not to default to English.

| Country / Region | Language |
|---|---|
| Brazil | Portuguese |
| Mexico, Colombia, Argentina, Spain | Spanish |
| Russia, Ukraine, Belarus, Kazakhstan, CIS | Russian |
| Italy | Italian |
| Turkey | Turkish |
| Germany | German |
| All other countries | English |

**When writing in a non-English language:**
- The email body and subject lines must be in the lead's language
- All briefing metadata (ВЕРИФИКАЦИЯ, STRUCTURE, СИГНАЛ, GEO LOGIC, NEXT STEP) stays in English so Sergo can read it
- Add a one-line note after the email: `ЯЗЫК: [language] — [why: country/name cues]`
- If unsure about the lead's language, default to English and flag it

**General rules:**
- Use **simple, clear phrasing** regardless of language — avoid complex idioms
- Keep the body under **600 characters** (excluding subject line)
- If the user explicitly asks for a different language, follow their instruction

---

## Forbidden Elements

- **No placeholders** — never write $X, X% CTR, [insert number]. If you don't have the data, don't reference it.
- **No invented metrics** — never write "$500/mo", "40% reduction", "3x ROAS" unless the user provides these.
- **No compliments or evaluations** — "interesting project!", "solid numbers!", "impressive growth!", "big brand push", "huge story" are all banned.
- **No mentoring tone** — "many companies don't realize...", "you might not know..."
- **No emoji** unless the user specifically requests it.
- **No AI-template phrases** — "I hope this message finds you well", "I wanted to reach out", "I came across your profile".
- **No cheap sales phrases** — "so now is a good time to test", "you won't want to miss this".
- **No complex phrasal verbs** — write for non-native speakers. "have you tried" > "have you tapped into".
- **No "Largest Telegram ad network"** — state the product, not superlatives.
- **No "I'm Sergo from..."** — sender identity is in the email header. Don't waste body space on it.
- **No "feel free to reach me"** — template phrase. Just list contacts without preamble.
- **Never remove or "fix" the `t.me/moslender` link in the CTR range** — it is intentional.

---

## Output Format

For each lead, output:

```
## [Lead Name] — [Company]

ВЕРИФИКАЦИЯ: [Confirmed / Role changed / Left company / Cannot verify — 1 sentence]
STRUCTURE: [Product Card / Personalized Pitch — and why]
СИГНАЛ: [What specific signal we found — 1-2 sentences] (Personalized Pitch only)
GEO LOGIC: [Single market: [country] / Worldwide: [reason] — determines subject geo and P.S. presence]

To: [email address from CRM]
Subject: [subject line — one for Product Card, A+B for Personalized Pitch]

```[ready-to-send message]```

NEXT STEP: [what to do if they reply / don't reply]
```

For batch mode, output all leads sequentially with `---` separators.

**If lead did not pass verification** (Left company / Cannot verify):

```
## [Lead Name] — [Company]
ВЕРИФИКАЦИЯ: Left company — LinkedIn shows [new employer] since [date].
РЕКОМЕНДАЦИЯ: Пропустить. Lead Status → "Skip".
```

---

## Pre-Send Checklist

### Product Card checklist:
- [ ] Subject has format: `Telegram ads (paid & native) — [vertical], [geo]`
- [ ] Vertical matches the **company's** industry
- [ ] Geo: single market (1 country) → country name; 2+ markets or offshore HQ → "60+ countries"
- [ ] Formats line matches vertical (iGaming: text/video/native; Adult: video/native/adult ai-engagement)
- [ ] Stats line: `11M+ views/month, CTR 1.7% – @moslender, built-in anti-fraud` — link intact
- [ ] Clients line: present for iGaming (1xBet), omitted for adult/VPN
- [ ] Signature: just `Sergo` + contacts, no title, no CTA text
- [ ] P.S.: present ONLY for single-market leads, absent for worldwide
- [ ] P.S. data matches benchmarks table for the lead's country
- [ ] Language matches the lead's country
- [ ] No greeting ("Hey [Name]"), no "I'm Sergo", no storytelling

### Personalized Pitch checklist:
- [ ] Paragraph 1 explains what AdsGram sells (no "I'm Sergo from...")
- [ ] Paragraph 2 has ONE observation + Telegram question + test period mention
- [ ] Paragraph 3 has a soft CTA
- [ ] Language matches the lead's country
- [ ] Simple, clear phrasing — no complex idioms in any language
- [ ] No evaluations or compliments after facts
- [ ] No placeholders ($X, X%)
- [ ] No invented numbers
- [ ] Signature is just "Sergo" (no title in body)
- [ ] Under 600 characters body
- [ ] Output includes To: email address

---

## ⚠️ Periodic Reminder (every 40 emails)

**STOP AND RE-READ THIS:** The CTR line in the Product Card body (`CTR 1.7% – @moslender`) contains the Telegram handle after the dash. This is INTENTIONAL. Do not replace it with a number. Do not remove it. This is a deliberate design choice by the user. If you have generated 40+ emails in this session, re-confirm this is still in place.

---

## CRM Update

Update the CRM **only after an explicit user command** like "отправлено", "sent", "processed", "обновляй CRM". Never update proactively — even if the pitch is approved, the user may not have sent it yet.

When the user confirms:
- Set **Lead Status** to "Processed"
- Set **First Contact Date** to today
- Set **Suggested CTA** to the full email text that was sent
- Set **Stage** to "1st letter sent"
