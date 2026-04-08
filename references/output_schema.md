# PDF OCR Output Schema

## JSON Output Structure

When using `--format json`, the output follows this schema:

```json
{
  "source_file": "document.pdf",
  "total_pages": 3,
  "output_format": "json",
  "pages": [
    {
      "page_number": 1,
      "content_markdown": "# Contract Title\n\nParty A: ...\n\n| Item | Qty | Price |\n|------|-----|-------|\n| ... | ... | ... |",
      "tables": null,
      "confidence": 0.85,
      "engine": "glm-ocr",
      "fallback_reasons": []
    },
    {
      "page_number": 2,
      "content_markdown": "## Terms and Conditions\n\n1. ...",
      "tables": null,
      "confidence": 0.42,
      "engine": "gpt-5.4",
      "fallback_reasons": ["text too short (38 chars)", "no markdown structure detected"]
    }
  ],
  "processing_time_seconds": 12.34
}
```

## Field Reference

### OCRResult (top level)

| Field | Type | Description |
|-------|------|-------------|
| `source_file` | string | Original PDF filename |
| `total_pages` | int | Number of pages processed |
| `output_format` | string | `"markdown"` or `"json"` |
| `pages` | array | Per-page OCR results |
| `processing_time_seconds` | float | Total pipeline execution time |

### PageResult (per page)

| Field | Type | Description |
|-------|------|-------------|
| `page_number` | int | 1-based page index |
| `content_markdown` | string | OCR text in Markdown format |
| `tables` | array\|null | Extracted table structures (if detected) |
| `confidence` | float | Confidence score (0.0 – 1.0) |
| `engine` | string | OCR engine used: `"glm-ocr"` or `"gpt-5.4"` |
| `fallback_reasons` | array | List of reasons if confidence was low |

## Confidence Score Breakdown

| Dimension | Weight | Low-confidence trigger |
|-----------|--------|----------------------|
| Text length | 0.30 | < 50 characters |
| Garbled chars | 0.25 | > 20% non-CJK/ASCII |
| Text density | 0.20 | Low chars-to-area ratio |
| Structure | 0.15 | No Markdown markers found |
| Language consistency | 0.10 | No recognizable language |
