# Automatización de Consolidación de Facturación — V2 AI-Powered

Versión mejorada con integración de Claude para extracción inteligente de datos de facturas.

**¿Qué es V2?** Extiende el baseline de V1 agregando un paso de extracción de datos impulsado por IA. Ahora puede procesar facturas escaneadas (PDFs con OCR) y facturas con formatos irregulares, extrayendo datos estructurados con Claude antes de consolidarlas.

## Arquitectura V2

```
┌──────────────────────────────────────────────────────────────────┐
│                      docker-compose                               │
│                                                                   │
│  ┌────────────────┐   POST /extract   ┌──────────────────────┐  │
│  │       n8n      │  ────────────────> │   facturacion (v2)   │  │
│  │ (orquestador)  │                   │                      │  │
│  │                │   POST /run        │ • Flask (app_v2.py) │  │
│  │ • Schedule     │  ────────────────> │ • prompt_extractor  │  │
│  │   Trigger      │  <────────────────  │   (Claude)          │  │
│  │ • HTTP         │   JSON con datos  │ • consolidar_       │  │
│  │   Request      │                   │   facturas.py        │  │
│  │ • Telegram     │                   │ • pandas/openpyxl   │  │
│  └────────┬───────┘                   └──────────┬──────────┘  │
│           │                                      │              │
│           └──────────────┬───────────────────────┘              │
│                          │                                      │
│             Carpeta compartida (volumen)                        │
│     subdiarios/ · comprobantes/ · PDFs/ · planilla             │
└──────────────────────────────────────────────────────────────────┘
         │
         └─> Claude API (prompt engineering + JSON extraction)
```

## Flujo de Datos — V2

**Entrada:** Facturas en múltiples formatos
- Subdiarios `.XLS` estructurados (V1 completo)
- PDFs escaneados de facturas (NUEVO)
- Texto OCR de facturas irregulares (NUEVO)

**Paso 1: Extracción (Claude + Prompt Engineering)**
- El texto de factura llega a `prompt_extractor.py`
- Claude recibe un **prompt estructurado** diseñado para extraer campos específicos
- El prompt **fuerza output en JSON** usando instrucciones explícitas
- Resultado: JSON con estructura garantizada {fecha, número, cliente, items, totales, etc.}

**Paso 2: Validación (Claude)**
- El JSON extraído se valida con otro prompt
- Verifica aritmética (neto + IVA = total)
- Detecta datos faltantes o imposibles
- Devuelve correcciones sugeridas

**Paso 3: Procesamiento (Python + Pandas)**
- Los datos validados entran al pipeline de consolidación (V1)
- Se unifican con subdiarios ya digitalizados
- Se escriben en la planilla final AFIP

**Salida:** Planilla `planilla_anual.xlsx` lista para presentación

## Endpoints HTTP — V2

### `POST /extract`
Extrae datos de una factura usando Claude.

**Request:**
```json
{
  "invoice_text": "Texto OCR o datos de factura escaneada",
  "validate": true,
  "prepare_for_consolidation": true
}
```

**Response:**
```json
{
  "ok": true,
  "extracted": {
    "invoice_date": "2025-07-15",
    "invoice_number": "00003396",
    "point_of_sale": "0004",
    "customer_name": "BASF ARGENTINA SA",
    "line_items": [...],
    "total_amount": 12100.0,
    ...
  },
  "validation": {
    "is_valid": true,
    "errors": [],
    "warnings": [],
    "corrected_fields": {}
  },
  "consolidated": {...ready for consolidation...}
}
```

### `POST /run`
Ejecuta la consolidación completa (V1).

**Response:**
```json
{
  "ok": true,
  "codigo": 0,
  "salida": "✓ Listo. Archivo guardado como: planilla_anual.xlsx\n..."
}
```

### `POST /extract-and-consolidate`
Pipeline completo: extrae → valida → consolida.

**Request:**
```json
{
  "invoice_text": "...",
  "run_consolidation": true
}
```

**Response:**
```json
{
  "ok": true,
  "extraction": {...resultado de extracción...},
  "consolidation": {...resultado de consolidación...}
}
```

### `GET /health`
Chequeo de salud del servicio.

**Response:**
```json
{
  "estado": "ok",
  "version": "2.0-ai-powered",
  "extractor_available": true
}
```

