---
name: gmail-drafter
version: 1.0.0
description: "Creates Gmail draft emails from approved outreach pitches. Does NOT send — drafts appear in Gmail for manual review and sending. Trigger when user says: 'создай черновики', 'create drafts', 'загрузи в Gmail', 'подготовь драфты', 'draft emails', or after outreach pitch approval at Checkpoint 2."
---

# Gmail Draft Creator

## What It Does

Takes approved pitches from Outreach Writer and creates Gmail drafts.
User reviews drafts in Gmail and sends manually. No emails are sent
automatically.

## Prerequisites

### First-Time Setup (user does manually)

1. **Enable Gmail API** in Google Cloud Console
   (use existing GCP project or create new)

2. **Create OAuth2 Desktop App credential:**
   - Google Cloud Console → APIs & Services → Credentials
   - Create OAuth Client ID → Desktop App
   - Download JSON → save as `gmail_credentials.json` in project root

3. **Install dependencies:**
   ```bash
   pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
   ```

4. **Run auth flow** (needs browser access — run from terminal, not Claude Code):
   ```bash
   python agent-system/skills/gmail-drafter/create_drafts.py --auth-only
   ```
   This opens a browser, user grants consent, `token.json` is saved.
   Subsequent runs use the token silently.

### Scope
`https://www.googleapis.com/auth/gmail.compose` — can only create
drafts and send emails. Cannot read inbox, delete messages, or
modify existing emails.

## Input

List of approved pitches. For each pitch:
- `to` — recipient email address
- `subject` — subject line (use Subject A by default, Subject B if user specifies)
- `body` — ready-to-send message text
- `lead_name` — for reporting

## How to Use

### Step 1: Prepare batch JSON

Create a temporary file with approved pitches:

```json
[
  {
    "to": "a.fedorov@adguard.com",
    "subject": "4M+ views/mo for AdGuard in TG",
    "body": "Hello Andrey,\n\nI see AdGuard is hosting...",
    "lead_name": "Andrey Fedorov"
  },
  {
    "to": "grows.vladi@proxy-seller.com",
    "subject": "$1.93 CPM for Proxy-Seller in TG",
    "body": "Hello Vladyslav,\n\nI see Proxy-Seller...",
    "lead_name": "Vladyslav Halaktionov"
  }
]
```

### Step 2: Run the script

```bash
python agent-system/skills/gmail-drafter/create_drafts.py --batch-file /tmp/drafts_batch.json
```

### Step 3: Parse output

Script returns JSON:
```json
{
  "status": "success",
  "drafts_created": 2,
  "drafts_failed": 0,
  "total": 2,
  "results": [
    {
      "status": "created",
      "draft_id": "r1234567890",
      "message_id": "msg-abc123",
      "to": "a.fedorov@adguard.com",
      "subject": "4M+ views/mo for AdGuard in TG",
      "lead_name": "Andrey Fedorov"
    }
  ]
}
```

Status values: `success` (all created), `partial` (some failed),
`blocked` (all failed or auth error).

## Subject Line Selection

Outreach Writer produces Subject A and Subject B for each lead.
By default use **Subject A** (volume-first). Override rules:

- User says "Subject B" or "CPM-first" → use Subject B for all
- User specifies per-lead → follow their choice
- If unsure → ask user at Checkpoint 2

## Step 4: Update CRM after drafts created

After successful draft creation, **immediately** update CRM for all leads in the batch:

```bash
python3 tools/sheets_helper.py crm-update-cells /tmp/crm_draft_updates.json
```

For each lead with a draft:

- **Stage** → `Draft`
- **First Contact Date** → today's date
- **Suggested CTA** → full email text (Subject + Body)

For warning/skip leads (drafts prepared but flagged):

- **Stage** → `Draft`
- **First Contact Date** → today's date
- **Notes** → append `OUTREACH SKIP: [reason]` (use `"+|text"` prefix for append)

⚠️ **Do NOT skip this step.** First Contact Date must be set at draft creation time.

See `agent-system/reference/outreach-rules.md` → "CRM Update" for full rules.

## Error Handling

- **Auth expired** → script prints error with re-auth instructions.
  User must run `--auth-only` from terminal.
- **credentials.json missing** → script prints setup instructions.
- **Single draft fails** → continue with remaining, report as `partial`.
- **All drafts fail** → report as `blocked` with error details.

## Language

Communicate with user in Russian. Script output in English (JSON).
