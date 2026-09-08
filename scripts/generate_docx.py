"""
FactLoom Project Brief — Generator
Produces FactLoom_Project_Brief.docx in the project root.
Run with: python scripts/generate_docx.py
"""

import os
from docx import Document
from docx.shared import Pt, RGBColor, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

def add_heading(doc, text, level=1, color=None):
    p = doc.add_heading(text, level=level)
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    if color:
        for run in p.runs:
            run.font.color.rgb = RGBColor(*color)
    return p

def add_body(doc, text):
    p = doc.add_paragraph(text)
    p.style.font.size = Pt(11)
    return p

def add_bullet(doc, text, level=0):
    p = doc.add_paragraph(text, style='List Bullet')
    p.paragraph_format.left_indent = Inches(0.25 * (level + 1))
    return p

def add_table_row(table, cells):
    row = table.add_row()
    for i, text in enumerate(cells):
        row.cells[i].text = text
    return row

def add_separator(doc):
    doc.add_paragraph("─" * 60)

def set_header_row(table):
    """Make the first row of a table bold and styled."""
    hdr = table.rows[0]
    for cell in hdr.cells:
        for para in cell.paragraphs:
            for run in para.runs:
                run.bold = True
    return hdr

doc = Document()

# --- Document margins ---
for section in doc.sections:
    section.top_margin = Cm(2)
    section.bottom_margin = Cm(2)
    section.left_margin = Cm(2.5)
    section.right_margin = Cm(2.5)

# ============================================================
# TITLE
# ============================================================
title = doc.add_heading("FactLoom — Project Brief", level=0)
title.alignment = WD_ALIGN_PARAGRAPH.CENTER
for run in title.runs:
    run.font.color.rgb = RGBColor(0x1A, 0x1A, 0x2E)

subtitle = doc.add_paragraph("Auditable Cross-Document Fact Reconciliation")
subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
subtitle.runs[0].bold = True
subtitle.runs[0].font.size = Pt(13)

doc.add_paragraph()

# ============================================================
# SECTION 1 — THE PROBLEM
# ============================================================
add_heading(doc, "1. The Problem We Are Solving", level=1)

add_body(doc,
    "Imagine you are a financial analyst. You open Delhivery's Annual Report and see:"
)
add_bullet(doc, "Adjusted EBITDA: ₹1,266.41 million")
add_bullet(doc, "Source: Page 48 of the Annual Report, FY24")

add_body(doc,
    "Then you open the Q4 Earnings Presentation and see:"
)
add_bullet(doc, "Adjusted EBITDA: ₹127 Cr")
add_bullet(doc, "Source: Page 3 of the Earnings Deck, FY24")

doc.add_paragraph()
add_body(doc,
    "Are these the same number? A different number? A mistake? How would you know?"
)
doc.add_paragraph()
add_body(doc,
    "The answer is: they ARE the same number, just written in different units. "
    "₹1,266.41 million equals approximately ₹126.6 Crore — within 0.28% rounding difference, "
    "which is completely normal in financial reporting."
)
doc.add_paragraph()
add_body(doc,
    "But here is the critical point: a normal AI assistant, a search engine, or a human "
    "analyst skimming documents would NOT catch this. They would either see two different "
    "numbers and get confused, or worse — silently pick one and ignore the other. "
    "If there is a real mistake — if the numbers genuinely disagree — that would be invisible too."
)
doc.add_paragraph()
add_body(doc,
    "This problem gets much worse at scale:"
)
add_bullet(doc, "Companies publish 5–20 documents per year — annual reports, earnings calls, prospectuses, regulatory filings")
add_bullet(doc, "The same metric gets mentioned dozens of times in different formats and units")
add_bullet(doc, "Older filings can contradict newer ones (e.g., a director who resigned)")
add_bullet(doc, "Some numbers are estimates that get revised later by official figures")
add_bullet(doc, "Current AI tools (ChatGPT, etc.) invent explanations or average conflicting numbers — which is dangerous in financial contexts")

doc.add_paragraph()

# ============================================================
# SECTION 2 — THE SOLUTION
# ============================================================
add_heading(doc, "2. What FactLoom Does", level=1)

