"""
CLI utility to count pages in a PDF file using PyMuPDF.
Used by verification.md automated checks for Phase 1.
Usage: python -m backend.ingest.count_pages <pdf_path>
"""

import sys
import pymupdf

def main():
    if len(sys.argv) < 2:
        print("Usage: python -m backend.ingest.count_pages <pdf_path>", file=sys.stderr)
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    try:
        doc = pymupdf.open(pdf_path)
        count = len(doc)
        doc.close()
        print(count)
    except Exception as e:
        print(f"Error opening {pdf_path}: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
