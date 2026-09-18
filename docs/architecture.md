# System Architecture — V1 vs V2

Technical documentation comparing both versions of the invoicing automation system.

## Summary

| | V1 Baseline | V2 AI-Powered |
|--|------------|---------------|
| Released | 2025 | 2026 |
| Stack | Python, n8n, Docker | Python, Claude, n8n, Docker |
| Input | Structured XLS | XLS + Scanned PDFs |
| Extraction | Direct cell reading | LLM + Prompt Engineering |
| Validation | NaN checks, deduplication | LLM self-check + corrections |
| Idempotent | ✓ | ✓ |
| Notifications | Telegram | Telegram |
| Error handling | n8n error workflow | n8n error workflow |

---

## V1 — Baseline Architecture

```
Windows (host)
└── "Facturacion 2025" folder
    ├── subdiarios/     (.XLS exported from SINET)
    ├── comprobantes/   (.XLS per invoice)
    └── base spreadsheet (.xlsx AFIP format)
         │
         ▼
┌─────────────────────────────────────────────┐
│  docker-compose                              │
│                                             │
│  ┌──────────┐  HTTP POST /run  ┌──────────┐ │
│  │   n8n    │ ──────────────> │  Python  │ │
│  │          │ <────────────── │ (Flask)  │ │
│  │ Schedule │  JSON summary   │          │ │
│  │ Trigger  │                 │ pandas   │ │
│  │          │                 │ openpyxl │ │
│  │ Telegram │                 │ xlrd     │ │
│  └──────────┘                 └──────────┘ │
└─────────────────────────────────────────────┘
         │
         ▼
   planilla_anual.xlsx
```

### V1 Flow

1. **Schedule Trigger** (n8n) — fires once a month
2. **HTTP Request** (n8n) — calls `POST /run`
3. **consolidar_facturas.py** — reads subledgers, matches with invoices
4. **pandas** — consolidates, sorts, deduplicates
5. **openpyxl** — writes to AFIP spreadsheet
6. **Telegram** (n8n) — sends result notification

---

## V2 — AI-Powered Architecture

```
Windows (host)
└── "Facturacion 2025" folder
    ├── subdiarios/     (.XLS exported from SINET)
    ├── comprobantes/   (.XLS per invoice)
    ├── PDFs/           (scanned invoices) ← NEW
    └── base spreadsheet (.xlsx AFIP format)
         │
         ▼
┌──────────────────────────────────────────────────────┐
│  docker-compose                                       │
│                                                      │
│  ┌──────────┐  POST /extract   ┌───────────────────┐ │
│  │   n8n    │ ───────────────> │    Python (V2)    │ │
│  │          │ <─────────────── │                   │ │
│  │ Schedule │  JSON extracted  │  prompt_extractor │ │
│  │ Trigger  │                  │  ┌─────────────┐  │ │
│  │          │  POST /run       │  │  Claude API │  │ │
│  │ Telegram │ ───────────────> │  │  (Anthropic)│  │ │
│  └──────────┘ <─────────────── │  └──────┬──────┘  │ │
│               JSON summary     │         │         │ │
│                                │  pandas + openpyxl│ │
│                                └───────────────────┘ │
└──────────────────────────────────────────────────────┘
         │                              │
         ▼                              ▼
   planilla_anual.xlsx          Claude API (external)
                               Extraction + Validation
```

### V2 Flow

1. **Schedule Trigger** (n8n) — fires once a month
2. **HTTP Request** to `/extract` (n8n) — sends scanned invoice text
3. **prompt_extractor.py** (Python) — 3-step pipeline with Claude:
   - **Extraction:** structured prompt → JSON with invoice data
   - **Validation:** Claude validates arithmetic and critical fields
   - **Preparation:** adapts output to consolidation format
4. **HTTP Request** to `/run` (n8n) — runs full consolidation
5. **consolidar_facturas.py** — processes structured data + V1 flow
6. **Telegram** (n8n) — sends complete result notification

---

## Prompt Engineering — Technical Detail

V2 uses 3 distinct prompts, each with a specific purpose:

### Prompt 1: Extraction

```
CRITICAL: You MUST respond ONLY with valid JSON, nothing else.
No preamble, no explanation, no markdown code blocks — just the JSON object.

Extract the following fields:
- invoice_date: invoice date (YYYY-MM-DD format)
- invoice_number: document number
...
If a field is not found or unclear, use null.
Quantities and amounts must be numbers, not strings.
```

**Techniques used:**
- Explicit format instruction (`ONLY valid JSON`)
- Negation of unwanted behaviors (`no preamble, no explanation`)
- Explicit data types (`must be numbers, not strings`)
- Fallback value for missing fields (`use null`)

### Prompt 2: Validation

```
Check for:
1. Arithmetic errors (net_total + tax_total should equal total_amount)
2. Invalid dates
3. Missing critical fields
4. Unrealistic values (negative amounts, etc.)

Respond ONLY with JSON in this format:
{"is_valid": true/false, "errors": [...], "corrected_fields": {...}}
```

**Techniques used:**
- Explicit validation checklist
- Forced output schema
- Self-check (Claude validates its own extraction)

### Prompt 3: Consolidation

```
Given the extracted invoice data below, prepare it for consolidation
into an Argentine tax authority (AFIP) format spreadsheet.
```

**Techniques used:**
- Domain context (AFIP, Argentina)
- Business-specific instructions

---

## Design Decisions

### Why two Claude calls (extraction + validation)?

A single prompt doing both extraction and validation tends to make silent trade-offs. Separating the steps:
- Allows catching errors from the first step
- Improves traceability (you know exactly what failed)
- Allows corrections without re-extracting

### Why not replace V1 entirely?

V1 is faster and cheaper for already-digitized subledgers (no API calls). V2 adds capability for irregular sources without removing what already works. Both coexist in the same container.

### Why Flask instead of FastAPI?

Flask is simpler and was already in V1. For this use case (few endpoints, no massive async load) it's sufficient. Migrating to FastAPI would be the next iteration if request volume increases.

---

## Estimated Costs

| Action | Estimated tokens | Approximate cost |
|--------|-----------------|------------------|
| Extraction (1 invoice) | ~500 tokens | $0.001 |
| Validation (1 invoice) | ~300 tokens | $0.0006 |
| Monthly batch (237 invoices) | ~190,000 tokens | $0.38 |

*Prices estimated with Claude Sonnet. Update according to current plan.*

---

## Security

- **API Key:** never hardcoded. Always passed via environment variable or `.env`
- **`.env` in `.gitignore`:** never committed to the repo
- **Invoicing data:** also in `.gitignore`
- **Telegram token:** stored in n8n (encrypted), never in code