add_body(doc,
    "FactLoom is a fact reconciliation engine. Instead of answering questions with \"I think,\" "
    "it answers with \"Here is the exact quote, the page number, the bounding box on the PDF, "
    "and the arithmetic that proves these two numbers are the same — or why they are not.\""
)
doc.add_paragraph()
add_body(doc,
    "Think of it like a detective system for financial documents. It:"
)
add_bullet(doc, "Reads every PDF and extracts every number with its exact context")
add_bullet(doc, "Assigns every number to a canonical fact (Who reported What, for When)")
add_bullet(doc, "Compares every pair of numbers about the same fact across documents")
add_bullet(doc, "Runs arithmetic to decide: same number in different units? Real contradiction? Outdated claim?")
add_bullet(doc, "Shows you exactly where it got the answer, with the exact quote highlighted in the PDF")
add_bullet(doc, "Refuses to answer when it genuinely cannot resolve a conflict — it says \"I don't know\" instead of making something up")

doc.add_paragraph()

# ============================================================
# SECTION 3 — HOW IT WORKS
# ============================================================
add_heading(doc, "3. How It Works — The Pipeline", level=1)

add_body(doc,
    "The system processes documents through four stages:"
)
doc.add_paragraph()

add_heading(doc, "Stage 1: Ingestion", level=2)
add_body(doc,
    "When you upload a PDF, FactLoom uses PyMuPDF (a PDF library) to extract every text block "
    "on every page, along with exact coordinate bounding boxes — so later we know precisely "
    "WHERE on the page a number appears. This text is then sent to an AI model (Groq's LLaMA 3.3) "
    "which extracts structured records: the number, its unit, the fiscal period it refers to, "
    "and the exact verbatim quote from the document."
)
doc.add_paragraph()

add_heading(doc, "Stage 2: The Fact Registry (Canonicalization)", level=2)
add_body(doc,
    "Every extracted number needs to be matched to a canonical fact. A 'canonical fact' is like "
    "a card in a filing cabinet: it represents one specific thing — "
    "e.g., 'Delhivery's Adjusted EBITDA for FY24.'"
)
doc.add_paragraph()
add_body(doc,
    "When a new number comes in, the system asks: does a canonical fact for this already exist? "
    "It uses sentence embeddings (AI-generated numerical fingerprints of text meaning) to find "
    "the closest match. The decision process has three tiers:"
)
add_bullet(doc, "Very high similarity (≥88%): Automatically link to existing fact — no human input needed")
add_bullet(doc, "Middle range (65–88%): Ask the LLM to adjudicate — is 'EBITDA' the same as 'Adjusted EBITDA'? Not necessarily!")
add_bullet(doc, "Very low similarity (<65%): Create a brand new fact in the registry")

doc.add_paragraph()

add_heading(doc, "Stage 3: The 3-Tier Reconciliation Engine", level=2)
add_body(doc,
    "Once two observations are linked to the same fact, the engine compares them:"
)
doc.add_paragraph()
add_body(doc,
    "Tier 1 — Deterministic Rules (runs FIRST, no AI involved):"
)
add_bullet(doc, "Convert both numbers to a common base unit (e.g., both to base INR)")
add_bullet(doc, "Calculate the percentage difference")
add_bullet(doc, "If the difference is within 0.5%, conclude they are the same number with rounding")
add_bullet(doc, "CRITICAL: If the unit is a discrete count (customers, people, items), block the rounding — you cannot round a headcount")

add_body(doc, "Tier 2 — LLM Adjudication (for edge cases Tier 1 cannot resolve):")
add_bullet(doc, "Sends both observations to the AI with a structured prompt")
add_bullet(doc, "AI returns: SAME_AS / UNRESOLVED / SUPERSEDES / RECONCILED_BY")

add_body(doc, "Tier 3 — Independent Verifier (backstop that overrides the AI):")
add_bullet(doc, "Re-runs the arithmetic independently, without looking at what Tier 2 said")
add_bullet(doc, "If the AI said SAME_AS but the math doesn't check out, the verifier DOWNGRADES to UNRESOLVED")
add_bullet(doc, "This is the most important safety feature — the AI cannot lie about the numbers")

doc.add_paragraph()

