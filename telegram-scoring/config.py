"""
Central configuration module.
Loads .env secrets and all /business/ YAML files at import time.
Fails fast with clear messages if anything is missing or malformed.
"""

import os
import types
import yaml
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
BUSINESS_DIR = BASE_DIR / "business"

load_dotenv(BASE_DIR / ".env")


# ---------------------------------------------------------------------------
# Secrets — fail fast if missing
# ---------------------------------------------------------------------------

def _require_env(key: str) -> str:
    val = os.getenv(key, "").strip()
    if not val:
        raise SystemExit(
            f"ERROR: Missing required env var: {key}\n"
            f"Copy .env.example to .env and fill in all values."
        )
    return val


def _optional_env(key: str, default: str = "") -> str:
    return os.getenv(key, default).strip()


SOURCE_SHEET_ID = _require_env("SOURCE_SHEET_ID")
SOURCE_SHEET_NAME = _optional_env("SOURCE_SHEET_NAME", "work")
SCORED_SHEET_NAME = f"scored_{SOURCE_SHEET_NAME}"
GOOGLE_CREDENTIALS_PATH = _optional_env("GOOGLE_CREDENTIALS_PATH", "credentials.json")

# Source column names
SOURCE_HANDLE_COLUMN = _optional_env("SOURCE_HANDLE_COLUMN", "TG username")
SOURCE_MESSAGE_COLUMN = _optional_env("SOURCE_MESSAGE_COLUMN", "Message they sent in the chat")
SOURCE_BIO_COLUMN = _optional_env("SOURCE_BIO_COLUMN", "Profile's bio")
SOURCE_CHAT_COLUMN = _optional_env("SOURCE_CHAT_COLUMN", "Name of the chat")
SOURCE_REASON_COLUMN = _optional_env("SOURCE_REASON_COLUMN", "Reason why this is \"our\" client")
SOURCE_OFFER_COLUMN = _optional_env("SOURCE_OFFER_COLUMN", "What can we offer")
BD_MANAGER_COLUMN = _optional_env("BD_MANAGER_COLUMN", "BD Manager")
BD_MANAGER_DEFAULT = _optional_env("BD_MANAGER_DEFAULT", "Sergey")
SOURCE_STATUS_COLUMN = _optional_env("SOURCE_STATUS_COLUMN", "status")
SENDER_NAME = _optional_env("SENDER_NAME", "Sergo")

DEEPSEEK_API_KEY = _require_env("DEEPSEEK_API_KEY")

# ---------------------------------------------------------------------------
# Business YAMLs — fail fast if missing or malformed
# ---------------------------------------------------------------------------

def _load_yaml(filename: str) -> dict:
    path = BUSINESS_DIR / filename
    if not path.exists():
        raise SystemExit(
            f"ERROR: Missing business config: {path}\n"
            f"Ensure all files exist in the business/ directory."
        )
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if data is None:
            raise SystemExit(f"ERROR: Empty business config: {path}")
        return data
    except yaml.YAMLError as e:
        raise SystemExit(f"ERROR: Malformed YAML in {path}:\n{e}")


BIZ = types.SimpleNamespace(
    product=_load_yaml("adsgram_product.yaml"),
    niches=_load_yaml("niches.yaml"),
    prioritization=_load_yaml("prioritization.yaml"),
    fit_scoring=_load_yaml("fit_scoring.yaml"),
)

# ---------------------------------------------------------------------------
# Runtime constants
# ---------------------------------------------------------------------------

PIPELINE_VERSION = "3.0.0"

# Canonical role and segment enums — single source of truth
ROLES = {"Publisher", "Advertiser", "Agency", "Unclear", "Trash"}
PITCH_ROLES = {"Publisher", "Advertiser", "Agency"}
SKIP_SEGMENTS = {"Trash", "Exclude", "Defer"}
PITCH_SEGMENTS = {"Hot", "Warm", "Cold"}

# ---------------------------------------------------------------------------
# Output columns — single source of truth for scored sheet write order
# ---------------------------------------------------------------------------

SCORED_COLUMNS = [
    "handle",
    "segment",
    "messages_combined",
    "draft_pitch",
    "final_pitch",
    "contact_date",
    "msg_role",
    "msg_niche_signal",
]

