# Credit Management Rules

This is extremely important — the user has explicitly asked for careful credit management.

1. **Always check balance** before any paid operation: `apollo_users_api_profile` with `include_credit_usage: true`
2. **Always state the cost** before enrichment: "Это будет стоить N кредитов"
3. **Wait for explicit approval** — never auto-enrich
4. **Report any wasted credits** — if enrichment returns no email, acknowledge it
5. **Summarize spend** at the end: "Потрачено X кредитов, осталось Y"
6. **Minimize waste** — Discoverer web discovery should reduce the number of leads that need paid enrichment. If web search already found a verified email, skip Apollo enrichment for that lead.
