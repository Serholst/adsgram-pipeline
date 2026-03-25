---
name: adsgram-autopipeline
version: 2.2.0
description: "Automated AdsGram prospecting pipeline: takes a vertical+GEO or domain list, auto-runs Apollo search, web verification, and CRM write — pausing only once for enrichment credit approval. Replaces the manual step-by-step prospector with a single-command flow. Trigger when user says: 'автопоиск', 'autopipeline', 'запусти пайплайн', 'автопроспектинг', 'pipeline iGaming Brazil', 'найди лидов автоматом', or any prospecting request where the user wants minimal interaction. Also trigger on standard prospecting phrases: 'найди лидов', 'поиск контактов', 'обогатить лиды', 'prospecting', 'find leads' — the pipeline handles the full cycle automatically."
---

# AdsGram Auto-Pipeline

## Step 1 → PROSPECTOR

Spawn a subagent:

```
Read the skill at [path to adsgram-prospector/SKILL.md].
Task: [user's request]
Find leads and write them to CRM, but do not enrich.
Return leads that need enrichment and Apollo credit balance.
```

---

## Step 2 → CHECKPOINT: Enrichment

Show the user what the prospector returned — enrichment candidates, cost, and balance.

Soft limit: 20 credits per session. If exceeded, warn but allow with confirmation.

- User approves → go to Step 3
- User declines → go to Step 4

---

## Step 3 → ENRICHER

Spawn a subagent:

```
Read the skill at [path to adsgram-prospector/SKILL.md].
Enrich these leads: [approved list from checkpoint]
Write results to CRM.
Return enrichment summary.
```

---

## Step 4 → OUTREACH

Spawn a subagent:

```
Read the skill at [path to adsgram-outreach/SKILL.md].
Write pitches for new leads in CRM (Google Sheets).
Return pitches.
```

---

## Step 5 → CHECKPOINT: Pitches

Show pitches to the user. Wait for approval.

- User approves → go to Step 6
- User declines → stop, pitches saved for later

---

## Step 6 → GMAIL DRAFTER

Spawn a subagent:

```
Read the skill at skills/gmail-drafter/SKILL.md.
Create Gmail drafts for approved pitches: [list with To, Subject, Body]
Return draft confirmations.
```

Drafts appear in Gmail for manual review. User sends manually.

---

## Step 7 → Summary

Print results from all steps.

---

## Language

Communicate with the user in Russian.