add_heading(doc, "Stage 4: Query & Answer", level=2)
add_body(doc,
    "When you ask a question, the system:"
)
add_bullet(doc, "Parses your question to find: entity, metric, and time period")
add_bullet(doc, "Looks up matching facts and their observations from the database")
add_bullet(doc, "Synthesizes an answer that cites every number with [cite:obs_id] tags")
add_bullet(doc, "Validates every citation tag against the database before responding — if any citation doesn't resolve, it's caught")
add_bullet(doc, "If the question has multiple valid answers (different periods, ambiguous scope), presents all of them instead of guessing")

doc.add_paragraph()

# ============================================================
# SECTION 4 — UNIQUE FEATURES
# ============================================================
add_heading(doc, "4. What Makes This Different", level=1)

features = [
    (
        "The Discrete Count Safeguard",
        "33,250 vs 33,278 active customers. The difference is 0.084% — which is well inside the 0.5% "
        "rounding tolerance that correctly identifies rounded financial figures. But a customer count "
        "cannot be rounded. One document has 33,250 and another has 33,278, and without a footnote "
        "explaining the gap, this is a real unresolved discrepancy. Most systems would silently call "
        "them the same. FactLoom abstains and says: 'I cannot resolve this.' This is the hardest and "
        "most important case to get right."
    ),
    (
        "Zero Registry Pollution",
        "When the system processes a user question, it should NEVER accidentally add that question "
        "into its metric database. Without this guardrail, searching for 'EBITDA across all documents' "
        "could create a ghost metric called 'EBITDA across all documents' in the registry, which would "
        "then corrupt future searches. FactLoom uses a strict allow_create=False flag on every query "
        "path to prevent this entirely."
    ),
    (
        "The Deterministic Backstop",
        "Every single relationship the AI produces is independently re-verified with arithmetic. "
        "The AI and the math verifier are completely separate. If the AI hallucinate that two different "
        "numbers are identical, the verifier catches it and overrides the decision. This is what "
        "'deterministic backstop' means: the deterministic system always has the final word on numbers."
    ),
    (
        "Temporal Supersession",
        "A 2022 IPO Prospectus says Suvir Sujan is a Nominee Director at Delhivery. "
        "A 2023 BSE regulatory filing says he resigned on August 24, 2023. "
        "FactLoom correctly identifies that the later filing supersedes the earlier one, and answers "
        "'Is he still a director?' with 'No — he ceased directorship on August 24, 2023 [cite:obs_2] — "
        "the 2022 Prospectus listed him as nominee [cite:obs_1], but this was superseded.' "
        "A chatbot would likely answer 'Yes' based on the Prospectus."
    ),
    (
        "Mandatory Abstention on Ambiguity",
        "If you ask 'What is India's GDP growth?' without specifying a year, FactLoom has data for "
        "FY24 (8.2% estimate from Economic Survey) and FY24 (8.4% actual from RBI Report). "
        "Rather than averaging them or picking one, it shows BOTH with their sources and explicitly "
        "says: 'These are from different periods / different methodologies — I cannot collapse them "
        "into a single answer.' This is the correct behaviour that prevents compounding errors."
    ),
    (
        "100% Citation Resolution Rate",
        "Every answer includes clickable citation tags like [cite:obs_4b2a1f]. Before the answer "
        "is returned to you, a citation validator checks every single tag against the database. "
        "If even one observation ID doesn't exist, the validation fails. In 28 benchmark questions "
        "with hundreds of citations, the rate was 100.0% — zero hallucinated citations."
    ),
]

for title_text, body_text in features:
    add_heading(doc, title_text, level=2)
    add_body(doc, body_text)
    doc.add_paragraph()

# ============================================================
# SECTION 5 — THE WEBSITE PAGES
# ============================================================
add_heading(doc, "5. What Each Page of the Website Does", level=1)

