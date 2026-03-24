"""Configuration: loads .env and defines constants."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")


def _require_env(key: str) -> str:
    val = os.environ.get(key)
    if not val:
        raise RuntimeError(f"Missing required environment variable: {key}. Check your .env file.")
    return val


def _optional_env(key: str, default: str) -> str:
    return os.environ.get(key, default)


# --- API ---
APOLLO_API_KEY = _require_env("APOLLO_API_KEY")
API_BASE_URL = "https://api.apollo.io/api/v1"

# --- Rate limits ---
RATE_LIMIT_RPM = int(_optional_env("RATE_LIMIT_RPM", "50"))
DAILY_CREDIT_LIMIT = int(_optional_env("DAILY_CREDIT_LIMIT", "500"))
REQUEST_TIMEOUT = 30  # seconds

# --- Paths ---
EXCEL_PATH = Path(_optional_env("EXCEL_PATH", str(BASE_DIR / "crm_companies.xlsx")))
BACKUP_DIR = Path(_optional_env("BACKUP_DIR", str(BASE_DIR / "backups")))
CREDIT_TRACKER_FILE = BASE_DIR / ".credits.json"
LOG_FILE = BASE_DIR / "apollo_operations.log"

# --- Default search titles ---
TARGET_TITLES = [
    "Media Buyer",
    "Traffic Manager",
    "User Acquisition Manager",
    "Performance Marketing Manager",
    "Head of Media Buying",
    "Growth Manager",
    "Business Development Manager",
    "Sales",
    "Sales Manager"
]

# --- Batch processing ---
SAVE_EVERY_N = 10  # save Excel after every N contacts processed
MAX_CONSECUTIVE_ERRORS = 5
