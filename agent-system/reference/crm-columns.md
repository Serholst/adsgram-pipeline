# CRM Column Definitions & Write Rules

The CRM lives in Google Sheets (access via `tools/sheets_helper.py`).

## Columns

Company | Vertical | Country | Name | Title | Email | Email Status | Socials | Alt Contacts | Sources & Signals | Lead Status | Stage | First Contact Date | Last Activity Date | Suggested CTA | Notes

## Column definitions

- **Socials**: Social media profile links only. Format: `LinkedIn: [url] | TG: @handle | Twitter: @handle | IG: @handle`. Only profile links — no sources, no phone numbers.
- **Alt Contacts**: Phone, WhatsApp, alternative emails found during discovery. Format: `Phone: +number | WhatsApp: +number | Alt email: press@company.com`. Optional — fill only if data available.
- **Sources & Signals**: Source attribution + personalization signals for outreach. Format: `Source: Apollo, ZoomInfo | Conference: SiGMA 2025 | Hiring: UA Manager role in Lagos`.
- **Email Status**: "verified", "catchall", "unverified", "unavailable"
- **Lead Status**: Set based on verification results (Verified / Partially verified / Not verified / Needs review / Skip)
- **Stage**: leave empty (will be filled during outreach)
- **First Contact Date**: leave empty
- **Last Activity Date**: leave empty
- **Suggested CTA**: leave empty

## SKIP leads

**ALL leads must be written to CRM, including SKIP leads.** This ensures the CRM is a complete record of every person evaluated, preventing re-enrichment in future sessions.

SKIP leads (no email, irrelevant role, left company, etc.) are written to CRM with:
- **Lead Status**: "Skip"
- **Notes**: MUST include the skip reason. Examples:
  - "SKIP. No email returned from enrichment. No web contacts found."
  - "SKIP. Irrelevant role — Retail Sales Manager, not digital marketing."
  - "SKIP. Left company — LinkedIn shows new employer since 2025."
  - "SKIP. Role discrepancy — Apollo says Media Buyer, actually Administrative Analyst."
  - "SKIP. Duplicate — same person found under different Apollo record."
- **Email**: fill if available (even for skipped leads — useful for future dedup)
- **Socials**: fill with any discovered social links (even for skipped leads)
- **Alt Contacts**: fill with phone/WhatsApp if available
- **Sources & Signals**: fill with sources and signals (even for skipped leads)
- All other fields (Stage, dates, CTA): leave empty

## Stage column values

- `1st letter sent` — initial outreach sent
- `ghosting` — no response after follow-up
- `declined` — explicitly said no
- `interested` — positive response received
- `started working` — deal in progress
- `other` — specify in Notes

## Priority sorting

For new leads (within the batch being appended):
1. Director/VP roles first
2. Growth/UA/Media Buyer roles next
3. Generic Marketing/Sales roles last
4. Within each tier, larger companies first

## Fallback

If Google Sheets is not accessible, fall back to creating a standalone JSON report in the `outputs/` directory and notify the user. Do NOT create a separate report alongside the CRM — the CRM is the single deliverable.