pages = [
    (
        "Command Center (home page)",
        [
            "The landing page. Shows three live numbers pulled directly from the database: how many documents are loaded, how many canonical facts have been discovered, and how many reconciled relationships exist between facts.",
            "Documents = number of PDFs ingested into the system",
            "Canonical Facts = number of unique (Who, What, When) facts registered across all documents",
            "Reconciled Edges = number of pairs of observations that have been compared and given a verdict (SAME_AS, UNRESOLVED, SUPERSEDES, etc.)",
            "The animated braided ropes in the background are not decorative — they represent the conceptual metaphor: individual document 'threads' being woven into verified truth.",
        ]
    ),
    (
        "Reconciliation Hub",
        [
            "The main demonstration page. Shows the four core test cases with full visual explanations.",
            "Each case has a visual animation: braided ropes merging (SAME_AS), fraying apart (UNRESOLVED), or knotting in sequence (SUPERSEDES).",
            "For Case 1 (EBITDA): The Braid View shows ₹1,266.41M and ₹127 Cr being woven into a single verified strand, with a badge showing 'ROUNDING + UNIT_MISMATCH — Δ 0.283%.'",
            "For Case 2 (Active Customers): The Fray View shows 33,250 and 33,278 pulling apart into loose frayed fibers that cannot merge, with a gap in the middle. The orange badge says UNRESOLVED.",
            "For Case 3a (Director): The Knot View shows a temporal thread tied into an overhand knot — representing the supersession event.",
        ]
    ),
    (
        "Fact Explorer",
        [
            "A searchable, filterable table of every canonical fact in the database.",
            "Click any row to expand it and see all the observations that contribute to that fact — with exact quotes, page numbers, and documents.",
            "Use the filters at the top to narrow by entity (company/person), metric (Revenue, EBITDA, etc.), or time period.",
            "The numbers shown in the table are the canonical values after unit normalization.",
        ]
    ),
    (
        "Evidence Viewer",
        [
            "A PDF document viewer that lets you inspect any document page by page.",
            "Use the typeable page number input (click on it and type any number, then press Enter) to jump directly to any page.",
            "Use Fit Page to see the whole page, or Fit Width to zoom in and scroll.",
            "When you click a citation badge in the Ask panel, it automatically opens the right document on the right page and highlights the exact bounding box where the number appears with a green glowing rectangle.",
        ]
    ),
    (
        "Ask Panel",
        [
            "A natural language Q&A interface. Type any question about the documents.",
            "The answer always includes citation tags like [cite:obs_4b2a1f] — these are clickable and open the Evidence Viewer at the exact location.",
            "If the question is ambiguous (no time period specified, or multiple facts match), the system presents multiple answer cards instead of collapsing them.",
            "If the question asks about something not in the documents (a hallucination trap), the system returns 'No grounded facts found for this query.'",
            "If the question involves an UNRESOLVED conflict, the system shows BOTH numbers and explicitly states it cannot resolve the gap.",
        ]
    ),
    (
        "Limitations Panel",
        [
            "A deliberately honest page disclosing what the system cannot do well.",
            "This is NOT boilerplate — each limitation was discovered during development:",
            "Discrete Count Safeguard edge cases: The 0.084% active customer gap is documented here.",
            "Structural table parsing: Tables with merged headers or complex column layouts may not parse perfectly.",
            "EPS modifier attachment: Standalone 'Basic EPS' and 'Diluted EPS' may occasionally alias incorrectly if the document header is stripped.",
            "Segment sum tolerances: Corporate overhead eliminations in multi-segment tables need special handling.",
        ]
    ),
    (
        "Upload",
        [
            "Upload any new PDF. The system ingests it, extracts facts, and registers them into the canonical registry.",
            "New metrics and entities are automatically discovered from the new document.",
            "If you upload an Apple 10-K, the system will correctly extract iPhone revenue, Services revenue, etc. without any Apple-specific tuning.",
        ]
    ),
]

for page_title, bullets in pages:
    add_heading(doc, page_title, level=2)
    for b in bullets:
        add_bullet(doc, b)
    doc.add_paragraph()

# ============================================================
# SECTION 6 — WHAT THE NUMBERS MEAN
# ============================================================
add_heading(doc, "6. What All Those Numbers Mean", level=1)

add_body(doc, "Here is a reference glossary for every number and label you will see in the UI:")
doc.add_paragraph()

glossary = doc.add_table(rows=1, cols=2)
glossary.style = 'Table Grid'
glossary.rows[0].cells[0].text = "Term / Number"
glossary.rows[0].cells[1].text = "What It Means"
set_header_row(glossary)

