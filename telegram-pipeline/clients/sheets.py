"""
Google Sheets client — read source sheet, write scored results to same spreadsheet.
Auth via service account JSON file.
"""

import logging
import time
import gspread
from google.oauth2.service_account import Credentials
from config import (
    SOURCE_SHEET_ID, SOURCE_SHEET_NAME,
    SCORED_SHEET_NAME,
    GOOGLE_CREDENTIALS_PATH, SCORED_COLUMNS,
    PITCH_SEGMENTS,
)

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

LEGEND_SHEET_NAME = "Легенда"
WRITE_RETRIES = 3
WRITE_BACKOFF_BASE = 5  # seconds, multiplied by attempt number


def _append_row_with_retry(ws, row: list, table_range: str, retries: int = WRITE_RETRIES):
    """Append a row to the table, auto-expanding it. Retry on API errors."""
    for attempt in range(retries):
        try:
            ws.append_row(
                row,
                value_input_option="USER_ENTERED",
                table_range=table_range,
            )
            return
        except gspread.exceptions.APIError as e:
            if attempt < retries - 1:
                wait = WRITE_BACKOFF_BASE * (attempt + 1)
                logger.warning(
                    "Sheets API error (attempt %d/%d), retrying in %ds: %s",
                    attempt + 1, retries, wait, e,
                )
                time.sleep(wait)
            else:
                raise


def _cell_value(value) -> str:
    """Convert a lead field value to a sheet cell string."""
    return str(value) if value is not None else ""

# Russian descriptions for scored columns
COLUMN_DESCRIPTIONS = {
    "handle":                "Telegram username контакта (@ручка)",
    "segment":               "Сегмент приоритизации: Hot / Warm / Cold / Defer / Trash / Exclude",
    "messages_combined":     "Все сообщения от этого контакта (объединены через ---)",
    "draft_pitch":           "Черновик персонализированного аутрич-сообщения (сгенерирован LLM по плейбуку)",
    "final_pitch":           "Финальная версия питча после редактуры менеджером (заполняется вручную)",
    "contact_date":          "Дата контакта с лидом (заполняется вручную менеджером)",
    "msg_role":              "Роль по сообщению: Publisher / Advertiser / Agency / Unclear / Trash",
    "msg_niche_signal":      "Ниша, определённая из текста сообщения и bio",
}


