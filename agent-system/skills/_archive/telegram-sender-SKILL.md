---
name: telegram-outreach-sender
description: "Full-cycle Telegram outreach: reads scored leads from Excel, writes personalized pitches following BD_SKILL rules, sends via Telegram Web, updates Excel with status and contact_date. Trigger when user says: 'обработай лидов', 'отправь питчи', 'разошли сообщения', 'send outreach', 'process scored sheet', or references a scored_* sheet in AdsGram RaviolliSCAN Excel file."
version: 1.0.0
---

# Telegram Outreach Sender — Full Cycle

You process scored Telegram leads from an Excel file: write personalized cold pitches, send them via Telegram Web, and update the Excel with status tracking.

---

## Context

**Product:** AdsGram.ai — Telegram-native ad network with wallet-based targeting and 1,000+ resources: channels, bots, groups, TMA, etc.
**Sender:** Sergo
**Source:** Scored leads from BD chat scanning pipeline (Excel file with `scored_*` sheets)

---

## Pipeline Overview

```
Step 1: READ — Load scored sheet, understand each lead
Step 2: CHECK HISTORY — Open Telegram Web, check existing conversations for ALL leads
Step 3: WRITE — Generate final_pitch + notes for each lead
Step 4: REVIEW — Present pitches to user for approval
Step 5: SEND — Send approved pitches via Telegram Web, get user confirmation per message
Step 6: UPDATE — Fill contact_date + status in Excel, save file
```

**CRITICAL: Step 2 (Check History) MUST happen BEFORE Step 3 (Write).** Never write a pitch without checking if there's an existing conversation. This prevents spam over active dialogs or rejected leads.

---

## Step 1: READ

Load the scored sheet from the Excel file. Expected columns:

| Column | Purpose |
|---|---|
| handle | Telegram handle (@username) |
| segment | Hot / Warm / Cold / Defer / Trash / Exclude |
| messages_combined | Original lead messages from BD chat + BIO |
| draft_pitch | LLM-generated draft (may be bad or empty) |
| final_pitch | YOUR output — the polished pitch |
| contact_date | Date of first contact (YOUR output) |
| msg_role | Advertiser / Publisher / Agency / Dev Studio / Unclear / Trash |
| msg_niche_signal | Detected niche (Crypto/TON/Web3, Gambling/Betting, etc.) |
| notes | YOUR output — justification for pitch or skip (max 2 sentences, Russian) |
| status | YOUR output — pipeline status |

**Filtering rules:**
- **Trash** → skip, write notes with reason
- **Exclude** → skip, write notes with reason
- **Defer** → skip (too cold for pitch), write notes with reason
- **Hot / Warm / Cold** → process (write pitch)

---

## Step 2: CHECK HISTORY (mandatory before writing)

For EVERY lead that needs a pitch, open Telegram Web and search for their handle. Check:

1. **No existing chat** → OK to send cold pitch
2. **Existing chat, no reply from lead** → Evaluate: if recent (<2 weeks), skip. If old, may re-approach.
3. **Existing chat, lead replied positively** → DO NOT send cold pitch. Mark as active dialog, needs personalized follow-up.
4. **Existing chat, lead declined** → DO NOT send cold pitch. Mark as "declined".
5. **Existing chat, lead ghosting** → Evaluate context. May send a different angle or skip.

**Record findings** for each lead before writing any pitches. This prevents wasted effort.

---

## Step 3: WRITE — Pitch Rules

### Core Rules (from BD_SKILL.md)

**Tone:** Friendly-professional, peer-level. No corporate language, no mentoring, no emoji (unless lead uses them).

**Language:** Match the lead's language from messages_combined. If unknown or mixed → English.

**Length:** Max 500 characters. Telegram format: short blocks with blank lines between them.

**Structure (all in one message, NOT separate lines for greeting):**

```
Hey, [Name]! [Fact-based observation from lead's message]

[Representation: who we are + product]

[Relevant angle for THIS lead]

[CTA: qualifying question or concrete next step]
```

**IMPORTANT:** "Hey, [Name]!" goes on the SAME LINE as the opening observation. No line break after greeting.

### Two Approach Modes

**Full pitch with AdsGram** — when lead clearly:
- Buys traffic or seeks ad tools
- Is agency with clients needing growth
- Is publisher with channel needing monetization
- Actively promotes project needing audience

