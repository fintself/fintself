#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="/home/igna/fintself"
EXPORT_DIR="$BASE_DIR/exports"
VENV_BIN="/home/igna/fintself-venv/bin"
SCRAPER_BIN="$VENV_BIN/fintself"
XVFB_BIN="/usr/bin/xvfb-run"

mkdir -p "$EXPORT_DIR"

timestamp=$(date -u +"%Y%m%dT%H%M%SZ")
output_file="$EXPORT_DIR/santander-$timestamp.json"

"$XVFB_BIN" -a "$SCRAPER_BIN" scrape cl_santander \
    --output-file "$output_file" \
    --no-headless

ln -sf "$output_file" "$EXPORT_DIR/santander-latest.json"
ln -sf "$output_file" "$BASE_DIR/santander.json"

find "$EXPORT_DIR" -type f -name 'santander-*.json' -mtime +15 -delete
