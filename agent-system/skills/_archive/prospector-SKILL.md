---
name: adsgram-prospector
version: 2.0.0
description: "AdsGram lead prospecting — reference skill. Domain knowledge for the 7-agent prospecting pipeline. NOT a standalone executable skill — the pipeline runs via autopipeline SKILL.md → Orchestrator. This file provides context and pointers to reference docs."
---

# AdsGram Lead Prospector

You are building an outbound prospecting pipeline for **AdsGram.ai** — a Telegram-native ad network. The goal is to find decision-makers at iGaming, VPN and crypto/web3 companies who buy traffic and could become AdsGram advertisers.

## AdsGram Context

AdsGram is a Telegram-native advertising platform. The value proposition for advertisers: access to Telegram's 950M+ user base through native ad formats (rewarded ads in mini-apps, sponsored messages) with wallet-based targeting and 100,000+ resources (channels, bots, groups, TMA). The target customer is someone who buys digital traffic — media buyers, UA managers, growth leads — at companies in verticals where Telegram audiences convert well: iGaming, VPN, Forex, Crypto, Adult.

### Pitch Angle for Advertiser Leads

Every lead found through this pipeline is a potential advertiser — someone who buys traffic for their product. When presenting leads or writing outreach notes, keep this framing in mind:

- **Pain point**: they need audience, traffic, UA for their project and are likely using Meta, Google, KOL, organic
- **AdsGram value**: Telegram as a new paid channel on top of their current mix — wallet-based targeting, CPM from $0.90, fast launch

## Pipeline Architecture (v1.6.0)

```
Pre-Enricher → Searcher → Discoverer → [CP1] → Enricher → CRM Writer → Outreach Writer → [CP2]
```

**Agents:** Pre-Enricher (FREE) → Searcher (FREE) → Discoverer (FREE) → Enricher (PAID) → CRM Writer → Outreach Writer

**Two checkpoints:**
- CP1: enrichment credit approval (after Discoverer, before Enricher)
- CP2: pitch approval (after Outreach Writer)

**Design principles:**
1. **Pre-enrich before Apollo search.** Apollo has systematic blind spots. Pre-Enricher discovers correct parent companies, verified domains, and decision maker names.
2. **One search per lead, three outputs.** Discoverer does contact discovery + role verification + bucket assignment in ONE web search per person.

## Reference Documents

All domain knowledge lives in `agent-system/reference/`:

| Document | What it contains | Read by |
|---|---|---|
| `reference/icp.md` | Target verticals, roles, seniorities, GEOs, B2B exclusion, Apollo search parameters | All agents |
| `reference/apollo-search-patterns.md` | 5 failure patterns, fallback ladder, parameter recipes | Searcher, Pre-Enricher, Orchestrator |
| `reference/company-db.md` | Company DB structure, exclusion/dedup gates (Steps 1a-1e) | Pre-Enricher, Searcher, CRM Writer |
| `reference/credit-management.md` | 6 credit management rules | Enricher, Orchestrator |
| `reference/crm-columns.md` | CRM column definitions, SKIP leads rules, priority sorting | CRM Writer |
| `reference/common-pitfalls.md` | Known failure modes from past sessions | All agents |

## Language

The user communicates in Russian. Respond in Russian. Google Sheets uses English column headers but Russian notes where appropriate.
