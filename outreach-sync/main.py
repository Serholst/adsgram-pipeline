#!/usr/bin/env python3
"""
AdsGram Outreach CRM Sync Pipeline.

Extracts dialog data from Telegram "Outreach" folder, enriches via AdsGram
dashboard, computes lead statuses, syncs to Google Sheets CRM, and sends
a weekly report to Saved Messages.

Usage (from adsgram-pipeline/):
    python3 outreach-sync/main.py --mode full
    python3 outreach-sync/main.py --mode update
    python3 outreach-sync/main.py --mode report
    python3 outreach-sync/main.py --mode full --skip-enrich --dry-run
"""

import argparse
import asyncio
import json
import os
import sys
import time
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup — import shared tools from ../tools/
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_DIR / "tools"))

from sheets_helper import (  # noqa: E402
    _get_client,
    _col_letter,
    _load_env,
    _append_rows_with_retry,
    _open_sheet,
)

# ---------------------------------------------------------------------------
# Dependency checks
# ---------------------------------------------------------------------------

try:
    from telethon import TelegramClient
    from telethon.errors import FloodWaitError
    from telethon.tl.functions.messages import GetDialogFiltersRequest
    from telethon.tl.types import (
        DialogFilter,
        InputPeerChannel,
        InputPeerChat,
        InputPeerUser,
    )
except ImportError:
    print("ERROR: telethon not installed. Run: pip install telethon", file=sys.stderr)
    sys.exit(1)

try:
    from playwright.async_api import async_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

STATE_PATH = SCRIPT_DIR / "state.json"

OUTREACH_CRM_HEADERS = [
    "id", "name", "tg_handle", "adsgram_id", "source",
    "first_message_date", "last_message_date", "last_message_from",
    "my_consecutive_msgs", "client_ever_replied", "days_since_activity",
    "status", "status_override", "notes", "last_script_run", "email",
]
CRM_COL = {name: i for i, name in enumerate(OUTREACH_CRM_HEADERS)}
PROTECTED_COLS = {"status_override", "notes", "id"}

DATE_FMT = "%d.%m.%Y"
WRITE_RETRIES = 3
WRITE_BACKOFF = 5

STREAMLIT_URL = "https://adsgram-dashboard.streamlit.app/Moderation"


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def log(step: str, msg: str):
    print(f"  [{step}] {msg}", file=sys.stderr)


def load_state() -> dict:
    if not STATE_PATH.exists():
        return {"last_run": None, "contacts": {}}
    try:
        data = json.loads(STATE_PATH.read_text())
        data.setdefault("contacts", {})
        return data
    except (json.JSONDecodeError, KeyError):
        log("state", "corrupt state file, starting fresh")
        return {"last_run": None, "contacts": {}}


def save_state(state: dict):
    state["last_run"] = datetime.now().isoformat(timespec="seconds")
    tmp = STATE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2))
    tmp.rename(STATE_PATH)


