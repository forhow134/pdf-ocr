# pdf-ocr

PDF document OCR recognition tool, supporting scanned documents, stamps/seal occlusion, blurry text, and other challenging scenarios.

Uses a hybrid architecture: local GLM-OCR (Ollama) for primary recognition, with automatic fallback to GPT-5.4 Vision for low-confidence results. Outputs Markdown or JSON.

## Architecture Flow

```
PDF File
  ↓
PDF → Image (pdf2image + poppler, DPI=300)
  ↓
Image Preprocessing (contrast enhancement / sharpening / optional red stamp masking)
  ↓
Local GLM-OCR Recognition (Ollama HTTP API)
  ↓
Confidence Evaluation (5-dimensional weighted scoring)
  ↓
>= Threshold → Use local result
< Threshold  → GPT-5.4 Vision fallback
  ↓
Formatted Output (Markdown / JSON)
```

## Requirements

- macOS / Linux
- Python 3.10+
- [poppler](https://poppler.freedesktop.org/) — PDF to image conversion
- [Ollama](https://ollama.ai) — Local GLM-OCR model execution
- `OPENAI_API_KEY` environment variable (required for LLM fallback; optional for local-only mode)

## Quick Start

### 1. Install Dependencies

```bash
cd pdf-ocr
bash scripts/setup_env.sh
```

This script will:
- Check if `poppler` and `ollama` are installed
- Create Python venv and install dependencies
- Pull the `glm-ocr` model to Ollama

### 2. Start Ollama Service

```bash
ollama serve
```

### 3. Run OCR

```bash
# Using start.sh (recommended, auto-activates venv)
./start.sh your_document.pdf

# Or manually activate venv and call directly
source .venv/bin/activate
python scripts/ocr_pipeline.py your_document.pdf
```

## Usage Examples

```bash
# Basic usage — output Markdown to terminal
./start.sh contract.pdf

# JSON format output to file
./start.sh contract.pdf --format json --output result.json

# Enable red stamp masking (for seal-occluded documents)
./start.sh contract.pdf --stamp-mask

# High DPI for blurry documents
./start.sh contract.pdf --dpi 400 --stamp-mask

# Local-only mode (no OpenAI API calls)
./start.sh contract.pdf --force-local

# Combined usage
./start.sh invoice.pdf --format json --stamp-mask --dpi 400 --output invoice.json
```

## CLI Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `<pdf_path>` | (required) | Path to PDF file |
| `--format` | `markdown` | Output format: `markdown` or `json` |
| `--output` | stdout | Output file path |
| `--threshold` | `0.6` | Confidence threshold; triggers LLM fallback if below |
| `--dpi` | `300` | PDF to image resolution; use 400 for blurry documents |
| `--force-local` | off | Disable LLM fallback; use local OCR only |
| `--max-fallback-pages` | `10` | Maximum pages allowed for LLM calls (cost control) |
| `--no-enhance` | off | Disable image enhancement preprocessing |
| `--stamp-mask` | off | Enable red stamp masking/dimming |

## Output Formats

### Markdown

Preserves original document structure (headings, tables, paragraphs). Multiple pages separated by `---`.

### JSON

Contains complete metadata:

```json
{
  "source_file": "contract.pdf",
  "total_pages": 1,
  "output_format": "json",
  "pages": [
    {
      "page_number": 1,
      "content_markdown": "# Purchase Contract ...",
      "confidence": 0.82,
      "engine": "glm-ocr",
      "fallback_reasons": []
    }
  ],
  "processing_time_seconds": 5.67
}
```

See [references/output_schema.md](references/output_schema.md) for the complete schema.

## Confidence Evaluation

| Dimension | Weight | Low Score Trigger |
|-----------|--------|-------------------|
| Text Length | 0.30 | < 50 characters |
| Garbled Text Ratio | 0.25 | Non-CJK/ASCII > 20% |
| Text Density | 0.20 | Characters/image area too low |
| Structure Completeness | 0.15 | No Markdown markers |
| Language Consistency | 0.10 | No recognizable language characters |

## Project Structure

```
pdf-ocr/
├── SKILL.md                 # Verdent/OpenCode Skill metadata
├── README.md                # This document
├── README_CN.md             # Chinese version
├── mcp_server.py            # MCP Server (Verdent/OpenCode/OpenClaw compatible)
├── start.sh                 # One-click launch script (CLI mode)
├── scripts/
│   ├── requirements.txt     # Python dependencies (includes MCP SDK)
│   ├── setup_env.sh         # Environment initialization
│   ├── ocr_pipeline.py      # Main entry CLI
│   ├── pdf_to_images.py     # PDF → PNG
│   ├── preprocess.py        # Image enhancement + red stamp masking
│   ├── local_ocr.py         # GLM-OCR (Ollama API)
│   ├── confidence.py        # Confidence evaluation
│   ├── llm_fallback.py      # GPT-5.4 Vision fallback
│   └── output_formatter.py  # Markdown/JSON formatting
└── references/
    └── output_schema.md     # JSON output schema
```

## Using as Verdent Skill

Copy the `pdf-ocr/` directory to `~/.verdent/skills/pdf-ocr/` and Verdent will automatically recognize and use it.

## Using as MCP Server (Recommended)

MCP Server mode is compatible with **Verdent, OpenCode, OpenClaw**, and all clients supporting the MCP protocol.

### Exposed Tools

| Tool Name | Function | Main Parameters |
|-----------|----------|-----------------|
| `ocr_pdf` | Complete OCR pipeline | `pdf_path`, `output_format`, `threshold`, `dpi`, `force_local`, `stamp_mask` |
| `ocr_pdf_check` | Quick PDF info check | `pdf_path` |

### Configuration

Add the following to your client's MCP configuration file:

**Verdent** (`~/.verdent/mcp.json`):
```json
{
  "mcpServers": {
    "pdf-ocr": {
      "command": "/path/to/pdf-ocr/.venv/bin/python",
      "args": ["/path/to/pdf-ocr/mcp_server.py"],
      "env": {
        "OPENAI_API_KEY": "your-key-here"
      }
    }
  }
}
```

**OpenCode** (`~/.config/opencode/config.json` or project `.opencode/config.json`):
```json
{
  "mcpServers": {
    "pdf-ocr": {
      "command": "/path/to/pdf-ocr/.venv/bin/python",
      "args": ["/path/to/pdf-ocr/mcp_server.py"],
      "env": {
        "OPENAI_API_KEY": "your-key-here"
      }
    }
  }
}
```

**OpenClaw** (`~/.openclaw/mcp.json` or project config):
```json
{
  "mcpServers": {
    "pdf-ocr": {
      "command": "/path/to/pdf-ocr/.venv/bin/python",
      "args": ["/path/to/pdf-ocr/mcp_server.py"],
      "env": {
        "OPENAI_API_KEY": "your-key-here"
      }
    }
  }
}
```

> Replace `/path/to/pdf-ocr` with the actual absolute path to your `pdf-ocr/` directory.
> `OPENAI_API_KEY` can be omitted in local-only mode (set `force_local=true` in tool parameters).

### Testing MCP Server Manually

```bash
# Start MCP development inspector
cd pdf-ocr
source .venv/bin/activate
mcp dev mcp_server.py
```

## License

Core dependencies are under Apache-2.0 / MIT licenses, no GPL distribution risks.
