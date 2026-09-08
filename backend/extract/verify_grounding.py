"""
FactLoom Grounding Verification Tool
Automated verification tool for Phase 2 quantitative gate per verification.md.
Usage: python -m backend.extract.verify_grounding [--doc all]
"""

import os
import sys
import json
import argparse
from typing import List, Dict, Any, Optional

from backend.store.db import get_connection
from backend.ingest.parser import PDFParser, ParsedPage
from backend.extract.extractor import FactExtractor
from backend.extract.client import GroqClient

sys.stdout.reconfigure(encoding='utf-8')

def run_grounding_audit(candidates_with_page_text: List[Dict[str, Any]], extractor: Optional[FactExtractor] = None) -> Dict[str, Any]:
    """Check literal substring presence of quote_span in page_text."""
    total = len(candidates_with_page_text)
    if total == 0:
        return {"total": 0, "valid": 0, "percentage": 100.0}

    ext = extractor or FactExtractor()
    valid = 0
    failures = []

    for item in candidates_with_page_text:
        quote = item["quote_span"]
        page_text = item["page_text"]

        is_valid, _ = ext._verify_grounding(quote, page_text)
        if is_valid:
            valid += 1
        else:
            failures.append({
                "page": item.get("page_number"),
                "claim": item.get("claim_text"),
                "quote": quote
            })

    pct = (valid / total) * 100.0
    return {
        "total": total,
        "valid": valid,
        "percentage": pct,
        "failures": failures
    }

def verify_case1_raw_material(extracted_records: List[Dict[str, Any]]) -> bool:
    """
    Verify Case 1 raw material:
    Confirm that EBITDA (1,266.41 and 127) and Revenue (81,415.38 and 8,142)
    are present in the extraction records.
    """
    found_ebitda_ar = False
    found_ebitda_deck = False
    found_rev_ar = False
    found_rev_deck = False

    for rec in extracted_records:
        val = rec.get("value", "").replace(",", "")
        claim = rec.get("claim_text", "").lower()
        metric = rec.get("metric_mention", "").lower()
        quote = rec.get("quote_span", "").lower()

        combined = f"{val} {claim} {metric} {quote}"

        if "1266.41" in combined or "1,266.41" in combined:
            found_ebitda_ar = True
        if val == "127" or ("127" in combined and any(k in combined for k in ["ebitda", "cr", "income", "profit", "value"])):
            found_ebitda_deck = True
        if "81415.38" in combined or "81,415.38" in combined:
            found_rev_ar = True
        if "8142" in combined or "8,142" in combined or val == "8142" or val == "8,142":
            found_rev_deck = True

    print(f"Case 1 Raw Material Status:")
    print(f"  - AR EBITDA (1,266.41M): {found_ebitda_ar}")
    print(f"  - Deck EBITDA (127Cr):   {found_ebitda_deck}")
    print(f"  - AR Revenue (81,415.38M): {found_rev_ar}")
    print(f"  - Deck Revenue (8,142Cr):  {found_rev_deck}")

    return found_ebitda_ar and found_ebitda_deck and found_rev_ar and found_rev_deck

def main():
    parser = argparse.ArgumentParser(description="Verify extraction grounding and Case 1 raw material.")
    parser.add_argument("--doc", type=str, default="all", help="Document to verify or 'all'")
    parser.add_argument("--sample", type=int, default=10, help="Number of sample pages to run live extraction on")
    args = parser.parse_args()

    # If GROQ_API_KEY is not set or placeholder, inform user
    groq_key = os.environ.get("GROQ_API_KEY", "")
    if not groq_key or groq_key.startswith("your_groq"):
        print("ERROR: GROQ_API_KEY is required to run live extraction.", file=sys.stderr)
        print("Please configure GROQ_API_KEY in your .env file.", file=sys.stderr)
        sys.exit(1)

    print("GROQ_API_KEY found. Running extraction grounding verification...")
    # Target Case 1 specifically:
    # AR FY24 PDF p.36 (printed p.71)
    # Q4 Deck PDF p.17 (slide 16)
    pdf_parser = PDFParser()
    extractor = FactExtractor()

    ar_pdf = "starter-datasets/delhivery/02-delhivery-annual-report-fy24-excerpt.pdf"
    deck_pdf = "starter-datasets/delhivery/03-delhivery-q4-fy24-earnings-presentation.pdf"

    ar_pages = pdf_parser.parse(ar_pdf)
    deck_pages = pdf_parser.parse(deck_pdf)

    ar_p36 = next(p for p in ar_pages if p.page_number == 36)
    deck_p17 = next(p for p in deck_pages if p.page_number == 17)

    print("\nExtracting from AR Page 36 (MD&A printed p.71)...")
    ar_records = extractor.extract_from_page(ar_p36, doc_filename=os.path.basename(ar_pdf))
    print(f"Extracted {len(ar_records)} candidates from AR p.36.")

    print("\nExtracting from Deck Page 17 (Slide 16)...")
    deck_records = extractor.extract_from_page(deck_p17, doc_filename=os.path.basename(deck_pdf))
    print(f"Extracted {len(deck_records)} candidates from Deck p.17.")

    all_extracted = ar_records + deck_records

    # Prepare grounding audit inputs
    audit_items = []
    for r in ar_records:
        audit_items.append({**r, "page_text": ar_p36.full_text})
    for r in deck_records:
        audit_items.append({**r, "page_text": deck_p17.full_text})

    audit_res = run_grounding_audit(audit_items)
    print(f"\nGrounding Check Result: {audit_res['valid']}/{audit_res['total']} valid ({audit_res['percentage']:.2f}%) (Gate: >= 98%)")

    case1_pass = verify_case1_raw_material(all_extracted)
    print(f"Case 1 Raw Material Found: {case1_pass}")

    if audit_res['percentage'] >= 98.0 and case1_pass:
        print("\nPHASE 2 EXTRACTION VERIFICATION: PASS")
        sys.exit(0)
    else:
        print("\nPHASE 2 EXTRACTION VERIFICATION: FAIL", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
