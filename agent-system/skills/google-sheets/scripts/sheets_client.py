#!/usr/bin/env python3
"""
Universal Google Sheets client for the AdsGram pipeline.
Uses service account credentials. Supports read/write/update on any spreadsheet.

Usage:
  python sheets_client.py <command> --sheet-id <ID> [options]

Commands:
  read-all         Read all rows from a sheet
  read-headers     Read only the header (first) row
  read-row         Read a specific row by 1-based index (--row N)
  append           Append a row (--data '["val1","val2",...]')
  update-cell      Update a single cell (--row R --col C --value V)
  list-sheets      List all sheets/tabs in the spreadsheet

Options:
  --sheet-id ID    Spreadsheet ID (required)
  --sheet NAME     Sheet/tab name (default: first sheet)
  --gid GID        Sheet GID as alternative to --sheet
  --creds PATH     Path to service account credentials.json
                   (default: /Users/sergopro/Documents/adsgram/adsgram-pipeline/credentials.json)
  --row N          Row number (1-based)
  --col N          Column number (1-based)
  --value V        Cell value
  --data JSON      JSON array of values for a row
  --format         Output format: table | json (default: table)
"""

import argparse
import json
import sys
import time
from pathlib import Path

DEFAULT_CREDS = "/Users/sergopro/Documents/adsgram/adsgram-pipeline/credentials.json"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
MAX_RETRIES = 3
BACKOFF_BASE = 2  # seconds


def build_client(creds_path: str):
    try:
        from google.oauth2.service_account import Credentials
        import gspread
    except ImportError:
        print("ERROR: Missing dependencies. Run: pip install gspread google-auth", file=sys.stderr)
        sys.exit(1)

    creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    return gspread.authorize(creds)


