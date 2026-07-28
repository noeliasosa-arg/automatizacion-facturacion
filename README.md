# Invoicing Consolidation Automation

An unattended automation system that consolidates monthly invoicing records, integrating a Python processing script with a workflow orchestrator (n8n) through a decoupled container architecture.

## The problem

A company's monthly invoicing consolidation was done by hand: opening each sales subledger, locating each individual invoice file, copying its line items (description, quantity, price, VAT) into the annual spreadsheet, and sorting everything by date. A monthly batch meant **3 to 4 hours of manual work** — repetitive and prone to transcription errors.

## The solution

A system that, automatically once a month:

1. **Reads** all sales subledgers for the period.
2. **Matches** each invoice with its detail file (`.XLS` exported from the management system).
3. **Consolidates** everything into the annual spreadsheet, preserving the official AFIP (Argentine tax authority) format.
4. **Notifies** a summary via Telegram: invoices processed, line items added, missing invoices, and credit/debit notes requiring manual attention.

The user doesn't intervene: they drop the month's files into a folder and receive the result on their phone.

## Architecture

The system uses **two decoupled Docker containers** communicating over Docker's internal network:

```
┌─────────────────────────────────────────────────────────────┐
│                      docker-compose                          │
│                                                              │
│   ┌──────────────────┐   HTTP POST    ┌───────────────────┐  │
│   │       n8n        │  /run          │   facturacion     │  │
│   │  (orchestrator)  │ ─────────────> │  (Python service) │  │
│   │                  │                │                   │  │
│   │ • Schedule       │ <───────────── │ • Flask (app.py)  │  │
│   │   Trigger        │   JSON summary │ • consolidar_     │  │
│   │ • HTTP Request   │                │   facturas.py     │  │
│   │ • Telegram       │                │ • pandas/openpyxl │  │
│   └────────┬─────────┘                └─────────┬─────────┘  │
│            │                                    │            │
│            └──────────────┬─────────────────────┘            │
│                           │                                  │
│                Shared folder (volume)                        │
│         subledgers/  ·  invoices/  ·  spreadsheet            │
└─────────────────────────────────────────────────────────────┘
```

**Why two containers instead of one?** The official n8n image (v2) is *distroless*: by security design, it ships without a package manager and doesn't allow installing dependencies like Python or pandas. Rather than forcing the installation with fragile hacks, the processing logic was separated into its own standard Python container. This follows the **separation of concerns** principle: n8n orchestrates, Python processes, and each component uses its ideal image. The result is more maintainable and more resilient to updates.

## Components

| File | Role |
|------|------|
| `consolidar_facturas.py` | Processing engine: reads subledgers and invoices, consolidates into the annual spreadsheet. |
| `app.py` | Flask micro-service exposing the script over HTTP (`/health`, `/run`). |
| `Dockerfile` | Builds the Python container with dependencies (pandas, openpyxl, xlrd, flask). |
| `docker-compose.yml` | Orchestrates both containers, the internal network, and the shared volume. |
| n8n workflow | Schedule Trigger → HTTP Request → Telegram notification, with an associated error workflow. |

## Expected data structure

> **Note:** this repository does not include real invoicing data for privacy reasons. The structure the system expects is documented below.

The script works on three inputs, located alongside it:

```
project/
├── consolidar_facturas.py
├── <base-spreadsheet>.xlsx   # annual spreadsheet (official AFIP format)
├── subdiarios/               # .XLS monthly sales subledgers
└── comprobantes/             # .XLS of each individual invoice
```

- **Base spreadsheet:** annual spreadsheet in official AFIP format, sheet `FACTURACION`, 25 columns (group, date, invoice type, point of sale, number, tax ID, client, total, currency, exchange rate, allocation, authorization type, CAE, item code, description, quantity, price, net, VAT, item total, etc.). Can start empty (official downloadable AFIP template) or already populated.
- **Subledgers (`subdiarios/`):** `.XLS` files exported from the management system, one per month, containing each invoice's header (date, type, point of sale, number, tax ID, client, total, CAE).
- **Invoices (`comprobantes/`):** one `.XLS` per invoice, named by its fiscal identification (e.g. `FACTURA NÚMERO A 0003-00003396.XLS`), with the line-item detail (description, quantity, net, VAT).

**Output:** `planilla_anual.xlsx` — the base spreadsheet with all invoices consolidated and sorted by date.

## Key technical decisions

**Idempotency.** The process can be re-run without duplicating data. The script detects already-loaded invoices (via a normalized key of type/point-of-sale/number, robust to formatting differences in cells) and skips what already exists, adding only what's new. This makes the system safe to re-run after failures or repeated executions.

**Resilience to incomplete data.** If an invoice is missing its detail file, or an item has missing values (empty net/VAT), the system doesn't silently corrupt the spreadsheet: it loads the header, flags the missing item, and reports it in the notification for manual review.

**Production-grade error handling.** A dedicated error workflow sends a Telegram alert if any run fails, indicating which workflow failed and the error message. The system never fails silently.

**Trigger/process coherence.** The schedule was set to monthly to align with the real invoicing cycle, avoiding unnecessary empty runs.

## Impact

- **Estimated savings:** 3 hours per monthly consolidation.
- **Reduced** manual transcription errors.
- **Traceability:** every run leaves a record and a summary notification.

## Stack

Python (pandas, openpyxl, xlrd) · Flask · Docker · Docker Compose · n8n · Telegram Bot API

## Possible future improvements

- **Incremental processing** to scale to large volumes: process only new subledgers instead of re-reading everything (e.g., archiving already-consolidated files).
- **Event-based trigger** (new-file detection) as an alternative to the schedule.
- Support for export credit/debit notes (currently documented as a known limitation in the code).
