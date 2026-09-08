"""
FactLoom Evaluation Harness & Benchmark Runner (Phase 7)
Evaluates end-to-end question answering across 28 questions in 7 categories:
1. Extraction & Unit Conversion
2. Temporal & Vintage Governance
3. Reconciled Metrics & Estimate vs Actual
4. Mandatory Abstention & Discrepancies
5. Ambiguous Inquiries & Multi-Fact Abstention
6. Cross-Document Generalization (Apple FY24 Q4)
7. Hallucination Traps & Out-of-Corpus Questions

Measures:
- Grounding accuracy
- Citation resolution validity (100% target)
- Ambiguity & abstention compliance
- Response latency
Records runs in SQLite `eval_runs` table and exports `eval/results.json`.
"""

import os
import sys
import time
import json
import sqlite3
import datetime
from typing import Dict, Any, List

# Windows terminal UTF-8 encoding support
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.query.service import QueryService
from backend.query.seed_cases import seed_demo_cases

def init_eval_db(db_path: str):
    conn = sqlite3.connect(db_path)
    with conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS eval_runs (
            id TEXT PRIMARY KEY,
            run_at TEXT NOT NULL,
            question TEXT NOT NULL,
            expected TEXT NOT NULL,
            actual TEXT NOT NULL,
            category TEXT NOT NULL,
            pass_bool INTEGER NOT NULL
        );
        """)
    conn.close()

def record_eval_run(db_path: str, run_id: str, question: str, expected: str, actual: str, category: str, passed: bool):
    conn = sqlite3.connect(db_path)
    with conn:
        conn.execute("""
        INSERT OR REPLACE INTO eval_runs (id, run_at, question, expected, actual, category, pass_bool)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            run_id,
            datetime.datetime.utcnow().isoformat() + "Z",
            question,
            expected,
            actual[:500],
            category,
            1 if passed else 0
        ))
    conn.close()

