#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
VENV_DIR="$SKILL_DIR/.venv"

echo "=== pdf-ocr Skill Environment Setup ==="

errors=0

if ! command -v pdftoppm &>/dev/null; then
    echo "[MISSING] pdftoppm not found. Install with: brew install poppler"
    errors=$((errors + 1))
else
    echo "[OK] pdftoppm (poppler)"
fi

if ! command -v ollama &>/dev/null; then
    echo "[MISSING] ollama not found. Install from: https://ollama.ai/download"
    errors=$((errors + 1))
else
    echo "[OK] ollama"
fi

if [ $errors -gt 0 ]; then
    echo ""
    echo "Please install the missing dependencies above and re-run this script."
    exit 1
fi

echo ""
echo "--- Creating Python venv ---"
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    echo "Created venv at $VENV_DIR"
else
    echo "Venv already exists at $VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

echo ""
echo "--- Installing Python dependencies ---"
pip install --upgrade pip -q
pip install -r "$SCRIPT_DIR/requirements.txt" -q
echo "Python dependencies installed."

echo ""
echo "--- Pulling GLM-OCR model ---"
if ollama list 2>/dev/null | grep -q "glm-ocr"; then
    echo "glm-ocr model already available."
else
    echo "Pulling glm-ocr model (this may take a while)..."
    ollama pull glm-ocr
fi

echo ""
echo "--- Verification ---"

python3 -c "import pdf2image, PIL, openai, requests, pydantic; print('[OK] All Python packages imported successfully')"

if curl -s http://localhost:11434/api/tags &>/dev/null; then
    echo "[OK] Ollama service is running"
else
    echo "[WARN] Ollama service not reachable at localhost:11434. Start it with: ollama serve"
fi

if [ -n "${OPENAI_API_KEY:-}" ]; then
    echo "[OK] OPENAI_API_KEY is set"
else
    echo "[WARN] OPENAI_API_KEY not set. LLM fallback will not work without it."
fi

echo ""
echo "=== Setup complete ==="
