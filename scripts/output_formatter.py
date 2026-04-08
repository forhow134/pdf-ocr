import json
from pydantic import BaseModel


class PageResult(BaseModel):
    page_number: int
    content_markdown: str
    tables: list[dict] | None = None
    confidence: float
    engine: str
    fallback_reasons: list[str]


class OCRResult(BaseModel):
    source_file: str
    total_pages: int
    output_format: str
    pages: list[PageResult]
    processing_time_seconds: float


def format_as_markdown(result: OCRResult) -> str:
    parts = []
    for page in result.pages:
        parts.append(page.content_markdown)

    return "\n\n---\n\n".join(parts)


def format_as_json(result: OCRResult) -> str:
    return result.model_dump_json(indent=2)


def format_output(result: OCRResult, output_format: str = "markdown") -> str:
    if output_format == "json":
        return format_as_json(result)
    return format_as_markdown(result)