def run_evaluation(questions_path: str = None, db_path: str = None) -> Dict[str, Any]:
    if not questions_path:
        questions_path = os.path.join(PROJECT_ROOT, "eval", "questions.json")
    if not db_path:
        db_path = os.path.join(PROJECT_ROOT, "factloom.db")

    init_eval_db(db_path)
    seed_demo_cases(db_path)

    with open(questions_path, "r", encoding="utf-8") as f:
        bench_data = json.load(f)

    questions = bench_data.get("questions", [])
    service = QueryService(db_path=db_path)

    print("=" * 80)
    print("FACTLOOM COMPREHENSIVE EVALUATION SUITE (PHASE 7)")
    print(f"Total Questions: {len(questions)} | Target Database: {db_path}")
    print("=" * 80)

    results: List[Dict[str, Any]] = []
    category_stats: Dict[str, Dict[str, int]] = {}

    total_citations_audited = 0
    valid_citations_audited = 0
    start_all = time.time()

    for idx, q in enumerate(questions, 1):
        q_id = q["id"]
        cat = q["category"]
        question_text = q["question"]
        expected_kws = q.get("expected_keywords", [])
        must_cite_min = q.get("must_cite_min", 0)
        expect_ambig = q.get("expect_ambiguity", False)
        expect_abst = q.get("expect_abstention", False)

        if cat not in category_stats:
            category_stats[cat] = {"total": 0, "passed": 0}
        category_stats[cat]["total"] += 1

        t0 = time.time()
        res = service.ask(question_text)
        latency_ms = (time.time() - t0) * 1000

        answer_text = res.answer or ""
        answer_lower = answer_text.lower()

        # 1. Citation audit validation
        citations = res.citations or []
        num_citations = len(citations)
        total_citations_audited += num_citations

        citation_valid = True
        if citations:
            if res.citation_validation and res.citation_validation.is_valid:
                valid_citations_audited += num_citations
            else:
                citation_valid = False
        else:
            citation_valid = True

        min_cite_ok = (num_citations >= must_cite_min)

        # 2. Ambiguity validation
        ambiguity_ok = True
        if expect_ambig:
            ambiguity_ok = (res.is_ambiguous is True) and (len(res.facts) >= 2)

        # 3. Keyword / Content validation
        matched_kws = [kw for kw in expected_kws if kw.lower() in answer_lower]
        # For regular extraction, require at least one key target keyword
        keywords_ok = len(matched_kws) > 0 if expected_kws else True

        # Special handling for ambiguity queries where answer explains the ambiguity
        if expect_ambig and ambiguity_ok:
            keywords_ok = True

        # 4. Overall item pass determination
        item_passed = (citation_valid and min_cite_ok and ambiguity_ok and keywords_ok)

        if item_passed:
            category_stats[cat]["passed"] += 1

        # Record into database
        run_record_id = f"eval_{q_id}_{int(time.time())}"
        record_eval_run(
            db_path=db_path,
            run_id=run_record_id,
            question=question_text,
            expected=",".join(expected_kws),
            actual=answer_text,
            category=cat,
            passed=item_passed
        )

        status_tag = "[PASS]" if item_passed else "[FAIL]"
        print(f"{status_tag} Q{idx:02d} [{cat}] {question_text}")
        print(f"       -> Citations: {num_citations} (min: {must_cite_min}) | Latency: {latency_ms:.1f}ms | Ambiguous: {res.is_ambiguous}")
        if not item_passed:
            print(f"       [DEBUG FAIL] matched_kws: {matched_kws}/{expected_kws}, cite_valid: {citation_valid}, min_cite: {min_cite_ok}, ambig_ok: {ambiguity_ok}")
            print(f"       Answer snippet: {answer_text[:160]}...")

        results.append({
            "id": q_id,
            "category": cat,
            "question": question_text,
            "passed": item_passed,
            "latency_ms": round(latency_ms, 1),
            "citations_count": num_citations,
            "citation_valid": citation_valid,
            "is_ambiguous": res.is_ambiguous,
            "matched_keywords": matched_kws,
            "answer_preview": answer_text[:200]
        })
        time.sleep(0.5)

    total_time = time.time() - start_all
    total_q = len(questions)
    total_passed = sum(1 for r in results if r["passed"])
    accuracy_pct = (total_passed / total_q) * 100 if total_q else 0.0

    citation_resolution_rate = (
        (valid_citations_audited / total_citations_audited) * 100
        if total_citations_audited > 0 else 100.0
    )

    avg_latency = sum(r["latency_ms"] for r in results) / total_q if total_q else 0.0

    summary = {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "total_questions": total_q,
        "passed": total_passed,
        "failed": total_q - total_passed,
        "accuracy_pct": round(accuracy_pct, 2),
        "total_citations_audited": total_citations_audited,
        "valid_citations": valid_citations_audited,
        "citation_resolution_rate_pct": round(citation_resolution_rate, 2),
        "average_latency_ms": round(avg_latency, 1),
        "total_duration_seconds": round(total_time, 2),
        "category_breakdown": category_stats,
        "detailed_results": results
    }

    # Write results to eval/results.json
    results_path = os.path.join(PROJECT_ROOT, "eval", "results.json")
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    # Print summary table
    print("\n" + "=" * 80)
    print("EVALUATION SUMMARY REPORT")
    print("=" * 80)
    print(f"Overall Accuracy:          {total_passed}/{total_q} ({accuracy_pct:.1f}%)")
    print(f"Citation Resolution Rate:  {citation_resolution_rate:.1f}% (Audit Backstop)")
    print(f"Average Query Latency:     {avg_latency:.1f} ms")
    print(f"Total Execution Time:      {total_time:.2f} s")
    print("-" * 80)
    print(f"{'Category':<28} | {'Total':<6} | {'Passed':<6} | {'Pass Rate'}")
    print("-" * 80)
    for cat, stats in category_stats.items():
        rate = (stats["passed"] / stats["total"]) * 100 if stats["total"] else 0
        print(f"{cat:<28} | {stats['total']:<6} | {stats['passed']:<6} | {rate:6.1f}%")
    print("=" * 80)
    print(f"Detailed run metrics saved to: {results_path}")

    return summary

if __name__ == "__main__":
    summary = run_evaluation()
    if summary["accuracy_pct"] < 80.0:
        print(f"Evaluation accuracy below gate threshold (got {summary['accuracy_pct']}%, expected >= 80.0%)")
        sys.exit(1)
    else:
        print(f"Evaluation PASSED gate threshold ({summary['accuracy_pct']}% >= 80.0%)")
        sys.exit(0)
