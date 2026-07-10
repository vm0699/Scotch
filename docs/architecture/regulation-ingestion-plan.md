# Tamil Nadu Regulation Ingestion Plan

## Current state (Phase 32)

The TN advisory engine ships with **placeholder values** sourced from publicly documented CMDA/DTCP norms. Every output is:
- Flagged `is_placeholder: true` in the rule JSON
- Labelled `needs_professional_verification: true` in every API response and UI chip
- Accompanied by the disclaimer: *"These are advisory outputs generated from placeholder regulation values…"*

This structure is ingestion-ready: swapping real values requires only updating `data/regulations/tamil_nadu/rules.json` and `sources.json` — no engine code changes needed.

---

## Source documents to ingest

| Priority | Document | Issuer | Where to obtain |
|---|---|---|---|
| 1 | CMDA Development Regulations 2019 (+ amendments) | Chennai Metropolitan Development Authority | cmdachennai.gov.in → Publications |
| 2 | Tamil Nadu Combined Development and Building Rules 2019 (TN CDBRR) | DTCP Tamil Nadu | tntp.gov.in → Acts & Rules |
| 3 | TN Rainwater Harvesting GO Ms. No. 117 (2003) | Govt of Tamil Nadu | tn.gov.in → G.O.s |
| 4 | Local body bye-laws (Coimbatore, Madurai, etc.) | Respective municipal corporations | Per-city portals |

---

## Ingestion steps

### Step 1 — Obtain source PDFs

Download the official PDFs for each source document above. Store them under:
```
services/api/app/data/regulations/tamil_nadu/source_pdfs/
  cmda_dr_2019.pdf
  tn_cdbrr_2019.pdf
  tn_rwh_go_2003.pdf
```
(These are gitignored if large; reference by filename in the rule JSON.)

### Step 2 — Extract rule values

For each rule in `rules.json`, locate the corresponding section in the source PDF and update:
- `is_placeholder: false`
- Actual numeric limits (setback distances, FSI values, coverage %, stair widths, etc.)
- `source_section` — exact regulation number and subsection
- `version_date` — date of the specific regulation version
- `confidence: 0.9` (once verified from official text)

### Step 3 — Update sources.json

For each source:
- Set `is_placeholder: false`
- Add actual `url_or_path` (URL or relative path to the PDF)
- Add `version_date` from the official publication

### Step 4 — Add amendment tracking

Create `data/regulations/tamil_nadu/amendments.json`:
```json
[
  {
    "amendment_id": "cmda_amend_2022_01",
    "source_id": "cmda_dr_2019",
    "rule_ids_affected": ["tn_fsi_advisory"],
    "description": "FSI increased to 2.0 for certain CMA zones",
    "effective_date": "2022-06-01",
    "gazette_reference": "TN Gazette No. XX/2022"
  }
]
```

### Step 5 — Re-run tests

```bash
cd services/api
pytest tests/test_regulation_sources.py tests/test_tn_regulations.py -v
```

All tests should still pass. If new rule fields are added, update the schema validation in `test_regulation_sources.py`.

---

## Future: RAG / chunking pipeline (roadmap)

For higher-confidence extraction from large regulation PDFs:

1. **PDF → chunks**: Split each regulation PDF into ~512-token chunks with section headers preserved.
2. **Embedding store**: Index chunks via embeddings (local FAISS or cloud vector DB).
3. **Rule-grounded retrieval**: For each rule check, retrieve the 2–3 most relevant chunks and feed to an LLM for structured extraction.
4. **Human review gate**: Every extracted value is reviewed by a licensed architect before `is_placeholder` is set to `false`.
5. **Version tracking**: Each rule value carries the source chunk ID + extraction timestamp.

This is a manual-then-automated workflow. Phase 32 ships the deterministic placeholder layer; the RAG layer is a Phase 39+ enhancement.

---

## Confidence levels

| `confidence` | Meaning |
|---|---|
| 0.90–1.00 | Verified from official text by a licensed professional |
| 0.75–0.89 | Placeholder from publicly documented norms (Phase 32 default) |
| 0.60–0.74 | Inferred from secondary sources or older versions |
| < 0.60 | High uncertainty — treat as rough advisory only |

---

## Disclaimer (embedded in every API response)

> These are advisory outputs generated from placeholder regulation values. They do NOT constitute legal compliance certification. Consult a licensed architect/engineer and verify against the current CMDA/DTCP regulations before submission.
