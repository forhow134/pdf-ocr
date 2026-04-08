#!/usr/bin/env python3
"""PDF OCR MCP Server — exposes OCR pipeline as MCP tools for Verdent/OpenCode/OpenClaw."""

import os
import sys
import shutil
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "scripts"))

from mcp.server.fastmcp import Context, FastMCP

from pdf_to_images import pdf_to_images
from preprocess import preprocess_page
from local_ocr import ocr_page
from confidence import evaluate_confidence
from llm_fallback import fallback_ocr
from output_formatter import OCRResult, PageResult, format_output
from PIL import Image

mcp = FastMCP(
    name="pdf-ocr",
    instructions=(
        "PDF OCR tool for scanned documents. Handles stamps, seals, blurry text. "
        "Uses local GLM-OCR via Ollama with GPT-5.4 fallback for low-confidence pages."
    ),
)


@mcp.tool()
async def ocr_pdf(
    pdf_path: str,
    output_format: str = "markdown",
    threshold: float = 0.6,
    dpi: int = 300,
    force_local: bool = False,
    stamp_mask: bool = False,
    enhance: bool = True,
    max_fallback_pages: int = 10,
    ctx: Context = None,
) -> str:
    """Perform OCR on a PDF file and return the extracted text.

    Args:
        pdf_path: Absolute path to the PDF file.
        output_format: Output format, "markdown" or "json".
        threshold: Confidence threshold (0.0-1.0) for LLM fallback. Default 0.6.
        dpi: Image DPI for conversion. Use 400 for blurry documents. Default 300.
        force_local: If true, only use local OCR (no OpenAI API calls).
        stamp_mask: If true, enable red stamp/seal removal preprocessing.
        enhance: If true, enhance image contrast and sharpness. Default true.
        max_fallback_pages: Max pages to send to LLM fallback. Default 10.
    """
    pdf_path = os.path.abspath(pdf_path)
    if not os.path.isfile(pdf_path):
        return f"Error: PDF not found: {pdf_path}"

    tmp_dir = tempfile.mkdtemp(prefix="pdf_ocr_mcp_")
    try:
        start_time = time.time()

        if ctx:
            await ctx.info(f"Converting PDF to images (DPI={dpi})...")
        image_paths = pdf_to_images(pdf_path, dpi=dpi, output_dir=tmp_dir)
        total_pages = len(image_paths)

        if ctx:
            await ctx.info(f"{total_pages} page(s) extracted.")

        pages: list[PageResult] = []
        fallback_count = 0

        for i, img_path in enumerate(image_paths):
            page_num = i + 1
            if ctx:
                await ctx.report_progress(progress=i, total=total_pages)
                await ctx.info(f"Processing page {page_num}/{total_pages}...")

            img = Image.open(img_path)
            img_w, img_h = img.size

            variants = preprocess_page(
                img_path,
                enhance=enhance,
                stamp_mask=stamp_mask,
                output_dir=tmp_dir,
            )

            ocr_result = ocr_page(variants)
            local_text = ocr_result["text"]
            engine = ocr_result["engine"]

            conf = evaluate_confidence(local_text, image_width=img_w, image_height=img_h)
            score = conf["score"]
            reasons = conf["reasons"]

            final_text = local_text

            if score < threshold and not force_local:
                if fallback_count < max_fallback_pages:
                    if ctx:
                        await ctx.info(f"Page {page_num}: confidence {score:.2f} < {threshold}, using GPT-5.4 fallback...")
                    try:
                        fallback_text = fallback_ocr(
                            img_path,
                            local_ocr_text=local_text,
                            output_format=output_format,
                        )
                        final_text = fallback_text
                        engine = "gpt-5.4"
                        fallback_count += 1
                    except Exception as e:
                        if ctx:
                            await ctx.info(f"LLM fallback failed: {e}")
                else:
                    if ctx:
                        await ctx.info(f"Max fallback pages reached, using local result.")

            pages.append(PageResult(
                page_number=page_num,
                content_markdown=final_text,
                confidence=score,
                engine=engine,
                fallback_reasons=reasons,
            ))

        elapsed = round(time.time() - start_time, 2)
        result = OCRResult(
            source_file=os.path.basename(pdf_path),
            total_pages=total_pages,
            output_format=output_format,
            pages=pages,
            processing_time_seconds=elapsed,
        )

        if ctx:
            await ctx.report_progress(progress=total_pages, total=total_pages)
            await ctx.info(f"Done in {elapsed}s ({total_pages} pages, {fallback_count} fallback calls)")

        return format_output(result, output_format)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@mcp.tool()
async def ocr_pdf_check(pdf_path: str) -> str:
    """Check if a PDF can be processed and return basic info (page count, has text layer, file size).

    Args:
        pdf_path: Absolute path to the PDF file.
    """
    pdf_path = os.path.abspath(pdf_path)
    if not os.path.isfile(pdf_path):
        return f"Error: PDF not found: {pdf_path}"

    file_size = os.path.getsize(pdf_path)
    size_mb = round(file_size / 1024 / 1024, 2)

    tmp_dir = tempfile.mkdtemp(prefix="pdf_ocr_check_")
    try:
        images = pdf_to_images(pdf_path, dpi=72, output_dir=tmp_dir)
        page_count = len(images)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return (
        f"PDF: {os.path.basename(pdf_path)}\n"
        f"Pages: {page_count}\n"
        f"Size: {size_mb} MB\n"
        f"Estimated OCR time: ~{page_count * 90}s (local only) or ~{page_count * 30}s (with LLM fallback)\n"
        f"Ready for OCR: Yes"
    )


if __name__ == "__main__":
    mcp.run()
