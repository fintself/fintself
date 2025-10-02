#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="/home/igna/fintself"
EXPORT_DIR="$BASE_DIR/exports"
VENV_BIN="/home/igna/fintself-venv/bin"
SCRAPER_BIN="$VENV_BIN/fintself"
XVFB_BIN="/usr/bin/xvfb-run"
XVFB_ARGS=(-a -s "-screen 0 1920x1080x24")
CHROME_PROFILE_DIR="/home/igna/.config/google-chrome-fintself"

ENV_FILE="$BASE_DIR/.env"
if [ -f "$ENV_FILE" ]; then
    headless_override="${SCRAPER_HEADLESS_MODE:-}"
    headless_override_set="${SCRAPER_HEADLESS_MODE+x}"
    # shellcheck disable=SC1090  # .env provides runtime configuration variables
    set -a
    source "$ENV_FILE"
    set +a
    if [ "$headless_override_set" = "x" ]; then
        SCRAPER_HEADLESS_MODE="$headless_override"
        export SCRAPER_HEADLESS_MODE
    fi
fi

is_truthy() {
    case "${1:-}" in
        [Tt][Rr][Uu][Ee]|[Yy][Ee][Ss]|1|[Yy]|[Oo][Nn])
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

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

scraper_args=("$SCRAPER_BIN" scrape cl_santander --output-file "$output_file")

debug_enabled=false
if is_truthy "${DEBUG:-false}"; then
    debug_enabled=true
fi

headless_effective=true
if [ "$debug_enabled" = true ] || ! is_truthy "${SCRAPER_HEADLESS_MODE:-true}"; then
    headless_effective=false
fi

if [ "$headless_effective" = true ]; then
    scraper_args+=(--headless)
    "${scraper_args[@]}"
else
    scraper_args+=(--no-headless)
    "$XVFB_BIN" "${XVFB_ARGS[@]}" "${scraper_args[@]}"
fi

ln -sf "$output_file" "$EXPORT_DIR/santander-latest.json"
ln -sf "$output_file" "$BASE_DIR/santander.json"

find "$EXPORT_DIR" -type f -name 'santander-*.json' -mtime +15 -delete