def with_retry(fn, *args, **kwargs):
    """Call fn with exponential backoff on transient errors."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            err = str(e)
            is_transient = any(x in err for x in ["429", "500", "503", "RATE_LIMIT", "quota"])
            if attempt == MAX_RETRIES or not is_transient:
                raise
            wait = BACKOFF_BASE ** attempt
            print(f"  [retry {attempt}/{MAX_RETRIES}] {err[:80]} — waiting {wait}s...", file=sys.stderr)
            time.sleep(wait)


def open_sheet(client, sheet_id: str, sheet_name: str = None, gid: int = None):
    """Open a spreadsheet and return the target worksheet."""
    spreadsheet = with_retry(client.open_by_key, sheet_id)

    if gid is not None:
        for ws in spreadsheet.worksheets():
            if ws.id == gid:
                return ws
        raise ValueError(f"No sheet with gid={gid} found in spreadsheet {sheet_id}")

    if sheet_name:
        return with_retry(spreadsheet.worksheet, sheet_name)

    return spreadsheet.sheet1


def format_table(rows: list[list]) -> str:
    """Render rows as a simple ASCII table."""
    if not rows:
        return "(empty)"

    # Normalize row lengths
    max_cols = max(len(r) for r in rows)
    normalized = [r + [""] * (max_cols - len(r)) for r in rows]

    # Column widths
    widths = [max(len(str(normalized[r][c])) for r in range(len(normalized)))
              for c in range(max_cols)]

    sep = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
    lines = [sep]
    for i, row in enumerate(normalized):
        line = "| " + " | ".join(str(v).ljust(widths[c]) for c, v in enumerate(row)) + " |"
        lines.append(line)
        if i == 0:  # header separator
            lines.append(sep)
    lines.append(sep)
    return "\n".join(lines)


def cmd_read_all(ws, fmt: str):
    rows = with_retry(ws.get_all_values)
    if fmt == "json":
        if rows:
            headers = rows[0]
            data = [dict(zip(headers, r)) for r in rows[1:]]
            print(json.dumps({"headers": headers, "rows": data}, ensure_ascii=False, indent=2))
        else:
            print(json.dumps({"headers": [], "rows": []}))
    else:
        print(format_table(rows))
        print(f"\nTotal: {len(rows)} rows, {len(rows[0]) if rows else 0} columns")


def cmd_read_headers(ws, fmt: str):
    row = with_retry(ws.row_values, 1)
    if fmt == "json":
        print(json.dumps(row, ensure_ascii=False))
    else:
        for i, h in enumerate(row, 1):
            print(f"  {i:>3}. {h}")


def cmd_read_row(ws, row_num: int, fmt: str):
    values = with_retry(ws.row_values, row_num)
    headers = with_retry(ws.row_values, 1)
    if fmt == "json":
        print(json.dumps(dict(zip(headers, values)), ensure_ascii=False, indent=2))
    else:
        print(format_table([headers, values]))


def cmd_append(ws, data: list, fmt: str):
    result = with_retry(ws.append_row, data, value_input_option="USER_ENTERED")
    if fmt == "json":
        print(json.dumps({"status": "ok", "updated_range": str(result)}))
    else:
        print(f"OK — appended row: {data}")


def cmd_update_cell(ws, row: int, col: int, value: str, fmt: str):
    with_retry(ws.update_cell, row, col, value)
    if fmt == "json":
        print(json.dumps({"status": "ok", "row": row, "col": col, "value": value}))
    else:
        print(f"OK — updated R{row}C{col} = {value!r}")


def cmd_list_sheets(client, sheet_id: str, fmt: str):
    spreadsheet = with_retry(client.open_by_key, sheet_id)
    sheets = with_retry(spreadsheet.worksheets)
    if fmt == "json":
        data = [{"id": ws.id, "title": ws.title, "rows": ws.row_count, "cols": ws.col_count}
                for ws in sheets]
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(f"{'GID':>10}  {'Title':<40}  Rows x Cols")
        print("-" * 60)
        for ws in sheets:
            print(f"{ws.id:>10}  {ws.title:<40}  {ws.row_count} x {ws.col_count}")


def main():
    parser = argparse.ArgumentParser(description="Universal Google Sheets CLI client")
    parser.add_argument("command", choices=["read-all", "read-headers", "read-row",
                                            "append", "update-cell", "list-sheets"])
    parser.add_argument("--sheet-id", required=True, help="Spreadsheet ID")
    parser.add_argument("--sheet", default=None, help="Sheet/tab name")
    parser.add_argument("--gid", type=int, default=None, help="Sheet GID")
    parser.add_argument("--creds", default=DEFAULT_CREDS, help="Path to credentials.json")
    parser.add_argument("--row", type=int, default=None, help="Row number (1-based)")
    parser.add_argument("--col", type=int, default=None, help="Column number (1-based)")
    parser.add_argument("--value", default=None, help="Cell value")
    parser.add_argument("--data", default=None, help="JSON array of row values")
    parser.add_argument("--format", dest="fmt", choices=["table", "json"], default="table")

    args = parser.parse_args()

    if not Path(args.creds).exists():
        print(f"ERROR: Credentials file not found: {args.creds}", file=sys.stderr)
        sys.exit(1)

    client = build_client(args.creds)

    if args.command == "list-sheets":
        cmd_list_sheets(client, args.sheet_id, args.fmt)
        return

    ws = open_sheet(client, args.sheet_id, sheet_name=args.sheet, gid=args.gid)

    if args.command == "read-all":
        cmd_read_all(ws, args.fmt)

    elif args.command == "read-headers":
        cmd_read_headers(ws, args.fmt)

    elif args.command == "read-row":
        if not args.row:
            print("ERROR: --row required for read-row", file=sys.stderr)
            sys.exit(1)
        cmd_read_row(ws, args.row, args.fmt)

    elif args.command == "append":
        if not args.data:
            print("ERROR: --data required for append", file=sys.stderr)
            sys.exit(1)
        data = json.loads(args.data)
        cmd_append(ws, data, args.fmt)

    elif args.command == "update-cell":
        if not (args.row and args.col and args.value is not None):
            print("ERROR: --row, --col, --value required for update-cell", file=sys.stderr)
            sys.exit(1)
        cmd_update_cell(ws, args.row, args.col, args.value, args.fmt)


if __name__ == "__main__":
    main()
