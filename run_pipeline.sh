#!/bin/bash
set -euo pipefail

# ─────────────────────────────────────────────────────────
# AdsGram Pipeline — Autonomous VPS runner with retry
# ─────────────────────────────────────────────────────────
# Usage:
#   ./run_pipeline.sh <vertical> <geo>
#   ./run_pipeline.sh igaming LATAM
#
# Or via cron with schedule.conf:
#   ./run_pipeline.sh --scheduled
# ─────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Load environment
if [[ -f .env ]]; then
    set -a
    source .env
    set +a
fi

export PIPELINE_MODE=autonomous
export PATH="$HOME/.local/bin:$PATH"

# ── TG helper ───────────────────────────────────────────
tg_notify() {
    python3 tools/tg_approval.py notify --message "$1" 2>/dev/null || true
}

tg_error() {
    python3 tools/tg_approval.py error --message "$1" 2>/dev/null || true
}

# ── Lock: prevent parallel runs ───────────────────────
LOCKFILE="/tmp/adsgram-pipeline.lock"

if command -v flock &>/dev/null; then
    exec 200>"$LOCKFILE"
    if ! flock -n 200; then
        tg_notify "⏭ Pipeline skipped — another instance is already running (flock)"
        exit 0
    fi
else
    if [[ -f "$LOCKFILE" ]]; then
        old_pid=$(cat "$LOCKFILE" 2>/dev/null || echo "")
        if [[ -n "$old_pid" ]] && kill -0 "$old_pid" 2>/dev/null; then
            tg_notify "⏭ Pipeline skipped — another instance is already running (PID $old_pid)"
            exit 0
        fi
        # Stale lock — remove it
        rm -f "$LOCKFILE"
    fi
    echo $$ > "$LOCKFILE"
    trap 'rm -f "$LOCKFILE"' EXIT
fi

# ── Config ──────────────────────────────────────────────
LOG_DIR="${SCRIPT_DIR}/logs/runs"
RETRY_INITIAL=30        # seconds
RETRY_CAP=300           # seconds max backoff
RETRY_WINDOW=1800       # 30 minutes total
DATE=$(date +%Y-%m-%d_%H%M)

mkdir -p "$LOG_DIR"
LOG_FILE="${LOG_DIR}/run-${DATE}.log"

# ── Parse args ──────────────────────────────────────────
VERTICAL=""
GEO=""

if [[ "${1:-}" == "--scheduled" ]]; then
    # Read from schedule.conf based on day of week
    DOW=$(date +%u)  # 1=Mon ... 7=Sun
    if [[ -f "${SCRIPT_DIR}/schedule.conf" ]]; then
        ENTRY=$(grep -v '^#' "${SCRIPT_DIR}/schedule.conf" | grep -v '^$' | sed -n "${DOW}p")
        VERTICAL=$(echo "$ENTRY" | awk '{print $1}')
        GEO=$(echo "$ENTRY" | awk '{print $2}')
    fi
    if [[ -z "$VERTICAL" || -z "$GEO" ]]; then
        echo "No schedule entry for day $DOW" | tee -a "$LOG_FILE"
        exit 0
    fi
