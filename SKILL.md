---
name: pdf-ocr
description: >
  This skill should be used when tasks involve OCR recognition of PDF documents,
  especially scanned PDFs with stamps, seals, blurry text, or no extractable text layer.
  Supports converting PDF content to structured Markdown or JSON format using a hybrid
  approach: local GLM-OCR via Ollama first, with automatic GPT-5.4 fallback for
  low-confidence pages. Trigger keywords: OCR, PDF recognition, scanned document,
  stamp, seal, blurry text, document extraction, contract OCR, invoice OCR,
  pdf2markdown, pdf2json, document parsing, text extraction.
---

# PDF OCR Skill

Hybrid OCR pipeline for PDF documents. Uses local GLM-OCR (via Ollama) as the primary engine with automatic GPT-5.4 vision fallback for low-confidence results. Handles scanned documents, stamp-obscured text, and blurry content.

## Environment Setup

Run the setup script before first use:

```bash
cd <skill_dir>
bash scripts/setup_env.sh
```

Prerequisites:
- `poppler` — install via `brew install poppler` (provides `pdftoppm`)
- `ollama` — install from https://ollama.ai/download, then `ollama pull glm-ocr`
- `OPENAI_API_KEY` environment variable (required for LLM fallback, not needed with `--force-local`)

## Usage

Activate the skill's venv, then run the pipeline:

```bash
source <skill_dir>/.venv/bin/activate
python <skill_dir>/scripts/ocr_pipeline.py <pdf_path> [options]
```

### CLI Options

| Option | Default | Description |
|--------|---------|-------------|
| `--format markdown\|json` | `markdown` | Output format |
| `--output <path>` | stdout | Write output to file |
| `--threshold <0.0-1.0>` | `0.6` | Confidence threshold for LLM fallback |
| `--dpi <int>` | `300` | Image resolution (use 400 for blurry docs) |
| `--force-local` | off | Disable LLM fallback, local OCR only |
| `--max-fallback-pages <int>` | `10` | Max pages sent to LLM (cost control) |
| `--no-enhance` | off | Disable contrast/sharpness enhancement |
| `--stamp-mask` | off | Enable red stamp removal preprocessing |

### Examples

Basic Markdown output:
```bash
python scripts/ocr_pipeline.py contract.pdf
```

JSON output with stamp masking:
```bash
python scripts/ocr_pipeline.py contract.pdf --format json --stamp-mask --output result.json
```

Local-only mode (no API calls):
```bash
python scripts/ocr_pipeline.py contract.pdf --force-local
```

High-DPI for blurry scans:
```bash
python scripts/ocr_pipeline.py blurry.pdf --dpi 400 --stamp-mask
```

## Pipeline Architecture

```
PDF → pdf2image (poppler) → Image preprocessing → GLM-OCR (Ollama)
                                                       ↓
                                               Confidence check
                                              ↙              ↘
                                    >= threshold         < threshold
                                    Use local result     GPT-5.4 fallback
                                              ↘              ↙
                                          Format output (MD / JSON)
```

### Image Preprocessing (`--stamp-mask`)

When enabled, the preprocessor detects red stamp regions via HSV color analysis and fades them to reduce interference with text recognition. Combined with contrast/sharpness enhancement (enabled by default), this significantly improves OCR accuracy on stamped documents.

### Confidence Scoring

Each page is scored (0.0–1.0) based on:
- Text length (empty/short text = low confidence)
- Garbled character ratio (non-CJK/ASCII)
- Text density relative to image area
- Markdown structure presence (headings, tables, lists)
- Language consistency

Pages scoring below `--threshold` trigger the GPT-5.4 fallback, which receives both the image and the local OCR attempt as context for improved accuracy.

## Output Formats

- **Markdown**: Preserves document structure (headings, tables, paragraphs). Pages separated by `---`.
- **JSON**: Full structured output including per-page confidence scores, engine used, and fallback reasons. See `references/output_schema.md` for schema details.

## MCP Server Mode

This skill can also run as an MCP (Model Context Protocol) server, compatible with Verdent, OpenCode, OpenClaw, and any MCP client.

Start the server:
```bash
source <skill_dir>/.venv/bin/activate
python <skill_dir>/mcp_server.py
```

### MCP Tools Provided

- `ocr_pdf` — Full OCR pipeline. Parameters: `pdf_path`, `output_format`, `threshold`, `dpi`, `force_local`, `stamp_mask`, `enhance`, `max_fallback_pages`.
- `ocr_pdf_check` — Quick check: page count, file size, estimated time.

### Client Configuration

Add to your MCP config (e.g. `~/.verdent/mcp.json` or OpenCode equivalent):
```json
{
  "mcpServers": {
    "pdf-ocr": {
      "command": "<skill_dir>/.venv/bin/python",
      "args": ["<skill_dir>/mcp_server.py"],
      "env": {
        "OPENAI_API_KEY": "your-key-here"
      }
    }
  }
}
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `pdftoppm: command not found` | `brew install poppler` |
| Ollama connection refused | Start Ollama: `ollama serve` |
| `glm-ocr` model not found | `ollama pull glm-ocr` |
| LLM fallback fails | Check `OPENAI_API_KEY` is set, or use `--force-local` |
| Poor OCR on stamped docs | Add `--stamp-mask` flag |
| Blurry text not recognized | Increase DPI: `--dpi 400` |
