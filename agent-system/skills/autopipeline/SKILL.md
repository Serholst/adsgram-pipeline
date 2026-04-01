---
name: adsgram-autopipeline
version: 3.0.0
description: "Automated AdsGram prospecting pipeline: takes a vertical+GEO, runs demand-side discovery to find companies with active acquisition budgets, then delegates to the Orchestrator agent which runs the full 7-agent chain (Pre-Enricher → Searcher → Discoverer → Enricher → CRM Writer → Outreach Writer) with two checkpoints. Trigger when user says: 'автопоиск', 'autopipeline', 'запусти пайплайн', 'автопроспектинг', 'pipeline iGaming Brazil', 'найди лидов автоматом', or any prospecting request. Also trigger on: 'найди лидов', 'поиск контактов', 'prospecting', 'find leads'. Input MUST be vertical+GEO format (e.g. 'iGaming Brazil', 'VPN Turkey'). Domain lists are not supported."
---

# AdsGram Auto-Pipeline

This skill is a thin entry point that delegates to the **Orchestrator agent** for the full prospecting → outreach cycle. The Orchestrator manages all 7 agents, retry logic, data routing, and checkpoints internally.

## Step 1 → ORCHESTRATOR

Spawn the Orchestrator agent:

```
Read agent-system/agents/orchestrator/AGENT.md.
Read agent-system/config/agent-config.md.
Task: [user's request]
Run the full prospecting → outreach pipeline.
The Orchestrator will pause at two checkpoints:
  - CHECKPOINT 1: enrichment credit approval (after Discoverer)
  - CHECKPOINT 2: pitch approval (after Outreach Writer)
```

The Orchestrator internally runs:
Pre-Enricher → Searcher → Discoverer → [CP1] → Enricher → CRM Writer (Python script) → Outreach Writer → [CP2]

Data flows through files in `/tmp/pipeline/`, not through Orchestrator context.
CRM Writer is a Python script (`tools/crm_writer.py`), not a Claude agent.

Wait for the Orchestrator to complete. It will return a SUMMARY with funnel metrics.

---

## Step 2 → GMAIL DRAFTER

After the Orchestrator completes and pitches are approved (CP2), spawn the Gmail Drafter:

```
Read the skill at agent-system/skills/gmail-drafter/SKILL.md.
Create Gmail drafts for approved pitches: [list with To, Subject, Body from Orchestrator output]
Return draft confirmations.
```

Drafts appear in Gmail for manual review. User sends manually.

---

## Step 3 → Summary

Print combined results:
- Orchestrator SUMMARY (funnel, credits, recommendations)
- Gmail Drafter results (drafts created, any failures)

---

## Language

Communicate with the user in Russian.
