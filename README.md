# FactLoom — Auditable Cross-Document Fact Reconciliation

> **"When documents disagree, don't average — audit."**

FactLoom is a full-stack system that reads multiple financial and regulatory PDFs, extracts every numerical claim with its exact source quote, and then deterministically decides whether two numbers are the *same fact* expressed differently, a genuine contradiction, or superseded by a later filing. Every answer is grounded in verifiable evidence with zero hallucinated citations.

[![Phase 7 Benchmark](https://img.shields.io/badge/Benchmark-28%2F28%20100%25-34D399?style=flat-square&logo=checkmarx)](eval/results.json)
[![Unit Tests](https://img.shields.io/badge/Tests-31%2F31%20Passing-34D399?style=flat-square)](tests/)
[![Citation Audit](https://img.shields.io/badge/Citation%20Audit-100%25%20Resolved-34D399?style=flat-square)]()
[![Stack](https://img.shields.io/badge/Stack-FastAPI%20%7C%20React%2019%20%7C%20Three.js%20%7C%20SQLite-6B7280?style=flat-square)]()

---

## Table of Contents

- [Problem & Solution](#problem--solution)
- [Architecture](#architecture)
- [The 3-Tier Reconciliation Pipeline](#the-3-tier-reconciliation-pipeline)
- [Unique Technical Features](#unique-technical-features)
- [Quick Start](#quick-start)
- [Running the Eval Suite](#running-the-eval-suite)
- [Demo Cases](#demo-cases)
- [Dataset & Documents](#dataset--documents)

---

## Problem & Solution

### The Problem

Financial documents routinely report the *same number* in different ways:

| Document | What it says |
|---|---|
| Annual Report | EBITDA: ₹1,266.41 million |
| Earnings Deck | Adjusted EBITDA: ₹127 Cr |

A naive system sees two different numbers and either ignores one, averages them, or — in the case of LLMs — invents an explanation. None of these are acceptable when the stakes are legal filings, audit trails, or investor due diligence.

### The Solution

FactLoom treats every number as a **Fact** with three mandatory properties:
1. **Who** — the entity (e.g., Delhivery Limited)
2. **What** — the canonical metric (e.g., Adjusted EBITDA)
3. **When** — the exact fiscal period (e.g., FY24)

Every claim extracted from a PDF is an **Observation** — a verbatim quote, page number, bounding box, and raw value. The system then runs a 3-tier pipeline to decide whether two Observations of the same Fact are corroborated, superseded, or genuinely unresolved — and it proves its work with arithmetic.

---

## Architecture

```mermaid
flowchart TB
    subgraph INPUT["📄 Document Ingestion"]
        PDF["PDF Files\n(Annual Reports, Earnings Decks,\nProspectuses, RBI Reports)"]
        PARSE["PyMuPDF Parser\nExtract text blocks\n+ bounding boxes"]
        PDF --> PARSE
    end

    subgraph EXTRACT["🧠 LLM Extraction (Groq)"]
        GROQ["Groq LLaMA 3.3 70B\nStructured JSON extraction\nper page chunk"]
        PARSE --> GROQ
        GROQ --> OBS["Raw Observations\n{value, unit, quote, page, bbox}"]
    end

    subgraph CANON["🏛 Canonicalization Registry"]
        EMBED["Sentence Embedding\nall-MiniLM-L6-v2"]
        UPPER["High Similarity ≥ 0.88\n→ Deterministic Alias"]
        MIDDLE["Middle Band 0.65–0.88\n→ LLM Adjudication"]
        LOWER["Low Similarity < 0.65\n→ New Registry Entry"]
        OBS --> EMBED
        EMBED --> UPPER
        EMBED --> MIDDLE
        EMBED --> LOWER
        UPPER --> FACT["Canonical Fact\n{entity, metric, period, scope}"]
        MIDDLE --> FACT
        LOWER --> FACT
    end

    subgraph RECONCILE["⚖ 3-Tier Reconciliation"]
        T1["Tier 1: Deterministic\nUnit normalization\n±0.5% rounding tolerance\nDiscrete count safeguard"]
        T2["Tier 2: LLM Adjudication\n(Groq) for edge cases"]
        T3["Tier 3: Deterministic Verifier\nIndependent arithmetic backstop\nDowngrades invalid LLM claims"]
        T1 --> T2 --> T3
    end

    subgraph RELATIONS["🔗 Relationship Types"]
        SAME["SAME_AS\nCorroborated with audit"]
        UNRES["UNRESOLVED\nGenuine contradiction\nMandatory abstention"]
        SUPER["SUPERSEDES\nTemporal succession"]
        RECON["RECONCILED_BY\nEstimate → Actual"]
        T3 --> SAME
        T3 --> UNRES
        T3 --> SUPER
        T3 --> RECON
    end

    subgraph QUERY["💬 Query Engine"]
        PARSER["Query Parser\nExtract entity+metric+period\nallow_create=False guardrail"]
        RETRIEVER["Retriever\nFact + Observation lookup"]
        SYNTH["Answer Synthesizer\nGrounded citations [cite:obs_id]\nAmbiguity & abstention gates"]
        CITVAL["Citation Validator\n100% citation audit\nZero hallucination backstop"]
        PARSER --> RETRIEVER --> SYNTH --> CITVAL
    end

    subgraph STORE["🗃 SQLite Store"]
        DB[("factloom.db\ndocuments, pages\nentities, metrics\nfacts, observations\nrelationships")]
    end

    subgraph FRONTEND["🖥 React 19 Frontend"]
        HERO["Command Center\nLive DB stats"]
        RECON_HUB["Reconciliation Hub\nBraid / Fray / Knot animations"]
        EXPLORER["Fact Explorer\nFilterable registry"]
        EVIDENCE["Evidence Viewer\nPDF + bbox highlighting"]
        ASK["Ask Panel\nGrounded answers"]
        LIMITS["Limitations Panel\nHonest disclosures"]
    end

    FACT --> STORE
    T3 --> STORE
    STORE --> QUERY
    QUERY --> FRONTEND
    STORE --> FRONTEND
```

---

## The 3-Tier Reconciliation Pipeline

```mermaid
sequenceDiagram
    participant OA as Observation A
    participant OB as Observation B
    participant T1 as Tier 1 (Deterministic)
    participant T2 as Tier 2 (LLM)
    participant T3 as Tier 3 (Verifier)
    participant DB as SQLite

    OA->>T1: value="1,266.41", unit="₹ million"
    OB->>T1: value="127", unit="₹ Cr"
    T1->>T1: Normalize both to base INR
    T1->>T1: Δ = 0.283% < 0.5% tolerance
    T1->>T3: Propose SAME_AS [ROUNDING + UNIT_MISMATCH]
    T3->>T3: Re-verify arithmetic independently
    T3->>DB: Persist SAME_AS, verified_bool=1

    Note over T1,T3: Case 2 — Discrete Count Safeguard
    OA->>T1: value="33,250", unit="count"
    OB->>T1: value="33,278", unit="count"
    T1->>T1: Δ = 0.084% < 0.5% BUT currency_family=count
    T1->>T2: Escalate — discrete count, no rounding convention
    T2->>T3: Propose UNRESOLVED
    T3->>DB: Persist UNRESOLVED, verified_bool=0
```

---

## Unique Technical Features

### 1. Discrete Count Safeguard
The system distinguishes continuous financial figures (where ±0.5% rounding tolerance applies) from discrete counts like headcounts. 33,250 vs 33,278 is only 0.084% — which *passes* the continuous tolerance but the engine **correctly abstains** because you cannot round a customer count.

### 2. Zero Query-Time Registry Pollution
A `allow_create=False` guardrail on the query parser prevents question strings (e.g., *"What is EBITDA across all documents?"*) from being inserted into the metric registry. Without this, past ghost metrics pollute future queries and return empty results silently.

### 3. Three-Tier Verification with Independent Backstop
Every relationship produced by LLM adjudication is independently re-verified with deterministic arithmetic. If the LLM claims two different numbers are `SAME_AS` but the math doesn't check out, the Tier-3 verifier **downgrades** it to `UNRESOLVED` and logs the rejection.

### 4. Temporal Supersession Tracking
When Suvir Sujan resigned as a director in August 2023, the 2022 Prospectus still listed him as "Nominee Director." The system correctly identifies the later filing supersedes the earlier one and answers *"Is he still a director?"* with `No` — citing both documents and explaining the succession.

### 5. Mandatory Abstention Gate
When a user asks a temporally unanchored question (e.g., "What is India's GDP growth?"), the system presents *all* matching facts from different fiscal periods side-by-side instead of collapsing them into a single number.

### 6. 100% Citation Resolution Rate
Every `[cite:obs_id]` badge in an answer is validated against the SQLite database before the response is returned. Zero hallucinated citations — any observation ID that doesn't resolve causes the citation validator to flag the answer.

---

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- A Groq API key (free tier works for demos)

### 1. Clone and configure

```bash
git clone https://github.com/darksinnnn/FactLoom.git
cd FactLoom
cp .env.example .env
# Edit .env and set: GROQ_API_KEY=your_key_here
```

### 2. Install backend dependencies

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # Mac/Linux
pip install -r requirements.txt
```

### 3. Install frontend dependencies

```bash
cd frontend
npm install
cd ..
```

### 4. Start everything with one command

```bash
npm install          # From project root — installs concurrently
npm run dev          # Starts FastAPI backend (port 8000) + Vite frontend (port 5173)
```

Open [http://localhost:5173](http://localhost:5173)

### 5. Seed the demo cases

The database is pre-seeded. If you need to re-seed:

```bash
.venv\Scripts\python -m backend.query.seed_cases
```

---

## Running the Eval Suite

The full 28-question benchmark runs end-to-end against the live database:

```bash
.venv\Scripts\python eval/run_eval.py
```

Results are written to `eval/results.json` and stored in the `eval_runs` SQLite table.

**Phase 7 benchmark results:**

| Category | Pass Rate |
|---|---|
| Extraction & Unit Conversion | 4/4 — 100% |
| Temporal Governance | 4/4 — 100% |
| Reconciled Metrics | 4/4 — 100% |
| Mandatory Abstention | 4/4 — 100% |
| Ambiguous Inquiry Handling | 4/4 — 100% |
| Cross-Doc Generalization (Apple 10-K) | 4/4 — 100% |
| Hallucination Traps | 4/4 — 100% |
| **TOTAL** | **28/28 — 100%** |

---

## Demo Cases

| Case | Documents | Reconciliation | Outcome |
|---|---|---|---|
| **Case 1: EBITDA Corroboration** | Annual Report + Earnings Deck | ₹1,266.41M vs ₹127 Cr — Δ 0.283% | `SAME_AS` [ROUNDING + UNIT_MISMATCH] |
| **Case 2: Active Customers** | Annual Report + Earnings Deck | 33,250 vs 33,278 — Δ 0.084% | `UNRESOLVED` [Discrete Count Safeguard] |
| **Case 3a: Director Status** | Prospectus 2022 + BSE Filing 2023 | Nominee → Resigned Aug 24, 2023 | `SUPERSEDES` |
| **Case 3b: GDP Estimate vs Actual** | Economic Survey + RBI Report | 8.2% estimate vs 8.4% actual | `RECONCILED_BY [ESTIMATE_VS_ACTUAL]` |

---

## Dataset & Documents

The starter dataset includes real public domain filings:

| # | File | Type | Pages |
|---|---|---|---|
| 1 | `01-delhivery-prospectus-2022-excerpt.pdf` | IPO Prospectus | 50p excerpt |
| 2 | `02-delhivery-annual-report-fy24-excerpt.pdf` | Annual Report | 50p excerpt |
| 3 | `03-delhivery-q4-fy24-earnings-presentation.pdf` | Earnings Deck | 50p excerpt |
| 4 | `01-india-economic-survey-2024-25-excerpt.pdf` | Gov. Report | 50p excerpt |
| 5 | `02-rbi-annual-report-2024-25-excerpt.pdf` | Central Bank Report | 100p excerpt |
| 6 | `apple-10k-fy24.pdf` | SEC 10-K (out-of-corpus test) | Full |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI 0.115, Python 3.10 |
| LLM Inference | Groq (LLaMA 3.3 70B) |
| PDF Processing | PyMuPDF |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) |
| Database | SQLite (factloom.db) |
| Frontend | React 19, TypeScript, Vite 8 |
| Styling | Tailwind CSS v4 |
| 3D Visuals | Three.js + React Three Fiber |
| Animations | Framer Motion + GSAP + Lenis |
| UI Icons | Phosphor Icons |

---

*FactLoom v0.1.0 — Built with grounded truth as a first principle.*
