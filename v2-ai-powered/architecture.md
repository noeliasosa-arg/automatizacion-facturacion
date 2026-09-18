# Arquitectura del Sistema — V1 vs V2

Documentación técnica comparativa de ambas versiones del sistema de automatización de facturación.

## Resumen

| | V1 Baseline | V2 AI-Powered |
|--|------------|---------------|
| Lanzamiento | 2025 | 2026 |
| Stack | Python, n8n, Docker | Python, Claude, n8n, Docker |
| Entrada | XLS estructurado | XLS + PDF escaneados |
| Extracción | Lectura directa de celdas | LLM + Prompt Engineering |
| Validación | NaN, duplicados | LLM self-check + correcciones |
| Idempotente | ✓ | ✓ |
| Notificaciones | Telegram | Telegram |
| Manejo de errores | Error workflow n8n | Error workflow n8n |

---

## V1 — Arquitectura Baseline

```
Windows (host)
└── Carpeta "Facturacion 2025"
    ├── subdiarios/     (.XLS exportados de SINET)
    ├── comprobantes/   (.XLS por comprobante)
    └── planilla base   (.xlsx formato AFIP)
         │
         ▼
┌─────────────────────────────────────────────┐
│  docker-compose                              │
│                                             │
│  ┌──────────┐  HTTP POST /run  ┌──────────┐ │
│  │   n8n    │ ──────────────> │  Python  │ │
│  │          │ <────────────── │ (Flask)  │ │
│  │ Schedule │  JSON resumen   │          │ │
│  │ Trigger  │                 │ pandas   │ │
│  │          │                 │ openpyxl │ │
│  │ Telegram │                 │ xlrd     │ │
│  └──────────┘                 └──────────┘ │
└─────────────────────────────────────────────┘
         │
         ▼
   planilla_anual.xlsx
```

### Flujo V1

1. **Schedule Trigger** (n8n) — se activa una vez al mes
2. **HTTP Request** (n8n) — llama a `POST /run`
3. **consolidar_facturas.py** — lee subdiarios, cruza con comprobantes
4. **pandas** — consolida, ordena, detecta duplicados
5. **openpyxl** — escribe en planilla AFIP
6. **Telegram** (n8n) — notifica resultado

---

## V2 — Arquitectura AI-Powered

```
Windows (host)
└── Carpeta "Facturacion 2025"
    ├── subdiarios/     (.XLS exportados de SINET)
    ├── comprobantes/   (.XLS por comprobante)
    ├── PDFs/           (facturas escaneadas) ← NUEVO
    └── planilla base   (.xlsx formato AFIP)
         │
         ▼
┌──────────────────────────────────────────────────────┐
│  docker-compose                                       │
│                                                      │
│  ┌──────────┐  POST /extract   ┌───────────────────┐ │
│  │   n8n    │ ───────────────> │    Python (V2)    │ │
│  │          │ <─────────────── │                   │ │
│  │ Schedule │  JSON extraído   │  prompt_extractor │ │
│  │ Trigger  │                  │  ┌─────────────┐  │ │
│  │          │  POST /run       │  │  Claude API │  │ │
│  │ Telegram │ ───────────────> │  │  (Anthropic)│  │ │
│  └──────────┘ <─────────────── │  └──────┬──────┘  │ │
│               JSON resumen     │         │         │ │
│                                │  pandas + openpyxl│ │
│                                └───────────────────┘ │
└──────────────────────────────────────────────────────┘
         │                              │
         ▼                              ▼
   planilla_anual.xlsx          Claude API (externas)
                               Extracción + Validación
```

### Flujo V2

1. **Schedule Trigger** (n8n) — se activa una vez al mes
2. **HTTP Request** a `/extract` (n8n) — envía texto de facturas escaneadas
3. **prompt_extractor.py** (Python) — pipeline de 3 pasos con Claude:
   - **Extracción:** prompt estructurado → JSON con datos
   - **Validación:** Claude valida aritmética y campos críticos
   - **Preparación:** adapta al formato de consolidación
4. **HTTP Request** a `/run` (n8n) — consolida todo
5. **consolidar_facturas.py** — procesa datos estructurados + V1
6. **Telegram** (n8n) — notifica resultado completo

---

## Prompt Engineering — Detalle Técnico

V2 usa 3 prompts distintos, cada uno para un propósito específico:

### Prompt 1: Extracción

```
CRITICAL: You MUST respond ONLY with valid JSON, nothing else.
No preamble, no explanation, no markdown code blocks — just the JSON object.

Extract the following fields:
- invoice_date: fecha de la factura (formato YYYY-MM-DD)
- invoice_number: número de comprobante
...
If a field is not found or unclear, use null.
Quantities and amounts must be numbers, not strings.
```

**Técnicas usadas:**
- Instrucción explícita de formato (`ONLY valid JSON`)
- Negación de comportamientos no deseados (`no preamble, no explanation`)
- Tipos de dato explícitos (`must be numbers, not strings`)
- Valor para campo ausente (`use null`)

### Prompt 2: Validación

```
Check for:
1. Arithmetic errors (net_total + tax_total should equal total_amount)
2. Invalid dates
3. Missing critical fields
4. Unrealistic values (negative amounts, etc.)

Respond ONLY with JSON in this format:
{"is_valid": true/false, "errors": [...], "corrected_fields": {...}}
```

**Técnicas usadas:**
- Checklist explícita de validaciones
- Schema forzado en el output
- Self-check (Claude valida su propia extracción)

### Prompt 3: Consolidación

```
Given the extracted invoice data below, prepare it for consolidation
into an Argentine tax authority (AFIP) format spreadsheet.
```

**Técnicas usadas:**
- Contexto del dominio (AFIP, Argentina)
- Instrucciones específicas del negocio

---

## Decisiones de Diseño

### ¿Por qué dos llamadas a Claude (extracción + validación)?

Un solo prompt que extraiga y valide a la vez tiende a hacer trade-offs silenciosos. Separar los pasos:
- Permite detectar errores del primer paso
- Mejora la trazabilidad (sabés exactamente qué falló)
- Permite corregir sin re-extraer

### ¿Por qué no reemplazar V1 completamente?

V1 es más rápido y más barato para subdiarios ya digitalizados (no hay llamadas a la API). V2 agrega capacidad para fuentes irregulares sin quitar lo que ya funciona. Coexisten en el mismo contenedor.

### ¿Por qué Flask en lugar de FastAPI?

Flask es más simple y ya estaba en V1. Para este caso de uso (pocos endpoints, sin async masivo) es suficiente. Migrar a FastAPI sería la siguiente iteración si el volumen de requests aumenta.

---

## Costos Estimados

| Acción | Tokens estimados | Costo aproximado |
|--------|-----------------|------------------|
| Extracción (1 factura) | ~500 tokens | $0.001 |
| Validación (1 factura) | ~300 tokens | $0.0006 |
| Por lote mensual (237 facturas) | ~190,000 tokens | $0.38 |

*Precios estimados con Claude claude-sonnet-4. Actualizar según plan actual.*

---

## Seguridad

- **API Key:** nunca hardcodeada. Siempre por variable de entorno o `.env`
- **`.env` en `.gitignore`:** nunca sube al repo
- **Datos de facturación:** también en `.gitignore`
- **Token de Telegram:** guardado en n8n (encriptado), nunca en código