elif [[ $# -ge 2 ]]; then
    VERTICAL="$1"
    GEO="$2"
else
    echo "Usage: $0 <vertical> <geo>  OR  $0 --scheduled"
    exit 1
fi

echo "=== Pipeline: $VERTICAL $GEO — $(date) ===" | tee -a "$LOG_FILE"

# ── Pre-flight checks ─────────────────────────────────
echo "Running pre-flight checks..." | tee -a "$LOG_FILE"
preflight_output=$(python3 tools/preflight.py --json 2>&1) || {
    echo "Pre-flight FAILED:" | tee -a "$LOG_FILE"
    echo "$preflight_output" | tee -a "$LOG_FILE"
    tg_error "Pre-flight failed — pipeline aborted.\n$(echo "$preflight_output" | python3 -c "import sys,json; d=json.load(sys.stdin); print(chr(10).join(d.get('errors',[])))" 2>/dev/null || echo "$preflight_output")" 2>/dev/null || true
    exit 1
}
echo "Pre-flight OK" | tee -a "$LOG_FILE"

# ── Cleanup ────────────────────────────────────────────
cleanup_old_logs() {
    find "$LOG_DIR" -name "run-*.log" -mtime +30 -delete 2>/dev/null || true
    echo "Old logs cleaned (>30 days)" >> "$LOG_FILE"
}

cleanup_stale_data() {
    # Clear previous pipeline data so a fresh run starts clean
    local state_file="${SCRIPT_DIR}/data/pipeline/pipeline-state.json"
    if [[ ! -f "$state_file" ]] || python3 -c "
import json,sys
d=json.load(open('$state_file'))
sys.exit(0 if d.get('status')=='done' or d.get('next_step')=='done' else 1)
" 2>/dev/null; then
        rm -f "${SCRIPT_DIR}"/data/pipeline/*.json 2>/dev/null || true
        echo "Stale pipeline data cleaned" >> "$LOG_FILE"
    fi
}

cleanup_old_logs
cleanup_stale_data

# ── Build prompt ────────────────────────────────────────
build_prompt() {
    local resume_json
    resume_json=$(python3 tools/pipeline_io.py resume 2>/dev/null || echo '{"next_step":"start"}')
    local next_step
    next_step=$(echo "$resume_json" | python3 -c "import sys,json; print(json.load(sys.stdin).get('next_step','start'))" 2>/dev/null || echo "start")

    if [[ "$next_step" == "start" || "$next_step" == "done" ]]; then
        echo "Run the autopipeline skill for vertical=$VERTICAL geo=$GEO."
    else
        echo "Resume the autopipeline from step '$next_step' for vertical=$VERTICAL geo=$GEO. Previous steps completed — check pipeline_io.py resume for details."
    fi
}

# ── Run with retry ──────────────────────────────────────
attempt=0
delay=$RETRY_INITIAL
start_time=$(date +%s)

tg_notify "🚀 Pipeline: *$VERTICAL / $GEO*"

while true; do
    attempt=$((attempt + 1))
    prompt=$(build_prompt)

    echo "--- Attempt $attempt at $(date) ---" | tee -a "$LOG_FILE"
    echo "Prompt: $prompt" >> "$LOG_FILE"

    # Apollo MCP tools — UUID comes from .claude/settings.json on each machine
    # Use pattern: mcp__*__apollo_* to allow all Apollo tools regardless of UUID
    ALLOWED_TOOLS="Bash,Read,Write,Glob,Grep,Agent"
    ALLOWED_TOOLS+=",mcp__*__apollo_mixed_people_api_search"
    ALLOWED_TOOLS+=",mcp__*__apollo_mixed_companies_search"
    ALLOWED_TOOLS+=",mcp__*__apollo_people_match"
    ALLOWED_TOOLS+=",mcp__*__apollo_people_bulk_match"
    ALLOWED_TOOLS+=",mcp__*__apollo_organizations_enrich"
    ALLOWED_TOOLS+=",mcp__*__apollo_contacts_create"
    ALLOWED_TOOLS+=",mcp__*__apollo_contacts_search"
    ALLOWED_TOOLS+=",mcp__*__apollo_contacts_update"
    ALLOWED_TOOLS+=",mcp__*__apollo_emailer_campaigns_search"
    ALLOWED_TOOLS+=",mcp__*__apollo_emailer_campaigns_add_contact_ids"
    ALLOWED_TOOLS+=",mcp__*__apollo_email_accounts_index"

    exit_code=0
    claude -p "$prompt" --allowedTools "$ALLOWED_TOOLS" 2>&1 | tee -a "$LOG_FILE" || exit_code=$?

    if [[ $exit_code -eq 0 ]]; then
        # Success — extract summary from log tail
        summary=$(tail -30 "$LOG_FILE" | grep -o '{.*"next_step".*}' | tail -1 || echo "completed")
        tg_notify "✅ Pipeline завершён: *$VERTICAL / $GEO*\nAttempt: $attempt\n$summary"

        # Clean state for next run
        python3 tools/pipeline_io.py clean 2>/dev/null || true
        echo "=== SUCCESS at $(date) ===" | tee -a "$LOG_FILE"
        exit 0
    fi

    # Check if retry window exhausted
    elapsed=$(( $(date +%s) - start_time ))
    if [[ $elapsed -ge $RETRY_WINDOW ]]; then
        # Get last completed step for error report
        last_step=$(python3 tools/pipeline_io.py resume 2>/dev/null \
            | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('last_completed','unknown'))" 2>/dev/null \
            || echo "unknown")

        tg_error "Pipeline failed after ${attempt} attempts (30 min).\nVertical: $VERTICAL / $GEO\nLast step: $last_step\nLog: $LOG_FILE"
        echo "=== FAILED after $attempt attempts at $(date) ===" | tee -a "$LOG_FILE"
        exit 1
    fi

    # Notify and retry
    tg_notify "⚠️ Attempt $attempt failed. Retrying in ${delay}s..."
    echo "Sleeping ${delay}s before retry..." | tee -a "$LOG_FILE"
    sleep "$delay"

    # Exponential backoff with cap
    delay=$(( delay * 2 ))
    if [[ $delay -gt $RETRY_CAP ]]; then
        delay=$RETRY_CAP
    fi
done