def parse_args():
    p = argparse.ArgumentParser(description="AdsGram Outreach CRM Sync")
    p.add_argument("--mode", choices=["full", "update", "report"], default="full")
    p.add_argument("--skip-enrich", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args()


# ---------------------------------------------------------------------------
# Step 1: EXTRACT (Telethon)
# ---------------------------------------------------------------------------

def _peer_id(peer) -> int:
    for attr in ("user_id", "channel_id", "chat_id"):
        if hasattr(peer, attr):
            return getattr(peer, attr)
    return 0


async def find_outreach_folder(client):
    result = await client(GetDialogFiltersRequest())
    filters = getattr(result, "filters", result)
    for f in filters:
        if not isinstance(f, DialogFilter):
            continue
        title = f.title
        if hasattr(title, "text"):
            title = title.text
        if title == "Outreach":
            return f
    return None


async def get_folder_dialogs(client, folder):
    ids = {_peer_id(p) for p in folder.include_peers}
    all_dialogs = await client.get_dialogs()
    return [d for d in all_dialogs if d.entity.id in ids]


async def extract_dialog(client, dialog, state_entry, mode):
    entity = dialog.entity
    if getattr(entity, "deleted", False):
        return None

    name = ""
    if hasattr(entity, "first_name"):
        name = ((entity.first_name or "") + " " + (entity.last_name or "")).strip()
    elif hasattr(entity, "title"):
        name = entity.title or ""
    name = name or "No_name"
    username = getattr(entity, "username", None) or "no_username"

    min_id = 0
    if mode == "update" and state_entry and state_entry.get("last_msg_id"):
        min_id = state_entry["last_msg_id"]

    first_date = last_date = last_from = None
    consecutive = 0
    counting = True
    replied = False
    newest_id = None

    async for msg in client.iter_messages(entity, min_id=min_id):
        if msg.id == min_id:
            continue
        if newest_id is None:
            newest_id = msg.id
        if last_date is None:
            last_date = msg.date
            last_from = "me" if msg.out else "them"
        first_date = msg.date
        if counting:
            if msg.out:
                consecutive += 1
            else:
                counting = False
        if not msg.out:
            replied = True

    # Merge with state for incremental mode
    if mode == "update" and state_entry:
        if last_date is None:
            return None  # no new messages
        if state_entry.get("first_message_date"):
            first_date_str = state_entry["first_message_date"]
        else:
            first_date_str = first_date.strftime(DATE_FMT) if first_date else ""
        if state_entry.get("client_ever_replied"):
            replied = True
        if counting and state_entry.get("my_consecutive_msgs"):
            consecutive += state_entry["my_consecutive_msgs"]
    else:
        first_date_str = first_date.strftime(DATE_FMT) if first_date else ""

    if last_date is None:
        return None

    return {
        "name": name,
        "tg_handle": username,
        "entity_id": entity.id,
        "first_message_date": first_date_str or (first_date.strftime(DATE_FMT) if first_date else ""),
        "last_message_date": last_date.strftime(DATE_FMT),
        "last_message_from": last_from or "",
        "my_consecutive_msgs": consecutive,
        "client_ever_replied": replied,
        "last_msg_id": newest_id or (state_entry or {}).get("last_msg_id", 0),
        "adsgram_id": (state_entry or {}).get("adsgram_id", ""),
        "email": (state_entry or {}).get("email", ""),
    }


async def extract_all(client, state, mode):
    log("extract", "finding Outreach folder...")
    folder = await find_outreach_folder(client)
    if not folder:
        log("extract", "ERROR: folder 'Outreach' not found")
        sys.exit(1)

    log("extract", "loading dialogs...")
    dialogs = await get_folder_dialogs(client, folder)
    log("extract", f"found {len(dialogs)} dialogs")

    contacts = []
    errors = 0
    for i, dialog in enumerate(dialogs):
        handle = getattr(dialog.entity, "username", None) or "no_username"
        se = state["contacts"].get(handle.lower())
        try:
            c = await extract_dialog(client, dialog, se, mode)
            if c:
                contacts.append(c)
        except FloodWaitError as e:
            log("extract", f"  flood wait {e.seconds}s @{handle}, sleeping...")
            await asyncio.sleep(min(e.seconds, 30))
            try:
                c = await extract_dialog(client, dialog, se, mode)
                if c:
                    contacts.append(c)
            except Exception:
                errors += 1
        except Exception as e:
            log("extract", f"  ERROR @{handle}: {e}")
            errors += 1
        if (i + 1) % 20 == 0:
            log("extract", f"  {i + 1}/{len(dialogs)}")

    # In update mode, carry forward unchanged contacts from state
    if mode == "update":
        seen = {c["tg_handle"].lower() for c in contacts}
        for handle, se in state["contacts"].items():
            if handle not in seen and se.get("last_message_date"):
                contacts.append({
                    "name": se.get("name", ""),
                    "tg_handle": handle,
                    "entity_id": se.get("entity_id", 0),
                    "first_message_date": se.get("first_message_date", ""),
                    "last_message_date": se.get("last_message_date", ""),
                    "last_message_from": se.get("last_message_from", ""),
                    "my_consecutive_msgs": se.get("my_consecutive_msgs", 0),
                    "client_ever_replied": se.get("client_ever_replied", False),
                    "last_msg_id": se.get("last_msg_id", 0),
                    "adsgram_id": se.get("adsgram_id", ""),
                    "email": se.get("email", ""),
                })

    log("extract", f"done: {len(contacts)} contacts, {errors} errors")
    return contacts


# ---------------------------------------------------------------------------
# Step 2: ENRICH (Playwright, optional)
# ---------------------------------------------------------------------------

SEARCH_USERNAME_JS = """
async (usernames) => {
    const iframe = document.querySelector('iframe');
    if (!iframe) return JSON.stringify({error: 'no iframe'});
    const doc = iframe.contentDocument;
    const ns = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;
    function getInput(){
        return Array.from(doc.querySelectorAll('input[type="text"]'))
            .find(i=>i.placeholder&&i.placeholder.toLowerCase().includes('username'));
    }
    function readTable(){
        const t=doc.querySelectorAll('table');
        if(!t.length)return'NR';
        const r=[];
        t[0].querySelectorAll('tbody tr').forEach(tr=>{
            const c=[];tr.querySelectorAll('td').forEach(td=>c.push(td.textContent.trim()));r.push(c);
        });
        return r.length?r.map(x=>x[1]).join(','):'NR';
    }
    async function search(u){
        const inp=getInput();if(!inp)return{u,r:'no_input'};
        inp.focus();ns.call(inp,u);
        inp.dispatchEvent(new Event('input',{bubbles:true}));
        inp.dispatchEvent(new Event('change',{bubbles:true}));
        await new Promise(r=>setTimeout(r,50));
        inp.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',code:'Enter',keyCode:13,which:13,bubbles:true}));
        inp.dispatchEvent(new KeyboardEvent('keyup',{key:'Enter',code:'Enter',keyCode:13,which:13,bubbles:true}));
        await new Promise(r=>setTimeout(r,4000));
        return{u,r:readTable()};
    }
    const res=[];for(const u of usernames){res.push(await search(u));}
    return JSON.stringify(res);
}
"""

SEARCH_EMAIL_JS = """
async (ids) => {
    const iframe = document.querySelector('iframe');
    if (!iframe) return JSON.stringify({error: 'no iframe'});
    const doc = iframe.contentDocument;
    const ns = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;
    const res=[];
    for(const id of ids){
        const sbs=doc.querySelectorAll('.stSelectbox');
        const us=sbs[1];if(!us){res.push({id,email:''});continue;}
        const inp=us.querySelector('input');if(!inp){res.push({id,email:''});continue;}
        const sd=us.querySelector('[data-baseweb="select"]>div');
        if(sd)sd.click();await new Promise(r=>setTimeout(r,300));
        inp.focus();ns.call(inp,id+':');
        inp.dispatchEvent(new Event('input',{bubbles:true}));
        inp.dispatchEvent(new Event('change',{bubbles:true}));
        await new Promise(r=>setTimeout(r,500));
        const opts=doc.querySelectorAll('[role="option"]');
        let email='';
        for(const o of opts){const t=o.textContent.trim();
            if(t.startsWith(id+':')){email=t.split(':').slice(1).join(':').trim();break;}}
        res.push({id,email});
        inp.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',code:'Escape',keyCode:27,bubbles:true}));
        await new Promise(r=>setTimeout(r,200));
    }
    return JSON.stringify(res);
}
"""


async def enrich_contacts(contacts, skip=False):
    if skip:
        log("enrich", "skipped (--skip-enrich)")
        return
    if not HAS_PLAYWRIGHT:
        log("enrich", "skipped (playwright not installed)")
        return

    need_ids = [c for c in contacts
                if not c.get("adsgram_id") and c.get("tg_handle") != "no_username"]
    need_emails = [c for c in contacts
                   if c.get("adsgram_id")
                   and c["adsgram_id"] not in ("Not_registered", "No_username", "")
                   and not c.get("email")]

    if not need_ids and not need_emails:
        log("enrich", "all contacts already enriched")
        return

    log("enrich", "launching headless browser...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto(STREAMLIT_URL, timeout=60000)
            await page.wait_for_load_state("networkidle", timeout=60000)
            await page.wait_for_selector("iframe", timeout=30000)
            await page.wait_for_timeout(3000)
        except Exception as e:
            log("enrich", f"failed to load Streamlit: {e}")
            await browser.close()
            return

        # --- AdsGram ID lookup ---
        if need_ids:
            log("enrich", f"looking up AdsGram IDs for {len(need_ids)} contacts...")
            # Set dropdown to "Telegram username" mode
            try:
                frame = page.frame_locator("iframe").first
                sel = frame.locator('.stSelectbox').first
                await sel.locator('[data-baseweb="select"] > div').click()
                await page.wait_for_timeout(500)
                opts = frame.locator('[role="option"]')
                for i in range(await opts.count()):
                    t = await opts.nth(i).text_content()
                    if t and "elegr" in t.lower():
                        await opts.nth(i).click()
                        await page.wait_for_timeout(1000)
                        break
            except Exception as e:
                log("enrich", f"  could not set TG username mode: {e}")

            handle_map = {c["tg_handle"]: c for c in need_ids}
            BATCH = 8
            for start in range(0, len(need_ids), BATCH):
                batch = need_ids[start:start + BATCH]
                usernames = [c["tg_handle"] for c in batch]
                try:
                    raw = await page.evaluate(SEARCH_USERNAME_JS, usernames)
                    results = json.loads(raw)
                    if isinstance(results, dict):
                        continue
                    for r in results:
                        c = handle_map.get(r.get("u"))
                        if not c:
                            continue
                        val = r.get("r", "NR")
                        c["adsgram_id"] = val.split(",")[0].strip() if val not in ("NR", "no_input") else "Not_registered"
                except Exception as e:
                    log("enrich", f"  batch error: {e}")
                await page.wait_for_timeout(500)

            found = sum(1 for c in need_ids if c.get("adsgram_id") not in ("Not_registered", ""))
            log("enrich", f"AdsGram IDs: {found} found, {len(need_ids) - found} not registered")

        # --- Email lookup ---
        need_emails = [c for c in contacts
                       if c.get("adsgram_id")
                       and c["adsgram_id"] not in ("Not_registered", "No_username", "")
                       and not c.get("email")]
        if need_emails:
            log("enrich", f"looking up emails for {len(need_emails)} contacts...")
            # Set dropdown to "User" mode
            try:
                frame = page.frame_locator("iframe").first
                sel = frame.locator('.stSelectbox').first
                await sel.locator('[data-baseweb="select"] > div').click()
                await page.wait_for_timeout(500)
                opts = frame.locator('[role="option"]')
                for i in range(await opts.count()):
                    t = await opts.nth(i).text_content()
                    if t and t.strip() == "User":
                        await opts.nth(i).click()
                        await page.wait_for_timeout(1000)
                        break
            except Exception as e:
                log("enrich", f"  could not set User mode: {e}")

            ids = [c["adsgram_id"] for c in need_emails]
            id_map = {c["adsgram_id"]: c for c in need_emails}
            try:
                raw = await page.evaluate(SEARCH_EMAIL_JS, ids)
                results = json.loads(raw)
                if isinstance(results, list):
                    for r in results:
                        c = id_map.get(r.get("id"))
                        if c and r.get("email"):
                            c["email"] = r["email"]
            except Exception as e:
                log("enrich", f"  email lookup error: {e}")

            found = sum(1 for c in need_emails if c.get("email"))
            log("enrich", f"emails: {found}/{len(need_emails)} found")

        await browser.close()
    log("enrich", "done")


# ---------------------------------------------------------------------------
# Step 3: COMPUTE
# ---------------------------------------------------------------------------

def compute_all(contacts, today):
    for c in contacts:
        last_str = c.get("last_message_date", "")
        if not last_str:
            c["days_since_activity"] = 0
            c["status"] = "New"
            continue
        try:
            last_dt = datetime.strptime(last_str, DATE_FMT)
        except ValueError:
            c["days_since_activity"] = 0
            c["status"] = "New"
            continue

        days = max(0, (today - last_dt).days)
        c["days_since_activity"] = days
        cr = c.get("client_ever_replied", False)
        con = c.get("my_consecutive_msgs", 0)

        if not cr:
            if con >= 3:
                c["status"] = "Ghosting"
            elif con == 2:
                c["status"] = "Follow-up"
            else:
                c["status"] = "Initial Send"
        elif days >= 7:
            c["status"] = "Deprecated"
        elif c.get("last_message_from") == "me":
            c["status"] = "Need Response"
        else:
            c["status"] = "Active"

        if not c.get("adsgram_id"):
            c["adsgram_id"] = "No_username" if c.get("tg_handle") == "no_username" else "Not_registered"


# ---------------------------------------------------------------------------
# Step 4: SYNC (gspread via shared tools/sheets_helper.py)
# ---------------------------------------------------------------------------

def sync_crm(contacts, dry_run):
    sheet_id = os.environ.get("OUTREACH_SHEET_ID", "")
    if not sheet_id:
        log("sync", "ERROR: OUTREACH_SHEET_ID not set")
        sys.exit(1)

    ws = _open_sheet(sheet_id, "CRM")
    log("sync", "reading current CRM...")
    all_values = ws.get_all_values()

    existing = {}
    for i, row in enumerate(all_values[1:], start=2):
        handle = row[CRM_COL["tg_handle"]].strip().lower() if len(row) > CRM_COL["tg_handle"] else ""
        if handle:
            existing[handle] = {"row": i, "data": row}

    # Preserve enriched data from CRM: don't overwrite real IDs/emails
    # with empty or default values from extraction
    for c in contacts:
        handle = (c.get("tg_handle") or "no_username").lower()
        if handle not in existing:
            continue
        old = existing[handle]["data"]
        # Preserve adsgram_id if CRM has a real ID and contact doesn't
        old_aid = old[CRM_COL["adsgram_id"]].strip() if len(old) > CRM_COL["adsgram_id"] else ""
        new_aid = c.get("adsgram_id", "")
        if old_aid and old_aid not in ("Not_registered", "No_username") \
                and (not new_aid or new_aid in ("Not_registered", "No_username", "")):
            c["adsgram_id"] = old_aid
        # Preserve email if CRM has one and contact doesn't
        old_email = old[CRM_COL["email"]].strip() if len(old) > CRM_COL["email"] else ""
        if old_email and not c.get("email"):
            c["email"] = old_email

    now_str = datetime.now().strftime("%d.%m.%Y %H:%M")
    batch_updates = []
    new_rows = []
    stats = {"total_processed": len(contacts), "added_new": 0,
             "updated": 0, "skipped": 0, "errors": 0}
    next_id = len(all_values)

    for c in contacts:
        handle = (c.get("tg_handle") or "no_username").lower()
        if handle in existing:
            row_idx = existing[handle]["row"]
            old = existing[handle]["data"]
            changed = False
            for col_name, col_i in CRM_COL.items():
                if col_name in PROTECTED_COLS or col_name == "last_script_run":
                    continue
                if col_name == "client_ever_replied":
                    new_val = str(c.get(col_name, False)).upper()
                elif col_name in ("my_consecutive_msgs", "days_since_activity"):
                    new_val = str(c.get(col_name, 0))
                else:
                    new_val = str(c.get(col_name, ""))
                old_val = old[col_i] if col_i < len(old) else ""
                if new_val and new_val != old_val:
                    batch_updates.append({
                        "range": f"{_col_letter(col_i)}{row_idx}",
                        "values": [[new_val]],
                    })
                    changed = True
            batch_updates.append({
                "range": f"{_col_letter(CRM_COL['last_script_run'])}{row_idx}",
                "values": [[now_str]],
            })
            stats["updated" if changed else "skipped"] += 1
        else:
            row = [
                str(next_id), c.get("name", ""), c.get("tg_handle", ""),
                c.get("adsgram_id", ""), "telegram",
                c.get("first_message_date", ""), c.get("last_message_date", ""),
                c.get("last_message_from", ""), str(c.get("my_consecutive_msgs", 0)),
                str(c.get("client_ever_replied", False)).upper(),
                str(c.get("days_since_activity", 0)), c.get("status", ""),
                "", "", now_str, c.get("email", ""),
            ]
            new_rows.append(row)
            next_id += 1
            stats["added_new"] += 1

    log("sync", f"diff: {stats['added_new']} new, {stats['updated']} updated, "
        f"{stats['skipped']} unchanged")

    if dry_run:
        log("sync", "DRY RUN — no writes")
        return stats

    if batch_updates:
        for attempt in range(WRITE_RETRIES):
            try:
                ws.batch_update(batch_updates, value_input_option="USER_ENTERED")
                break
            except Exception as e:
                if attempt < WRITE_RETRIES - 1:
                    time.sleep(WRITE_BACKOFF * (attempt + 1))
                else:
                    raise

    if new_rows:
        _append_rows_with_retry(ws, new_rows)

    log("sync", "CRM updated")

    # Run Log
    ws_log = _open_sheet(sheet_id, "Run Log")
    ws_log.append_row([
        datetime.now().strftime(DATE_FMT),
        str(stats["total_processed"]), str(stats["added_new"]),
        str(stats["updated"]), str(stats["skipped"]), str(stats["errors"]),
    ], value_input_option="USER_ENTERED")
    log("sync", "Run Log updated")

    return stats


# ---------------------------------------------------------------------------
# Step 5: REPORT
# ---------------------------------------------------------------------------

async def send_report(client, contacts, stats):
    today = datetime.now()
    cutoff = today - timedelta(days=7)

    week = []
    for c in contacts:
        try:
            fd = datetime.strptime(c.get("first_message_date", ""), DATE_FMT)
            if fd >= cutoff:
                week.append(c)
        except ValueError:
            pass

    wc = Counter(c.get("status", "?") for c in week)
    report = f"📊 Outreach отчёт {today.strftime(DATE_FMT)}\n\n"
    report += f"Всего контактов: {len(contacts)}\n"
    report += f"Новых за неделю: {len(week)}\n"
    for s in ["Initial Send", "Active", "Follow-up", "Need Response", "Ghosting", "Deprecated"]:
        ch = "└" if s == "Deprecated" else "├"
        report += f"  {ch} {s}: {wc.get(s, 0)}\n"
    report += f"\nОбновлено: {stats.get('updated', 0)} | "
    report += f"Добавлено: {stats.get('added_new', 0)} | "
    report += f"Ошибок: {stats.get('errors', 0)}"

    await client.send_message("me", report)
    log("report", "sent to Saved Messages")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main():
    args = parse_args()
    _load_env()  # load .env into os.environ

    for key in ["TELEGRAM_API_ID", "TELEGRAM_API_HASH", "OUTREACH_SHEET_ID"]:
        if not os.environ.get(key):
            print(f"ERROR: {key} not set in .env", file=sys.stderr)
            sys.exit(1)

    session = os.environ.get("TELEGRAM_SESSION",
                             str(Path.home() / "Documents/Tools/telegram/telegram-checker/session"))

    print(f"=== Outreach Sync [{args.mode}] ===", file=sys.stderr)
    t0 = time.time()

    client = TelegramClient(session, int(os.environ["TELEGRAM_API_ID"]),
                            os.environ["TELEGRAM_API_HASH"])
    await client.start(phone=os.environ.get("TELEGRAM_PHONE"))
    log("init", "Telegram connected")

    today = datetime.now().replace(hour=23, minute=59, second=59)
    state = load_state()

    if args.mode == "report":
        ws = _open_sheet(os.environ["OUTREACH_SHEET_ID"], "CRM")
        rows = ws.get_all_values()
        contacts = []
        for r in rows[1:]:
            if len(r) < 12:
                continue
            contacts.append({
                "name": r[1], "tg_handle": r[2],
                "first_message_date": r[5], "last_message_date": r[6],
                "last_message_from": r[7],
                "my_consecutive_msgs": int(r[8]) if r[8].isdigit() else 0,
                "client_ever_replied": r[9].upper() == "TRUE",
                "status": r[11],
            })
        compute_all(contacts, today)
        await send_report(client, contacts, {"updated": 0, "added_new": 0, "errors": 0})
        await client.disconnect()
        return

    # Step 1
    contacts = await extract_all(client, state, args.mode)

    # Step 2
    await enrich_contacts(contacts, skip=args.skip_enrich)

    # Step 3
    compute_all(contacts, today)

    # Step 4
    stats = sync_crm(contacts, args.dry_run)

    # Step 5
    if not args.dry_run:
        await send_report(client, contacts, stats)

    # Save state
    if not args.dry_run:
        for c in contacts:
            h = (c.get("tg_handle") or "no_username").lower()
            state["contacts"][h] = {
                "entity_id": c.get("entity_id", 0),
                "name": c.get("name", ""),
                "last_msg_id": c.get("last_msg_id", 0),
                "first_message_date": c.get("first_message_date", ""),
                "last_message_date": c.get("last_message_date", ""),
                "last_message_from": c.get("last_message_from", ""),
                "my_consecutive_msgs": c.get("my_consecutive_msgs", 0),
                "client_ever_replied": c.get("client_ever_replied", False),
                "adsgram_id": c.get("adsgram_id", ""),
                "email": c.get("email", ""),
            }
        save_state(state)
        log("state", "saved")

    await client.disconnect()
    print(f"\n=== Done in {time.time() - t0:.1f}s ===", file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(main())
