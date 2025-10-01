#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="/home/igna/fintself"
EXPORT_DIR="$BASE_DIR/exports"
VENV_BIN="/home/igna/fintself-venv/bin"
SCRAPER_BIN="$VENV_BIN/fintself"
XVFB_BIN="/usr/bin/xvfb-run"
CHROME_PROFILE_DIR="/home/igna/.config/google-chrome-fintself"

# Best-effort cleanup of lingering Chrome profile holders before launch
if command -v pkill >/dev/null 2>&1; then
    pkill -f google-chrome-fintself 2>/dev/null || true
    # Wait briefly for processes to exit to avoid profile lock races
    for _ in $(seq 1 10); do
        if ! pgrep -f google-chrome-fintself >/dev/null 2>&1; then
            break
        fi
        sleep 0.5
    done
fi

# Clear stale Chrome singleton lock files that may prevent new sessions
if [ -d "$CHROME_PROFILE_DIR" ]; then
    rm -f "$CHROME_PROFILE_DIR"/Singleton{Lock,Cookie,Socket} 2>/dev/null || true
fi

mkdir -p "$EXPORT_DIR"

timestamp=$(date -u +"%Y%m%dT%H%M%SZ")
output_file="$EXPORT_DIR/santander-$timestamp.json"

"$XVFB_BIN" -a "$SCRAPER_BIN" scrape cl_santander \
    --output-file "$output_file" \
    --no-headless

ln -sf "$output_file" "$EXPORT_DIR/santander-latest.json"
ln -sf "$output_file" "$BASE_DIR/santander.json"

find "$EXPORT_DIR" -type f -name 'santander-*.json' -mtime +15 -delete