class SheetsClient:
    def __init__(self):
        try:
            creds = Credentials.from_service_account_file(
                GOOGLE_CREDENTIALS_PATH, scopes=SCOPES
            )
        except FileNotFoundError:
            raise SystemExit(
                f"ERROR: Credentials file not found: {GOOGLE_CREDENTIALS_PATH}\n"
                f"Place your Google service account JSON file at the path above."
            )
        except Exception as e:
            raise SystemExit(f"ERROR: Invalid credentials file: {e}")

        try:
            gc = gspread.authorize(creds)
        except Exception as e:
            raise SystemExit(f"ERROR: Google Sheets authorization failed: {e}")

        try:
            self._source_spreadsheet = gc.open_by_key(SOURCE_SHEET_ID)
            self._source_ws = self._source_spreadsheet.worksheet(SOURCE_SHEET_NAME)
        except gspread.exceptions.SpreadsheetNotFound:
            raise SystemExit(
                f"ERROR: Source spreadsheet not found (ID: {SOURCE_SHEET_ID}).\n"
                f"Check SOURCE_SHEET_ID in .env."
            )
        except gspread.exceptions.WorksheetNotFound:
            raise SystemExit(
                f"ERROR: Source worksheet '{SOURCE_SHEET_NAME}' not found in spreadsheet.\n"
                f"Check SOURCE_SHEET_NAME in .env."
            )

        # Create or open scored sheet in the same spreadsheet
        try:
            self._scored_ws = self._source_spreadsheet.worksheet(SCORED_SHEET_NAME)
        except gspread.exceptions.WorksheetNotFound:
            self._scored_ws = self._source_spreadsheet.add_worksheet(
                title=SCORED_SHEET_NAME, rows=100, cols=len(SCORED_COLUMNS)
            )
            logger.info("Created scored sheet '%s'", SCORED_SHEET_NAME)

    def read_scored_handles(self) -> set[str]:
        """Return set of handles already present in the scored sheet."""
        try:
            col_values = self._scored_ws.col_values(1)  # column A = handle
        except Exception:
            return set()
        # Skip header row
        return set(col_values[1:]) if len(col_values) > 1 else set()

    def read_source_rows(self) -> list[dict]:
        """Return all rows from the source sheet as a list of dicts."""
        records = self._source_ws.get_all_records(numericise_ignore=["all"])
        logger.info("Read %d rows from source sheet '%s'", len(records), SOURCE_SHEET_NAME)
        return records

    def _ensure_headers(self, ws, columns: list[str], sheet_name: str):
        """Write columns as header row if the sheet is empty or has wrong headers."""
        first_row = ws.row_values(1)
        if first_row == columns:
            return
        if first_row:
            logger.warning(
                "%s has unexpected headers — clearing and rewriting.", sheet_name,
            )
            ws.clear()
        ws.append_row(columns, value_input_option="USER_ENTERED")
        logger.info("Wrote headers to '%s'", sheet_name)

    def clear_scored_sheet(self):
        """Clear data rows from scored sheet, preserving header row and table formatting."""
        row_count = self._scored_ws.row_count
        if row_count > 1:
            last_col = chr(ord('A') + len(SCORED_COLUMNS) - 1)
            self._scored_ws.batch_clear([f"A2:{last_col}{row_count}"])
        logger.info("Cleared data rows in scored sheet '%s'", SCORED_SHEET_NAME)

    def ensure_scored_headers(self):
        """Update header row in-place, preserving table formatting."""
        first_row = self._scored_ws.row_values(1)
        if first_row != SCORED_COLUMNS:
            last_col = chr(ord('A') + len(SCORED_COLUMNS) - 1)
            self._scored_ws.update(f"A1:{last_col}1", [SCORED_COLUMNS], value_input_option="USER_ENTERED")
            logger.info("Updated headers in '%s'", SCORED_SHEET_NAME)

    def write_scored_row(self, lead: dict):
        """Append one lead row to the scored table (auto-expands the table)."""
        row = []
        for col in SCORED_COLUMNS:
            if col in ("final_pitch", "contact_date"):
                row.append("")
            else:
                row.append(_cell_value(lead.get(col)))
        _append_row_with_retry(self._scored_ws, row, table_range="A1")

    def ensure_legend_sheet(self):
        """Create or refresh the Легенда sheet with Russian column descriptions."""
        try:
            ws = self._source_spreadsheet.worksheet(LEGEND_SHEET_NAME)
            ws.clear()
        except gspread.exceptions.WorksheetNotFound:
            ws = self._source_spreadsheet.add_worksheet(
                title=LEGEND_SHEET_NAME, rows=len(SCORED_COLUMNS) + 2, cols=3
            )

        rows = [["Столбец", "Описание (RU)", "Пример значения"]]
        examples = {
            "handle": "@durov",
            "segment": "Hot",
            "messages_combined": "Привет, хочу разместить рекламу в своём канале",
            "draft_pitch": "Привет! Видел, что у тебя канал @mychannel. AdsGram может автоматизировать продажу рекламы — без ручных переговоров. Давайте обсудим?",
            "final_pitch": "",
            "contact_date": "",
            "msg_role": "Publisher",
            "msg_niche_signal": "Crypto/TON/Web3",
        }
        for col in SCORED_COLUMNS:
            rows.append([
                col,
                COLUMN_DESCRIPTIONS.get(col, ""),
                examples.get(col, ""),
            ])

        ws.update(rows, value_input_option="USER_ENTERED")

        # Bold header row
        ws.format("A1:C1", {"textFormat": {"bold": True}})
        logger.info("Legend sheet '%s' updated (%d columns)", LEGEND_SHEET_NAME, len(SCORED_COLUMNS))