## Decisiones Técnicas — V2

### Prompts Estructurados

El corazón de V2 es el **prompt engineering estructurado**. Los prompts están diseñados para:

1. **Forzar formato JSON:** "Respond ONLY with valid JSON, nothing else."
2. **Especificar campos exactos:** Listar qué se busca (invoice_date, number, items, etc.)
3. **Instrucciones claras:** "If a field is not found, use null."
4. **Definir tipos:** "Quantities and amounts must be numbers, not strings."

Esto garantiza que Claude devuelva **JSON parseable**, eliminando la fragilidad del procesamiento de lenguaje natural.

### Validación en Dos Pasos

- **Paso 1 (Extracción):** Claude saca los datos
- **Paso 2 (Validación):** Claude valida sus propios datos

El segundo paso es crítico: detecta aritmética inconsistente, campos faltantes, valores imposibles. Esto es un **self-check que mejora la confiabilidad**.

### Integración con V1

V2 **no reemplaza** a V1; lo **complementa**. Los datos extraídos por Claude entran en el mismo pipeline de consolidación de V1. Beneficios:

- Puedes procesar facturas de múltiples orígenes (subdiarios digitalizados + PDFs escaneados)
- La lógica de deduplicación, idempotencia y validación de V1 sigue funcionando
- Migrración suave: agrega V2 sin romper V1

## Stack — V2

- **Python:** pandas (transformación), openpyxl (escritura AFIP)
- **Claude API:** anthropic SDK para integración de LLM
- **Flask:** micro-servidor HTTP
- **Docker & Docker Compose:** orquestación de contenedores
- **n8n:** orquestación de workflows

## Cómo Usar — Local Development

### 1. Clonar y preparar

```bash
cd v2-ai-powered
python -m venv venv
source venv/bin/activate  # o `venv\Scripts\activate` en Windows
pip install -r requirements.txt
```

### 2. Configurar Claude

```bash
export ANTHROPIC_API_KEY="tu-clave-aqui"
```

### 3. Ejecutar localmente

```bash
python app_v2.py
```

Servidor corriendo en `http://localhost:8000`.

### 4. Probar endpoint

```bash
curl -X POST http://localhost:8000/extract \
  -H "Content-Type: application/json" \
  -d '{
    "invoice_text": "FACTURA 0004-00003396, Cliente: BASF, Total: $12100",
    "validate": true
  }'
```

## Con Docker

```bash
docker-compose up --build
```

El servicio estará en `http://facturacion:8000` (accesible desde n8n).

## Archivos de Ejemplo

En `examples/`:
- `invoice_sample.pdf` — Factura escaneada de ejemplo
- `extracted_output.json` — Salida esperada de extracción
- `workflow_v2.json` — Workflow de n8n lista para importar

## Comparación: V1 vs V2

| Aspecto | V1 | V2 |
|---------|----|----|
| **Entrada** | XLS estructurado | XLS + PDF escaneados + texto OCR |
| **Extracción** | Lectura de celdas | Claude + Prompts |
| **Validación** | Mínima (NaN, duplicados) | Claude validation con autocorrección |
| **Casos de uso** | Subdiarios limpios | Facturas de múltiples orígenes |
| **Tiempo de ejecución** | < 1 seg | 2-5 seg (llamadas a Claude) |
| **Costo** | Nada (local) | ~ $0.001-0.01 por factura (API Claude) |

## Impacto Empresarial

- **V1 ahorro:** 3 horas/mes (datos limpios)
- **V2 ahorro:** +manejo de casos irregulares (PDFs, OCR), menos trabajo manual de corrección

V2 es ideal para empresas que reciben facturas de proveedores en múltiples formatos.

## Próximos Pasos

1. **Batch processing:** Procesar múltiples PDFs en paralelo
2. **RAG (Retrieval-Augmented Generation):** Integrar con historial de facturas para contexto mejorado
3. **Fine-tuning:** Entrenar un modelo específico para facturas argentinas
4. **WebUI:** Interface visual para uploads y revisión de datos extraídos

## Licencia

MIT. Ver LICENSE en la raíz del repo.

---

**¿Preguntas?** Ver README.md en la raíz del repo para contexto general y V1.

**GitHub:** https://github.com/noeliasosa-arg/automatizacion-facturacion
