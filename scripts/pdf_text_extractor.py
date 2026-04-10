#!/usr/bin/env python3
"""PDF text extractor - detect and extract text from text-based PDFs."""

import pdfplumber
from typing import Optional


def extract_text_from_pdf(pdf_path: str, min_chars_per_page: int = 50) -> dict[int, Optional[str]]:
    """
    Extract text from PDF page by page.
    
    Args:
        pdf_path: Path to PDF file
        min_chars_per_page: Minimum characters to consider a page as text-based
    
    Returns:
        Dict mapping page_number (1-indexed) to extracted text or None if page is image-based
    """
    result: dict[int, Optional[str]] = {}
    
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text()
            
            if text and len(text.strip()) >= min_chars_per_page:
                result[i] = text.strip()
            else:
                result[i] = None
    
    return result


def is_text_based_pdf(pdf_path: str, min_chars_per_page: int = 50, threshold_ratio: float = 0.5) -> bool:
    """
    Detect if PDF is text-based (vs image/scanned).
    
    Args:
        pdf_path: Path to PDF file
        min_chars_per_page: Minimum characters to consider a page as text-based
        threshold_ratio: Ratio of text-based pages to consider whole PDF as text-based
    
    Returns:
        True if PDF is predominantly text-based
    """
    pages_text = extract_text_from_pdf(pdf_path, min_chars_per_page)
    
    if not pages_text:
        return False
    
    text_pages = sum(1 for text in pages_text.values() if text is not None)
    total_pages = len(pages_text)
    
    ratio = text_pages / total_pages if total_pages > 0 else 0
    return ratio >= threshold_ratio


def get_pdf_page_count(pdf_path: str) -> int:
    """Get total page count of PDF."""
    with pdfplumber.open(pdf_path) as pdf:
        return len(pdf.pages)