glossary_items = [
    ("7 Documents", "7 PDF files have been ingested into the system"),
    ("64 Canonical Facts", "64 unique (entity, metric, period) combinations have been registered — e.g. 'Delhivery / Adjusted EBITDA / FY24' is one fact"),
    ("31 Reconciled Edges", "31 pairs of observations have been compared and given a relationship verdict"),
    ("SAME_AS", "Two observations report the same number — corroborated, with the unit/rounding dimension shown"),
    ("UNRESOLVED", "Two observations disagree and the system cannot explain why — mandatory abstention"),
    ("SUPERSEDES", "The more recent filing overrides the older one — e.g. a resignation overrides a prospectus listing"),
    ("RECONCILED_BY [ESTIMATE_VS_ACTUAL]", "An advance estimate was later replaced by the official reported figure"),
    ("Δ 0.283%", "Delta — the percentage difference between two numbers after unit normalization"),
    ("verified_bool = 1", "The Tier-3 independent verifier confirmed the arithmetic is correct"),
    ("verified_bool = 0", "The verifier downgraded the relationship — the AI's claim was rejected"),
    ("[cite:obs_4b2a1f]", "A citation tag linking to a specific observation — obs ID uniquely identifies the verbatim quote in the database"),
    ("ROUNDING", "The difference is within 0.5% — consistent with standard financial reporting rounding"),
    ("UNIT_MISMATCH", "Both numbers refer to the same amount but in different units (e.g., Millions vs Crore)"),
    ("FY24", "Fiscal Year 2024 — April 2023 to March 2024 for Indian companies"),
    ("₹ Cr / ₹ million", "₹ Crore (10 million) vs ₹ million — 1 Crore = 10 million = 0.1 million Crore"),
    ("Tier-3 Verified badge", "The green badge on a relationship card meaning arithmetic was confirmed by the deterministic verifier"),
    ("Discrete Count Safeguard", "Flag that prevents the rounding tolerance from being applied to customer counts, employee counts, etc."),
    ("allow_create=False", "A guardrail that prevents question text from being written into the metric registry during query processing"),
    ("Phase 7 benchmark 28/28", "28 evaluation questions across 7 categories all passed — the accuracy and citation rate are both 100%"),
]

for term, meaning in glossary_items:
    r = glossary.add_row()
    r.cells[0].text = term
    r.cells[1].text = meaning

doc.add_paragraph()

# ============================================================
# SECTION 7 — HOW TO TEST THE SYSTEM
# ============================================================
add_heading(doc, "7. How to Test the System", level=1)

add_heading(doc, "Quick smoke test (2 minutes)", level=2)
add_body(doc, "With the system running (npm run dev from project root):")
add_bullet(doc, "1. Go to http://localhost:5173 — the landing page should show 7 documents, 64+ facts, 31+ edges")
add_bullet(doc, "2. Click 'Reconciliation' in the top nav")
add_bullet(doc, "3. Case 1 tab: you should see a braided animation and the SAME_AS verdict with Δ 0.283%")
add_bullet(doc, "4. Case 2 tab: you should see fraying fibers and an UNRESOLVED orange badge")
add_bullet(doc, "5. Click 'Ask' in the top nav")
add_bullet(doc, "6. Type: 'What was Delhivery's FY24 Adjusted EBITDA?' — you should see a grounded answer with [cite:] tags")
add_bullet(doc, "7. Click one of the [cite:] tags — it should open the Evidence Viewer on the correct page with a green bounding box highlight")

doc.add_paragraph()

add_heading(doc, "Hallucination trap test", level=2)
add_body(doc, "In the Ask panel, type any of these — the system should decline to answer:")
add_bullet(doc, "'What were Apple's electric vehicle sales in FY24?' — Apple sold no EVs, not in any document")
add_bullet(doc, "'What is Acme Corp's FY26 revenue?' — fictional company, future year")
add_bullet(doc, "'What is Delhivery's market cap?' — not in the documents")

doc.add_paragraph()

add_heading(doc, "Abstention test", level=2)
add_body(doc, "Type: 'What is India's GDP growth?' — without a year. The system should show multiple fact cards (FY24 estimate and FY24 actual) and explicitly refuse to give a single answer.")

doc.add_paragraph()

add_heading(doc, "Full automated benchmark", level=2)
add_body(doc, "Run the full 28-question evaluation suite from a terminal:")
doc.add_paragraph(".venv\\Scripts\\python eval/run_eval.py")

doc.add_paragraph()

