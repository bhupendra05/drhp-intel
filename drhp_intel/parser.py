"""PDF reader — wraps pdfplumber, falls back to pdfminer."""
from __future__ import annotations
from typing import Tuple


def read_pdf(path: str) -> Tuple[str, int]:
    """
    Extract full text and page count from a PDF file.
    Returns (text, page_count).
    Requires: pip install pdfplumber
    """
    try:
        import pdfplumber
        with pdfplumber.open(path) as pdf:
            pages = []
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    pages.append(t)
            return "\n\n".join(pages), len(pdf.pages)
    except ImportError:
        raise ImportError(
            "pdfplumber is required to read PDFs.\n"
            "Install it: pip install 'drhp-intel[pdf]'"
        )
    except Exception as e:
        raise ValueError(f"Could not read PDF '{path}': {e}")
