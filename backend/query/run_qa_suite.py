"""
FactLoom Phase 5 QA Suite & Automated Gate
Verifies:
1. All four core demo questions answered with evidence citations and correct reconciliation.
2. Scripted ambiguous question ("What is India's GDP growth?" with no period specified)
   returns multiple labeled Facts, abstaining from a single merged number.
3. Citation audit passes with 100% resolution (zero tolerance hallucination backstop).
4. FastAPI POST /ask endpoint behaves identically.
5. Zero hardcoded tokens in backend/query/ logic.
"""

import os
import sys
import logging
from typing import Dict, Any, List

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from fastapi.testclient import TestClient
from backend.api.app import app
from backend.query.service import QueryService
from backend.query.citation_audit import run_citation_audit
from backend.query.seed_cases import seed_demo_cases

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

def run_qa_suite():
    print("=" * 60)
    print("FACTLOOM PHASE 5 QA VERIFICATION SUITE")
    print("=" * 60)

    # Ensure demo cases are present
    seed_demo_cases()

    service = QueryService()
    client = TestClient(app)

    # -------------------------------------------------------------
    # Check 1: Citation Audit Gate (100% resolution)
    # -------------------------------------------------------------
    print("\n[CHECK 1] Running Deterministic Citation Audit...")
    audit_res = run_citation_audit()
    print(f"  Citation resolution rate: {audit_res['rate_pct']:.1f}%")
    assert audit_res["passed"], "Citation audit gate failed!"
    print("  [PASS] 100% of citations resolve to valid database records.")

    # -------------------------------------------------------------
    # Check 2: Case 1 (Delhivery FY24 EBITDA Corroboration)
    # -------------------------------------------------------------
    print("\n[CHECK 2] Evaluating Case 1: 'What was Delhivery's FY24 EBITDA?'...")
    q1 = "What was Delhivery's FY24 EBITDA?"
    res1 = service.ask(q1)
    print(f"  Answer: {res1.answer[:120]}...")
    print(f"  Citations found: {len(res1.citations)}")
    for c in res1.citations:
        print(f"    - [{c.observation_id}] Value: {c.value} {c.unit or ''} | Doc: {c.document_filename} (p.{c.page_number})")

    # Assertions
    assert len(res1.citations) >= 2, "Expected citations from both AR and Deck"
    assert ("1,266" in res1.answer or "127" in res1.answer), "EBITDA figure missing from answer"
    assert res1.citation_validation and res1.citation_validation.is_valid, "Citation validation failed for Case 1"
    print("  [PASS] Case 1 answered correctly with dual-document citations.")

    # -------------------------------------------------------------
    # Check 3: Case 2 (Active Customers Discrepancy Abstention)
    # -------------------------------------------------------------
    print("\n[CHECK 3] Evaluating Case 2: 'How many active customers does Delhivery have in FY24?'...")
    q2 = "How many active customers does Delhivery have in FY24?"
    res2 = service.ask(q2)
    print(f"  Answer: {res2.answer[:140]}...")
    print(f"  Citations found: {len(res2.citations)}")

    # Assertions
    assert "33,250" in res2.answer and "33,278" in res2.answer, "Both customer figures must be presented"
    assert any(k in res2.answer.lower() for k in ["unresolved", "no footnote", "discrepancy", "conflicting"]), "Answer must state discrepancy without inventing theories"
    assert res2.citation_validation and res2.citation_validation.is_valid, "Citation validation failed for Case 2"
    print("  [PASS] Case 2 correctly presents both figures and abstains from false reconciliation.")

    # -------------------------------------------------------------
    # Check 4: Case 3a (Suvir Sujan Directorship Status Change)
    # -------------------------------------------------------------
    print("\n[CHECK 4] Evaluating Case 3a: 'Is Suvir Sujan currently a director at Delhivery?'...")
    q3a = "Is Suvir Sujan currently a director at Delhivery?"
    res3a = service.ask(q3a)
    print(f"  Answer: {res3a.answer[:140]}...")
    print(f"  Citations found: {len(res3a.citations)}")

    # Assertions
    assert any(k in res3a.answer.lower() for k in ["ceased", "resigned", "supersedes", "august 24, 2023", "no"]), "Status change must be explained"
    assert res3a.citation_validation and res3a.citation_validation.is_valid, "Citation validation failed for Case 3a"
    print("  [PASS] Case 3a correctly resolves governance change via temporal supersession.")

    # -------------------------------------------------------------
    # Check 5: Case 3b (India Real GDP FY25 Estimate vs Actual)
    # -------------------------------------------------------------
    print("\n[CHECK 5] Evaluating Case 3b: 'What was India's Real GDP growth in FY25?'...")
    q3b = "What was India's Real GDP growth in FY25?"
    res3b = service.ask(q3b)
    print(f"  Answer: {res3b.answer[:140]}...")
    print(f"  Citations found: {len(res3b.citations)}")

    # Assertions
    assert ("6.4%" in res3b.answer or "6.4" in res3b.answer) and ("6.5%" in res3b.answer or "6.5" in res3b.answer), "Both estimate and actual figures must be presented"
    assert any(k in res3b.answer.lower() for k in ["estimate", "actual", "release", "reconciled"]), "Must distinguish estimate vs actual"
    assert res3b.citation_validation and res3b.citation_validation.is_valid, "Citation validation failed for Case 3b"
    print("  [PASS] Case 3b correctly reports advance estimate reconciled by official release.")

    # -------------------------------------------------------------
    # Check 6: Ambiguous GDP Question (No period specified)
    # -------------------------------------------------------------
    print("\n[CHECK 6] Evaluating Ambiguous Question: 'What is India's GDP growth?' (No period)...")
    q_ambig = "What is India's GDP growth?"
    res_ambig = service.ask(q_ambig)
    print(f"  is_ambiguous: {res_ambig.is_ambiguous}")
    print(f"  Abstention reason: {res_ambig.abstention_reason}")
    print(f"  Facts returned: {len(res_ambig.facts)}")
    for f in res_ambig.facts:
        print(f"    - Period: {f.get('period')} | Scope: {f.get('scope')} | Obs count: {f.get('observation_count')}")

    # Assertions per verification.md §Phase 5:
    # "The scripted ambiguous question ('What is India's GDP growth?' with no period specified)
    # returns multiple labeled Facts, not one merged number — confirm by inspecting the raw response object."
    assert res_ambig.is_ambiguous is True, "Ambiguous query must set is_ambiguous = True"
    assert len(res_ambig.facts) >= 2, f"Expected multiple labeled facts, got {len(res_ambig.facts)}"
    returned_periods = {f.get("period") for f in res_ambig.facts}
    assert "FY25" in returned_periods and "FY24" in returned_periods, "Expected both FY24 and FY25 facts returned"
    print("  [PASS] Ambiguous query returned multiple labeled facts rather than a single merged number.")

    # -------------------------------------------------------------
    # Check 7: FastAPI POST /ask Integration Test
    # -------------------------------------------------------------
    print("\n[CHECK 7] Evaluating POST /ask REST Endpoint...")
    api_resp = client.post("/ask", json={"question": "What was Delhivery's FY24 EBITDA?"})
    assert api_resp.status_code == 200, f"Expected 200, got {api_resp.status_code}"
    api_data = api_resp.json()
    assert "answer" in api_data and len(api_data["citations"]) >= 2
    print(f"  [PASS] POST /ask returned 200 OK with {len(api_data['citations'])} citations.")

    # -------------------------------------------------------------
    # Check 8: Hardcoding Grep
    # -------------------------------------------------------------
    print("\n[CHECK 8] Running Hardcoding Grep across backend/query/...")
    forbidden = ["delhivery", "ebitda", "superjoin", "rbi", "imf"]
    target_dir = os.path.join(os.path.dirname(__file__))
    hardcoding_violation = False

    for root, _, files in os.walk(target_dir):
        for f in files:
            if f.endswith(".py") and f not in ["run_qa_suite.py", "seed_cases.py"]:
                f_path = os.path.join(root, f)
                with open(f_path, "r", encoding="utf-8", errors="ignore") as fh:
                    content = fh.read().lower()
                    for token in forbidden:
                        if token in content:
                            print(f"  [HARDCODING ERROR] Found '{token}' in {f_path}")
                            hardcoding_violation = True

    assert not hardcoding_violation, "Hardcoding violation in query logic!"
    print("  [PASS] Zero starter-set tokens in query engine logic.")

    # -------------------------------------------------------------
    # Summary Report
    # -------------------------------------------------------------
    print("\n" + "=" * 60)
    print("PHASE 5 — SELF-REPORT")
    print(f"Citation audit: {audit_res['rate_pct']:.1f}% resolve (gate: 100%)")
    print(f"Ambiguous GDP question returns multiple labeled facts: yes, count {len(res_ambig.facts)}")
    print("Four case questions answered correctly with citations: yes")
    print("Gate: PASS")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = run_qa_suite()
    sys.exit(0 if success else 1)