Standard intro (EN): `I'm Sergo from AdsGram.ai — Telegram-native ad network with wallet-based targeting and 1,000+ resources: channels, bots, groups, TMA, etc.`
Standard intro (RU): `Я Sergo из AdsGram.ai — Telegram-native рекламная сеть с 1,000+ ресурсов: каналы, боты, группы, TMA и т.д.`

**Qualification without AdsGram** — when:
- Project status unknown
- Lead's role unclear
- Not enough context for specific offer

Qualification intro: `I'm Sergo, BD in Web3. I have a large network in Telegram.`

### CTA by Situation

| Situation | CTA |
|---|---|
| Lead ready to buy | `Want to set up a test campaign?` |
| Need qualification | `What does your current UA mix look like?` |
| Agency, need vertical | `What verticals are your clients mostly in?` |
| Publisher | `Интересно посмотреть какие ставки получают каналы в твоей нише?` |
| Unknown project status | `How's the project going right now — actively growing or pivoting?` |
| Partnership angle | `Could be worth exploring a referral setup — interested?` |
| Agency selling services | `Do your clients also need paid Telegram placements, or mostly organic engagement?` |

### Forbidden Elements

- Placeholders ($X, X% CTR)
- Invented numbers ("$500/mo", "40% reduction")
- "Want me to pull a channel list?"
- "Open to a quick chat?"
- "Largest Telegram ad network"
- Signature "Sergo" at the end
- Compliments after name ("interesting project!", "solid numbers!")
- Mentoring tone ("many projects don't realize...")
- Feature dumping

### Special Cases — Recognize and Adapt

- **Lead is a competitor/adjacent platform** (like Adexium) → partnership angle, NOT advertiser pitch
- **Lead sells services** (seeding, KOL, engagement) → they're agency, use qualification mode
- **Lead's msg_role is wrong** (e.g. labeled Advertiser but actually sells services) → override with correct approach

---

## Step 4: REVIEW

Present each pitch to the user before sending. For each lead show:
- Handle + Name + Segment
- The pitch text
- Reasoning (1-2 sentences): why this approach, what was fixed vs draft

Wait for user approval before proceeding to send.

---

## Step 5: SEND via Telegram Web

For each approved pitch:

1. Click Search in Telegram Web
2. Type the handle (without @)
3. Click the correct result
4. **CHECK for existing messages** — if found, STOP and inform user
5. Click message input field
6. Insert text via JavaScript (preserving line breaks):
```javascript
const msgInput = document.querySelector('[contenteditable="true"].form-control');
msgInput.focus();
document.execCommand('selectAll', false, null);
document.execCommand('delete', false, null);
const lines = text.split('\n');
for (let i = 0; i < lines.length; i++) {
    if (i > 0) document.execCommand('insertLineBreak', false, null);
    if (lines[i]) document.execCommand('insertText', false, lines[i]);
}
```
7. Take screenshot to verify
8. **Ask user for confirmation before clicking Send**
9. Click Send button
10. Take screenshot to confirm delivery

**After EACH send, provide reasoning to user:** what approach was chosen and why.

---

## Step 6: UPDATE Excel

After all sends are complete, update the Excel file:

### contact_date
- Leads sent TODAY → today's date
- Leads with prior conversation → date of original contact
- Leads not contacted → empty

### status (use these exact values for consistency with January sheet)

| Status | When to use |
|---|---|
| `1st letter sent` | First pitch sent today |
| `declined` | Lead already refused (found in TG history) |
| `ghosting` | Previously contacted, no meaningful response |
| `interested` | Lead showed interest |
| `Не отправлено` | Pitch ready but not sent (Defer segment or skipped) |
| `other (specify in the comments)` | Trash / Exclude / no action needed |

### notes
- For pitched leads: what was changed vs draft and why (max 2 sentences, Russian)
- For skipped leads: reason for skip (max 2 sentences, Russian)

Save the updated Excel to the workspace folder.

---

## Pre-Send Checklist

Before sending each pitch, silently verify:

- [ ] "Hey, [Name]!" is on the SAME line as the first sentence
- [ ] Language matches lead's messages_combined
- [ ] No placeholders or invented numbers
- [ ] No compliments in opening
- [ ] No "Sergo" signature at the end
- [ ] CTA leads to dialogue, not yes/no
- [ ] Under 500 characters
- [ ] Correct approach mode (full pitch vs qualification)
- [ ] No existing TG conversation that conflicts
- [ ] AdsGram intro uses standard formulation (if full pitch mode)
