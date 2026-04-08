#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
SCRIPTS_DIR="$SCRIPT_DIR/scripts"

if [ ! -d "$VENV_DIR" ]; then
    echo "Virtual environment not found. Running setup first..."
    bash "$SCRIPTS_DIR/setup_env.sh"
fi

source "$VENV_DIR/bin/activate"

if [ $# -eq 0 ]; then
    echo "Usage: ./start.sh <pdf_path> [options]"
    echo ""
    echo "Options:"
    echo "  --format markdown|json   Output format (default: markdown)"
    echo "  --output <path>          Write output to file (default: stdout)"
    echo "  --threshold <0.0-1.0>    Confidence threshold (default: 0.6)"
    echo "  --dpi <int>              Image DPI (default: 300)"
    echo "  --force-local            Local OCR only, no GPT-5.4 fallback"
    echo "  --max-fallback-pages N   Max pages for LLM fallback (default: 10)"
    echo "  --no-enhance             Disable image enhancement"
    echo "  --stamp-mask             Enable red stamp removal"
    echo ""
    echo "Examples:"
    echo "  ./start.sh contract.pdf"
    echo "  ./start.sh contract.pdf --format json --stamp-mask -o result.json"
    echo "  ./start.sh contract.pdf --force-local --dpi 400"
    exit 0
fi

python3 "$SCRIPTS_DIR/ocr_pipeline.py" "$@"
