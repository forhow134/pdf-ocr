#!/usr/bin/env python3
import argparse
import os
import sys
import time
import shutil
import tempfile

from pdf_to_images import pdf_to_images
from preprocess import preprocess_page
from local_ocr import ocr_page
from confidence import evaluate_confidence
from llm_fallback import fallback_ocr
from output_formatter import OCRResult, PageResult, format_output
from PIL import Image


def parse_args():
    parser = argparse.ArgumentParser(description="PDF OCR Pipeline — hybrid local + LLM fallback")
    parser.add_argument("pdf_path", help="Path to the PDF file")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown", help="Output format (default: markdown)")
    parser.add_argument("--output", default=None, help="Output file path (default: stdout)")
    parser.add_argument("--threshold", type=float, default=0.6, help="Confidence threshold for LLM fallback (default: 0.6)")
    parser.add_argument("--dpi", type=int, default=300, help="DPI for PDF to image conversion (default: 300)")
    parser.add_argument("--force-local", action="store_true", help="Force local OCR only, no LLM fallback")
    parser.add_argument("--max-fallback-pages", type=int, default=10, help="Max pages to send to LLM fallback (default: 10)")
    parser.add_argument("--no-enhance", action="store_true", help="Disable image enhancement preprocessing")
    parser.add_argument("--stamp-mask", action="store_true", help="Enable red stamp masking")
    return parser.parse_args()


def main():
    args = parse_args()
    start_time = time.time()

    pdf_path = os.path.abspath(args.pdf_path)
    if not os.path.isfile(pdf_path):
        print(f"Error: PDF not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    tmp_dir = tempfile.mkdtemp(prefix="pdf_ocr_")
    try:
        print(f"[1/5] Converting PDF to images (DPI={args.dpi})...", file=sys.stderr)
        image_paths = pdf_to_images(pdf_path, dpi=args.dpi, output_dir=tmp_dir)
        print(f"       {len(image_paths)} page(s) extracted.", file=sys.stderr)

        pages: list[PageResult] = []
        fallback_count = 0

        for i, img_path in enumerate(image_paths):
            page_num = i + 1
            print(f"[2/5] Processing page {page_num}/{len(image_paths)}...", file=sys.stderr)

            img = Image.open(img_path)
            img_w, img_h = img.size

            print(f"  [3/5] Preprocessing...", file=sys.stderr)
            variants = preprocess_page(
                img_path,
                enhance=not args.no_enhance,
                stamp_mask=args.stamp_mask,
                output_dir=tmp_dir,
            )

            print(f"  [3/5] Running local OCR (GLM-OCR)...", file=sys.stderr)
            ocr_result = ocr_page(variants)
            local_text = ocr_result["text"]
            engine = ocr_result["engine"]

            print(f"  [4/5] Evaluating confidence...", file=sys.stderr)
            conf = evaluate_confidence(local_text, image_width=img_w, image_height=img_h)
            score = conf["score"]
            reasons = conf["reasons"]
            print(f"       Confidence: {score} | Reasons: {reasons}", file=sys.stderr)

            final_text = local_text

            if score < args.threshold and not args.force_local:
                if fallback_count < args.max_fallback_pages:
                    print(f"  [5/5] Confidence below threshold ({args.threshold}), calling GPT-5.4 fallback...", file=sys.stderr)
                    try:
                        fallback_text = fallback_ocr(
                            img_path,
                            local_ocr_text=local_text,
                            output_format=args.format,
                        )
                        final_text = fallback_text
                        engine = "gpt-5.4"
                        fallback_count += 1
                    except Exception as e:
                        print(f"       LLM fallback failed: {e}", file=sys.stderr)
                else:
                    print(f"       Max fallback pages ({args.max_fallback_pages}) reached, using local result.", file=sys.stderr)

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
            total_pages=len(pages),
            output_format=args.format,
            pages=pages,
            processing_time_seconds=elapsed,
        )

        output_text = format_output(result, args.format)

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output_text)
            print(f"\nOutput written to: {args.output}", file=sys.stderr)
        else:
            print(output_text)

        print(f"\nDone in {elapsed}s ({len(pages)} pages, {fallback_count} fallback calls)", file=sys.stderr)

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
