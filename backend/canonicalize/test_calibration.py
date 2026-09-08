"""
FactLoom Calibration Test CLI
Verifies that distinct accounting metrics remain separate while synonymous/unit-suffixed mentions merge.
Usage:
    python -m backend.canonicalize.test_calibration --pair "EBITDA,Adjusted EBITDA" --expect distinct
    python -m backend.canonicalize.test_calibration --pair "EBITDA,EBITDA (₹Cr)" --expect same
"""

import sys
import argparse
import tempfile
import os
from backend.store.db import init_db
from backend.canonicalize.registry import RegistryEngine

def main():
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    parser = argparse.ArgumentParser(description="Test registry calibration on metric pairs.")
    parser.add_argument("--pair", type=str, required=True, help="Comma-separated pair of metric mentions, e.g. 'EBITDA,Adjusted EBITDA'")
    parser.add_argument("--expect", type=str, choices=["distinct", "same"], required=True, help="Expected outcome: 'distinct' or 'same'")
    args = parser.parse_args()

    parts = [p.strip() for p in args.pair.split(",")]
    if len(parts) != 2:
        print(f"[ERROR] Expected exactly two comma-separated mentions, got: {args.pair}")
        sys.exit(1)

    mention_a, mention_b = parts[0], parts[1]

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        temp_db_path = tf.name

    try:
        init_db(temp_db_path)
        engine = RegistryEngine(db_path=temp_db_path)

        # Resolve first mention
        id_a, name_a = engine.resolve_metric(mention_a)
        # Resolve second mention
        id_b, name_b = engine.resolve_metric(mention_b)

        is_same = (id_a == id_b)
        actual = "same" if is_same else "distinct"

        print(f"Calibration Test: '{mention_a}' vs '{mention_b}'")
        print(f"  Mention A resolved -> ID: {id_a}, Canonical: '{name_a}'")
        print(f"  Mention B resolved -> ID: {id_b}, Canonical: '{name_b}'")
        print(f"  Result: {actual} (Expected: {args.expect})")

        if actual == args.expect:
            print("[PASS] Calibration check succeeded.")
            sys.exit(0)
        else:
            print(f"[FAIL] Calibration check failed: expected {args.expect}, got {actual}.")
            sys.exit(1)

    finally:
        if os.path.exists(temp_db_path):
            try:
                os.remove(temp_db_path)
            except Exception:
                pass

if __name__ == "__main__":
    main()
