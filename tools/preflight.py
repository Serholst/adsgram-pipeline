#!/usr/bin/env python3
"""
Pre-flight credential & config validation for AdsGram Pipeline.

Runs lightweight checks BEFORE the main pipeline to fail fast on
broken credentials instead of discovering issues 10 minutes in.

Checks:
  1. .env exists and contains required variables
  2. Google Sheets credentials file exists and is valid JSON
  3. Gmail token file exists
  4. Telegram bot token is valid (getMe API call)
  5. PIPELINE_MODE is set
  6. Apollo API key & credits (soft check — skipped if key not set)

Exit codes:
  0 — all checks passed  (stdout: JSON with status=ok)
  1 — one or more checks failed (stdout: JSON with status=fail)

Usage:
    python3 tools/preflight.py           # human-readable output
    python3 tools/preflight.py --json    # machine-readable JSON
    python3 tools/preflight.py --help    # show this help
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path


SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
ENV_PATH = PROJECT_DIR / ".env"

REQUIRED_ENV_VARS = [
    "TG_BOT_TOKEN",
    "TG_OPERATOR_CHAT_ID",
    "GOOGLE_CREDENTIALS_PATH",
]


# ---------------------------------------------------------------------------
# Env loader (same as validate_data.py — no external deps)
# ---------------------------------------------------------------------------

def _load_env():
    if not ENV_PATH.exists():
        return
    for line in ENV_PATH.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


# ---------------------------------------------------------------------------
# Individual checks — each returns (ok: bool, detail: str)
# ---------------------------------------------------------------------------

def check_env_file():
    """Check that .env exists and contains required variables."""
    if not ENV_PATH.exists():
        return False, f".env not found at {ENV_PATH}"

    missing = []
    for var in REQUIRED_ENV_VARS:
        if not os.environ.get(var):
            missing.append(var)

    if missing:
        return False, f"Missing env vars: {', '.join(missing)}"
    return True, "all required vars present"


def check_google_credentials():
    """Check that Google Sheets credentials file exists and is valid JSON."""
    creds_path = os.environ.get("GOOGLE_CREDENTIALS_PATH", "")
    if not creds_path:
        return False, "GOOGLE_CREDENTIALS_PATH not set"

    path = Path(creds_path)
    if not path.is_absolute():
        path = PROJECT_DIR / path

    if not path.exists():
        return False, f"credentials file not found: {path}"

    try:
        data = json.loads(path.read_text())
        # Minimal sanity: service account JSON must have these keys
        for key in ("client_email", "private_key"):
            if key not in data:
                return False, f"credentials JSON missing '{key}' field"
    except json.JSONDecodeError as e:
        return False, f"credentials file is not valid JSON: {e}"

    return True, f"valid ({path.name})"


def check_gmail_token():
    """Check that Gmail token file exists."""
    token_path_str = os.environ.get("GMAIL_TOKEN_PATH", "")
    if token_path_str:
        token_path = Path(token_path_str)
        if not token_path.is_absolute():
            token_path = PROJECT_DIR / token_path
    else:
        # Default path matching validate_data.py
        token_path = PROJECT_DIR / "skills" / "gmail-drafter" / "token.json"

    if not token_path.exists():
        return False, f"Gmail token not found: {token_path}"

    try:
        json.loads(token_path.read_text())
    except json.JSONDecodeError as e:
        return False, f"Gmail token is not valid JSON: {e}"

    return True, f"exists ({token_path.name})"


def check_telegram_bot():
    """Validate TG bot token with a getMe call (no messages sent)."""
    token = os.environ.get("TG_BOT_TOKEN", "")
    if not token:
        return False, "TG_BOT_TOKEN not set"

    url = f"https://api.telegram.org/bot{token}/getMe"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            if data.get("ok"):
                bot_name = data.get("result", {}).get("username", "unknown")
                return True, f"bot @{bot_name}"
            return False, f"getMe returned ok=false: {data}"
    except urllib.error.HTTPError as e:
        return False, f"getMe HTTP {e.code}: token likely invalid"
    except Exception as e:
        return False, f"getMe failed: {e}"


def check_pipeline_mode():
    """Check that PIPELINE_MODE is set."""
    mode = os.environ.get("PIPELINE_MODE", "")
    if not mode:
        return False, "PIPELINE_MODE not set"
    return True, mode


def check_apollo_credits():
    """Check Apollo API key validity and remaining credits.

    Soft check: returns ok=True when APOLLO_API_KEY is not set
    (Apollo is optional in some pipeline runs).
    """
    api_key = os.environ.get("APOLLO_API_KEY", "")
    if not api_key:
        return True, "APOLLO_API_KEY not set — Apollo checks skipped"

    url = "https://api.apollo.io/api/v1/users/search"
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
    }

    try:
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())

        # Extract credit info from the response
        # Apollo users/search returns a list of users with team credit usage
        users = data.get("users", [])
        if not users:
            # Key is valid (got 200) but no user data — treat as ok
            return True, "Apollo API reachable, credit info unavailable"

        team_info = users[0].get("team", {}) if users else {}
        credits_remaining = None

        # Try multiple known paths for credit data
        for field in (
            "credits_remaining",
            "available_credits",
            "remaining_credits",
        ):
            val = team_info.get(field)
            if val is not None:
                credits_remaining = val
                break

        if credits_remaining is None:
            # API reachable and key valid, but credits field not found
            return True, "Apollo API reachable (credit details not in response)"

        if credits_remaining == 0:
            return False, "0 credits — enrichment will be skipped"

        return True, f"{credits_remaining} credits remaining"

    except urllib.error.HTTPError as e:
        if e.code == 401:
            return False, "Apollo API key invalid (HTTP 401)"
        return False, f"Apollo API error (HTTP {e.code})"
    except Exception as e:
        return False, f"Apollo API unreachable: {e}"


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

ALL_CHECKS = [
    ("env_file", check_env_file),
    ("google_credentials", check_google_credentials),
    ("gmail_token", check_gmail_token),
    ("telegram_bot", check_telegram_bot),
    ("pipeline_mode", check_pipeline_mode),
    ("apollo_credits", check_apollo_credits),
]


def run_all():
    """Run all checks, return (checks_dict, errors_list)."""
    checks = {}
    errors = []

    for name, fn in ALL_CHECKS:
        try:
            ok, detail = fn()
        except Exception as e:
            ok, detail = False, f"unexpected error: {e}"

        checks[name] = {"ok": ok, "detail": detail}
        if not ok:
            errors.append(f"{name}: {detail}")

    return checks, errors


def main():
    parser = argparse.ArgumentParser(
        description="Pre-flight credential & config validation for AdsGram Pipeline.",
        epilog="Exit 0 = all ok, Exit 1 = something broken.",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output machine-readable JSON instead of human text",
    )
    args = parser.parse_args()

    _load_env()
    checks, errors = run_all()

    if args.json:
        if errors:
            result = {"status": "fail", "errors": errors, "checks": checks}
        else:
            result = {"status": "ok", "checks": checks}
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("=" * 50)
        print("  AdsGram Pre-flight Check")
        print("=" * 50)
        for name, info in checks.items():
            icon = "OK" if info["ok"] else "FAIL"
            print(f"  [{icon:>4}]  {name}: {info['detail']}")
        print("=" * 50)
        if errors:
            print(f"  RESULT: FAIL ({len(errors)} error(s))")
        else:
            print("  RESULT: ALL CHECKS PASSED")
        print("=" * 50)

    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