# ============================================================
# SECTION 8 — 3-MINUTE PITCH SCRIPT
# ============================================================
add_heading(doc, "8. Three-Minute Pitch Script", level=1)

add_body(doc,
    "The following is a script you can deliver verbatim in approximately 3 minutes, covering the problem, "
    "solution, architecture, and unique features."
)
doc.add_paragraph()

add_heading(doc, "Opening (30 seconds)", level=2)
add_body(doc,
    "\"Here is a problem that every financial analyst faces. You open a company's Annual Report and see "
    "Adjusted EBITDA of 1,266 million rupees. Then you open the Q4 Earnings Deck and see 127 Crore. "
    "Same company, same quarter, same metric — two completely different numbers. Are they the same? "
    "A contradiction? A mistake? A normal chatbot will either average them, pick one, or make something up. "
    "FactLoom does neither. It proves the answer.\""
)
doc.add_paragraph()

add_heading(doc, "The Demo (60 seconds)", level=2)
add_body(doc,
    "\"Let me show you the Reconciliation Hub. [Point to Case 1] These two strands represent two "
    "observations from two different documents — they are being woven together because the engine "
    "determined they are the same number. The badge says: SAME_AS, dimension ROUNDING + UNIT_MISMATCH, "
    "delta 0.283%. That 0.283% is actual arithmetic — 1,266.41 million normalized to base rupees, "
    "versus 127 Crore normalized to base rupees — the math checks out.\""
)
doc.add_paragraph()
add_body(doc,
    "\"Now look at Case 2. [Point to Case 2] Active customers: 33,250 vs 33,278. The difference is "
    "only 0.084% — that is INSIDE our 0.5% rounding tolerance. A normal system would call these "
    "the same. We don't. Because this is a headcount — a discrete count — and you cannot round "
    "a customer. The system refuses to merge them and flags this as UNRESOLVED. "
    "That is our Discrete Count Safeguard, and it is the single hardest case to get right.\""
)
doc.add_paragraph()

add_heading(doc, "The Architecture (45 seconds)", level=2)
add_body(doc,
    "\"Under the hood, every PDF goes through four stages. First, PyMuPDF extracts every text "
    "block with its exact page coordinates. Second, Groq's LLaMA 3.3 model extracts structured "
    "records — number, unit, period, verbatim quote. Third, a canonicalization registry with "
    "sentence embeddings decides if a new number belongs to an existing fact or needs a new one. "
    "And fourth — this is the key innovation — a three-tier reconciliation engine. Tier 1 is pure "
    "deterministic arithmetic: unit normalization, rounding tolerance, discrete count safeguard. "
    "Tier 2 is LLM adjudication for edge cases. Tier 3 is an independent deterministic verifier "
    "that re-runs the arithmetic and can OVERRIDE the AI if the math doesn't match. "
    "The AI cannot lie about numbers here.\""
)
doc.add_paragraph()

add_heading(doc, "The Unique Features (30 seconds)", level=2)
add_body(doc,
    "\"Three things nobody else does. One: every answer includes clickable citation tags that "
    "open the exact page of the source PDF with the bounding box highlighted — 100% citation "
    "resolution, zero hallucinated citations across 28 benchmark questions. Two: when we cannot "
    "resolve a conflict, we say so explicitly and refuse to guess — mandatory abstention that "
    "triggers correctly even at 0.084% delta. Three: we validated on Apple's 10-K — a document "
    "the system was never tuned on — and correctly extracted iPhone revenue, Services revenue, "
    "and EPS without any Apple-specific configuration.\""
)
doc.add_paragraph()

add_heading(doc, "The Close (15 seconds)", level=2)
add_body(doc,
    "\"FactLoom is not a chatbot that answers financial questions. It is an audit engine that "
    "proves its answers with arithmetic and refuses to guess when the evidence is insufficient. "
    "The benchmark is 28 out of 28 questions correct, 100% citation resolution rate, "
    "31 unit tests green. The system is live at localhost:5173 right now.\""
)
doc.add_paragraph()

# ============================================================
# WRITE FILE
# ============================================================
output_path = os.path.join(os.path.dirname(__file__), '..', 'FactLoom_Project_Brief.docx')
doc.save(output_path)
print(f"Saved: {os.path.abspath(output_path)}")
