"""
FactLoom Unit & Numerical Conversion Engine
Provides domain-agnostic, extensible numerical parsing, scale normalization,
and relative tolerance calculations per architecture.md §2.3.
"""

import re
from typing import Optional, Tuple, Any

SCALE_FACTORS = {
    # Financial and count scales
    "thousand": 1e3,
    "k": 1e3,
    "lakh": 1e5,
    "lac": 1e5,
    "million": 1e6,
    "mn": 1e6,
    "m": 1e6,
    "crore": 1e7,
    "cr": 1e7,
    "billion": 1e9,
    "bn": 1e9,
    "b": 1e9,
    "trillion": 1e12,
    "tn": 1e12,
    "t": 1e12,
}

RATE_FACTORS = {
    "percent": 1e-2,
    "pct": 1e-2,
    "%": 1e-2,
    "bps": 1e-4,
    "basis points": 1e-4,
}

CURRENCY_SYMBOLS = {
    "₹": "INR",
    "rs": "INR",
    "inr": "INR",
    "rupees": "INR",
    "rupee": "INR",
    "$": "USD",
    "usd": "USD",
    "dollar": "USD",
    "dollars": "USD",
    "€": "EUR",
    "eur": "EUR",
    "euro": "EUR",
    "£": "GBP",
    "gbp": "GBP",
}

def parse_numerical_value(val: Any) -> Optional[float]:
    """
    Extract clean floating-point numerical value from strings, handling:
    - Comma separators: '1,266.41' -> 1266.41
    - Parenthesized negative accounting numbers: '(1,008.0)' -> -1008.0
    - Percentage symbols: '+12.68%' -> 12.68
    - Greater-than/approx prefixes: '>33,200' -> 33200.0, 'over 33,250' -> 33250.0
    """
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)

    s = str(val).strip()
    if not s:
        return None

    # Check for parenthesized negative: (1,234.56) or (565)
    is_negative = False
    m_neg = re.search(r'\(([\d,]+(?:\.\d+)?)\)', s)
    if m_neg:
        is_negative = True
        s = m_neg.group(1)
    else:
        if s.startswith("-"):
            is_negative = True
            s = s[1:]
        elif s.startswith("+"):
            s = s[1:]

    # Strip prefixes like '>', '<', 'over', 'approx', 'about'
    s = re.sub(r'^[><~]|(?:over|approx|about|around)\s+', '', s, flags=re.IGNORECASE).strip()

    # Find the main numeric token
    m_num = re.search(r'[\d,]+(?:\.\d+)?', s)
    if not m_num:
        return None

    num_str = m_num.group(0).replace(",", "")
    try:
        f = float(num_str)
        return -f if is_negative else f
    except ValueError:
        return None

parse_numeric_value = parse_numerical_value

def extract_scale_and_currency(unit_str: Optional[str]) -> Tuple[float, str]:
    """
    Parse scale factor and base currency/quantity family from unit string.
    Returns (scale_factor, unit_family).
    """
    if not unit_str:
        return 1.0, "unitless"

    u = unit_str.strip().lower()
    scale = 1.0

    # 1. Detect Currency Family
    currency = "count"
    for sym, curr in CURRENCY_SYMBOLS.items():
        if sym in ("₹", "$", "€", "£"):
            if sym in u:
                currency = curr
                break
        else:
            if re.search(r'(?:\b|[^\w])' + re.escape(sym) + r'(?:\b|[^\w]|$)', u):
                currency = curr
                break

    # 2. Detect Scale Factor
    # Sort scales by length descending so "million" matches before "m"
    matched_scale = False
    for name, factor in sorted(SCALE_FACTORS.items(), key=lambda x: len(x[0]), reverse=True):
        pattern = r'(?:\b|[^\w])' + re.escape(name) + r'(?:\b|[^\w]|$)'
        if re.search(pattern, u):
            scale = factor
            matched_scale = True
            break

    # 3. Detect Rates/Percentages
    if not matched_scale:
        for name, factor in RATE_FACTORS.items():
            if name in u:
                scale = factor
                currency = "rate"
                break

    return scale, currency

def normalize_to_base(value: float, unit_str: Optional[str]) -> Tuple[float, str]:
    """
    Convert a value and unit into its fundamental base unit.
    E.g. (1266.41, "million rupees") -> (1266410000.0, "INR")
         (127, "₹ Cr") -> (1270000000.0, "INR")
         (81415.38, "million rupees") -> (81415380000.0, "INR")
         (8142, "₹ Cr") -> (81420000000.0, "INR")
    """
    scale, unit_family = extract_scale_and_currency(unit_str)
    base_val = value * scale
    return base_val, unit_family

def compute_relative_delta(val_a: float, val_b: float) -> float:
    """
    Compute relative difference |A - B| / max(|A|, |B|).
    Returns 0.0 if both are zero.
    """
    abs_a = abs(val_a)
    abs_b = abs(val_b)
    denom = max(abs_a, abs_b)
    if denom == 0.0:
        return 0.0
    return abs(val_a - val_b) / denom
