---
name: adsgram-autopipeline
version: 3.0.0
description: "Automated AdsGram prospecting pipeline: takes a vertical+GEO or domain list, delegates to the Orchestrator agent which runs the full 7-agent chain (Pre-Enricher → Searcher → Discoverer → Enricher → CRM Writer → Outreach Writer) with two checkpoints. Trigger when user says: 'автопоиск', 'autopipeline', 'запусти пайплайн', 'автопроспектинг', 'pipeline iGaming Brazil', 'найди лидов автоматом', or any prospecting request where the user wants minimal interaction. Also trigger on standard prospecting phrases: 'найди лидов', 'поиск контактов', 'обогатить лиды', 'prospecting', 'find leads' — the pipeline handles the full cycle automatically."
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
Pre-Enricher → Searcher → Discoverer → [CP1] → Enricher → CRM Writer → Outreach Writer → [CP2]

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
