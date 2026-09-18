# Automatización de Consolidación de Facturación

Sistema de automatización que evoluciona desde baseline (v1) a una versión mejorada con IA (v2). Consolida facturación mensual de una empresa para su presentación al Régimen de Incentivo a la Cadena de Valor de Bienes de Capital (Ministerio de Producción, Argentina).

## Quick Start

**Latest: V2 AI-Powered** ✨ — Extracta datos de facturas escaneadas usando Claude + prompt engineering.

**Also available: V1 Baseline** — Automatización tradicional con n8n + Python.

## V1 vs V2 — Comparación

| Aspecto | V1 Baseline | V2 AI-Powered |
|---------|------------|---------------|
| **Entrada de datos** | Subdiarios .XLS (con estructura) | PDFs escaneados + XLS estructurados |
| **Extracción** | Lectura directa de celdas | Claude + Prompt Engineering (JSON output) |
| **Procesamiento** | pandas directo | pandas post-extracción |
| **Stack** | Python, pandas, n8n, Docker | Python, Claude API, n8n, Docker |
| **Caso de uso** | Subdiarios ya digitalizados | Facturas de papel o mal digitalizadas |
| **Impacto** | 3 horas ahorradas/mes | +control sobre fuentes irregulares |

## Estructura del Repo

```
├── v1-baseline/          ← Original (baseline sólida)
│   └── [scripts, docs, docker config]
│
├── v2-ai-powered/        ← NUEVA (con Claude integrado)
│   ├── README.md
│   ├── app.py            (mejorado, integra IA)
│   ├── prompt_extractor.py (NUEVO)
│   ├── config_prompts.py (NUEVO)
│   └── [docker, requirements, ejemplos]
│
└── docs/
    └── architecture.md   (diagramas comparativos)
```

## Empezar con V2

V2 requiere una API key de Anthropic (Claude). Para desarrollo local:

```bash
cd v2-ai-powered
export ANTHROPIC_API_KEY="tu-clave-aqui"
pip install -r requirements.txt
python app.py
```

O con Docker:

```bash
cd v2-ai-powered
docker-compose up
```

## Stack

- **V1:** Python (pandas, openpyxl, xlrd) · Flask · Docker · n8n · Telegram API
- **V2:** Python (pandas, openpyxl, anthropic) · Flask · Docker · n8n · Claude API · Telegram API

## Decisiones Técnicas

**V1 — Separación de contenedores:** n8n (orquestación) + Python (procesamiento) desacoplados en su propia imagen. El problema de la imagen distroless de n8n v2 se resolvió con una arquitectura de dos contenedores, cada uno con su responsabilidad.

**V2 — Extracción inteligente:** Claude se integra como un paso de extracción de datos intermedio. El prompt está estructurado para forzar JSON, garantizando que el output sea parseable por pandas. Esto permite procesar fuentes irregulares (PDFs escaneados, formatos ad-hoc) que v1 no podía manejar.

## Archivos de Entrada

### V1 Baseline
- Subdiarios de ventas (.XLS, formato SINET)
- Archivos de comprobantes (.XLS, uno por factura)
- Planilla base (formato oficial AFIP)

### V2 AI-Powered
- Todo lo de V1 +
- PDFs escaneados de facturas
- Facturas en formatos irregulares

## Impacto

- **V1:** 3 horas de trabajo manual por mes (consolidación limpia)
- **V2:** Extiende capacidad a fuentes sucias; reduce manejo manual de casos irregulares

## Certificaciones & Contexto

Proyecto desarrollado como parte de formación en Automatización de IA y Gestión de Políticas Públicas (UNTREF), con certificaciones en IA de la Universidad de Oxford (Saïd Business School).

## Licencia

MIT. Ver LICENSE.

---

**Para más detalles técnicos:** Ver README individual de cada versión (v1-baseline/README.md, v2-ai-powered/README.md).

**GitHub:** https://github.com/noeliasosa-arg/automatizacion-facturacion
