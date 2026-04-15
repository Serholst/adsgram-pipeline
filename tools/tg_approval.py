#!/usr/bin/env python3
"""
Telegram bot for pipeline approvals and notifications.

Usage:
    python3 tools/tg_approval.py approval --message "Enrichment: 15 leads × 1 credit = 15 credits. Approve?" [--timeout 600]
    python3 tools/tg_approval.py notify --message "Pipeline completed: 12 leads found"
    python3 tools/tg_approval.py error --message "Searcher failed: Apollo API timeout"

Environment variables:
    TG_BOT_TOKEN        — Telegram bot token from @BotFather
    TG_OPERATOR_CHAT_ID — Chat ID of the operator
    TG_DRY_RUN          — Set to "1" for mock responses (testing)

Returns JSON to stdout.
"""

import argparse
import json
import os
import re
import sys
import time


def _output(data):
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _die(msg: str):
    _output({"status": "error", "message": msg})
    sys.exit(1)


def _get_config():
    token = os.environ.get("TG_BOT_TOKEN", "")
    chat_id = os.environ.get("TG_OPERATOR_CHAT_ID", "")
    dry_run = os.environ.get("TG_DRY_RUN", "0") == "1"

    if not dry_run and (not token or not chat_id):
        _die("TG_BOT_TOKEN and TG_OPERATOR_CHAT_ID must be set. "
             "Use TG_DRY_RUN=1 for testing.")

    return token, chat_id, dry_run


def _parse_approval_reply(text: str) -> dict:
    """Parse operator's reply to an approval request.

    Recognized patterns:
        "да" / "yes" / "ок" / "ok" / "approve"      → approved (full budget)
        "нет" / "no" / "reject" / "отклонить"        → rejected
        "первые N" / "first N" / just a number "N"   → partial (budget=N)
    """
    text = text.strip().lower()

    if re.match(r"^(да|yes|ок|ok|approve|одобрить|go|ладно|давай)$", text):
        return {"status": "approved", "reply": text}

    if re.match(r"^(нет|no|reject|отклонить|skip|пропусти)$", text):
        return {"status": "rejected", "reply": text}

    m = re.match(r"^(?:первые|first)?\s*(\d+)$", text)
    if m:
        budget = int(m.group(1))
        return {"status": "partial", "reply": text, "budget": budget}

    # Unrecognized — return as-is, let caller decide
    return {"status": "unknown", "reply": text}


def cmd_approval(message: str, timeout: int, dry_run: bool,
                 token: str, chat_id: str):
    """Send approval request, wait for reply, return parsed response."""

    if dry_run:
        _output({"status": "approved", "reply": "да (dry-run)", "budget": 50,
                 "dry_run": True})
        return

    from telegram import Bot

    bot = Bot(token=token)

    # Send the approval request
    try:
        prefix = "🔔 *APPROVAL REQUIRED*\n\n"
        sent = bot.send_message(
            chat_id=chat_id,
            text=prefix + message + "\n\n_Ответь: да / нет / первые N_",
            parse_mode="Markdown",
        )
    except Exception as e:
        _output({"status": "error", "error": f"Telegram API send failed: {e}"})
        sys.exit(1)

    sent_msg_id = sent.message_id
    sent_time = time.time()

    # Poll for reply
    last_update_id = None
    while time.time() - sent_time < timeout:
        try:
            updates = bot.get_updates(
                offset=last_update_id,
                timeout=10,
                allowed_updates=["message"],
            )
        except Exception as e:
            _output({"status": "error", "error": f"Telegram API poll failed: {e}"})
            sys.exit(1)

        for update in updates:
            last_update_id = update.update_id + 1

            msg = update.message
            if msg is None:
                continue
            if str(msg.chat.id) != str(chat_id):
                continue
            # Only consider messages sent AFTER our request
            if msg.date.timestamp() < sent_time - 5:
                continue

            parsed = _parse_approval_reply(msg.text or "")
            _output(parsed)
            return

        time.sleep(2)

    # Timeout
    try:
        bot.send_message(
            chat_id=chat_id,
            text="⏰ Timeout — enrichment пропущен (безопасный дефолт).",
        )
    except Exception:
        pass  # Best-effort timeout notification
    _output({"status": "timeout"})


def cmd_notify(message: str, dry_run: bool, token: str, chat_id: str):
    """Send a notification (fire-and-forget)."""
    if dry_run:
        _output({"status": "sent", "dry_run": True})
        return

    from telegram import Bot

    bot = Bot(token=token)
    try:
        bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")
    except Exception as e:
        _output({"status": "error", "error": f"Telegram API send failed: {e}"})
        sys.exit(1)
    _output({"status": "sent"})


def cmd_error(message: str, dry_run: bool, token: str, chat_id: str):
    """Send an error notification (fire-and-forget)."""
    if dry_run:
        _output({"status": "sent", "dry_run": True})
        return

    from telegram import Bot

    bot = Bot(token=token)
    prefix = "🚨 *PIPELINE ERROR*\n\n"
    try:
        bot.send_message(chat_id=chat_id, text=prefix + message,
                         parse_mode="Markdown")
    except Exception as e:
        _output({"status": "error", "error": f"Telegram API send failed: {e}"})
        sys.exit(1)
    _output({"status": "sent"})


def main():
    parser = argparse.ArgumentParser(description="Telegram approval & notification tool")
    parser.add_argument("command", choices=["approval", "notify", "error"])
    parser.add_argument("--message", "-m", required=True, help="Message text")
    parser.add_argument("--timeout", "-t", type=int, default=600,
                        help="Timeout in seconds for approval (default: 600)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Return mock response without sending to TG")
    args = parser.parse_args()

    # --dry-run flag overrides env var
    token, chat_id, env_dry_run = _get_config()
    dry_run = args.dry_run or env_dry_run

    if args.command == "approval":
        cmd_approval(args.message, args.timeout, dry_run, token, chat_id)
    elif args.command == "notify":
        cmd_notify(args.message, dry_run, token, chat_id)
    elif args.command == "error":
        cmd_error(args.message, dry_run, token, chat_id)


if __name__ == "__main__":
    main()
