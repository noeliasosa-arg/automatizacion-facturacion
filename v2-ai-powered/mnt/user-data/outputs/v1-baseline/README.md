# Automatización de Consolidación de Facturación

Sistema de automatización que consolida comprobantes de facturación mensual de forma desatendida, integrando un script de procesamiento en Python con un orquestador de workflows (n8n) mediante una arquitectura de contenedores desacoplados.

## El problema

La consolidación mensual de facturación de una empresa se hacía a mano: abrir cada subdiario de ventas, buscar el archivo de cada comprobante individual, copiar sus ítems (descripción, cantidad, precio, IVA) a la planilla anual, y ordenar todo por fecha. Un lote mensual representaba **3 a 4 horas de trabajo manual**, repetitivo y propenso a errores de transcripción.

## La solución

Un sistema que, una vez al mes de forma automática:

1. **Lee** todos los subdiarios de ventas del período.
2. **Cruza** cada comprobante con su archivo de detalle (`.XLS` exportados del sistema de gestión).
3. **Consolida** todo en la planilla anual, respetando el formato oficial de AFIP.
4. **Notifica** por Telegram un resumen: comprobantes procesados, ítems agregados, comprobantes faltantes y notas de crédito/débito que requieren atención manual.

El usuario no interviene: deja los archivos del mes en una carpeta y recibe el resultado en el teléfono.

## Arquitectura

El sistema usa **dos contenedores Docker desacoplados** que se comunican por la red interna de Docker:

```
┌─────────────────────────────────────────────────────────────┐
│                      docker-compose                          │
│                                                              │
│   ┌──────────────────┐   HTTP POST    ┌───────────────────┐  │
│   │       n8n        │  /run          │   facturacion     │  │
│   │  (orquestador)   │ ─────────────> │  (servicio Python)│  │
│   │                  │                │                   │  │
│   │ • Schedule       │ <───────────── │ • Flask (app.py)  │  │
│   │   Trigger        │   JSON resumen │ • consolidar_     │  │
│   │ • HTTP Request   │                │   facturas.py     │  │
│   │ • Telegram       │                │ • pandas/openpyxl │  │
│   └────────┬─────────┘                └─────────┬─────────┘  │
│            │                                    │            │
│            └──────────────┬─────────────────────┘            │
│                           │                                  │
│               Carpeta compartida (volumen)                   │
│         subdiarios/  ·  comprobantes/  ·  planilla           │
└─────────────────────────────────────────────────────────────┘
```

**¿Por qué dos contenedores en vez de uno?** La imagen oficial de n8n (v2) es *distroless*: no incluye gestor de paquetes ni permite instalar dependencias como Python o pandas, por diseño de seguridad. En lugar de forzar la instalación con hacks frágiles, se separó la lógica de procesamiento en su propio contenedor Python estándar. Esto sigue el principio de **separación de responsabilidades**: n8n orquesta, Python procesa, y cada componente usa su imagen idónea. El resultado es más mantenible y más robusto ante actualizaciones.

## Componentes

| Archivo | Rol |
|---------|-----|
| `consolidar_facturas.py` | Motor de procesamiento: lee subdiarios y comprobantes, consolida en la planilla anual. |
| `app.py` | Micro-servicio Flask que expone el script vía HTTP (`/health`, `/run`). |
| `Dockerfile` | Construye el contenedor Python con las dependencias (pandas, openpyxl, xlrd, flask). |
| `docker-compose.yml` | Orquesta ambos contenedores, la red interna y el volumen compartido. |
| Workflow n8n | Schedule Trigger → HTTP Request → Notificación Telegram, con workflow de errores asociado. |

## Estructura de datos esperada

> **Nota:** este repositorio no incluye datos reales de facturación por privacidad. A continuación se documenta la estructura que el sistema espera.

El script trabaja sobre tres entradas, ubicadas junto a él:

```
proyecto/
├── consolidar_facturas.py
├── <planilla-base>.xlsx      # planilla anual (formato oficial AFIP)
├── subdiarios/               # .XLS de los subdiarios de ventas mensuales
└── comprobantes/             # .XLS de cada comprobante individual
```

- **Planilla base:** planilla anual con formato oficial de AFIP, hoja `FACTURACION`, 25 columnas (grupo, fecha, tipo de comprobante, punto de venta, número, CUIT, cliente, total, moneda, tipo de cambio, imputación, tipo de autorización, CAE, código de artículo, descripción, cantidad, precio, neto, IVA, total del ítem, etc.). Puede partir vacía (plantilla oficial descargable de AFIP) o ya iniciada.
- **Subdiarios (`subdiarios/`):** archivos `.XLS` exportados del sistema de gestión, uno por mes, con las cabeceras de cada comprobante (fecha, tipo, punto de venta, número, CUIT, cliente, total, CAE).
- **Comprobantes (`comprobantes/`):** un `.XLS` por comprobante, nombrado por su identificación fiscal (ej. `FACTURA NÚMERO A 0003-00003396.XLS`), con el detalle de ítems (descripción, cantidad, neto, IVA).

**Salida:** `planilla_anual.xlsx` — la planilla base con todos los comprobantes consolidados y ordenados por fecha.

## Decisiones técnicas destacadas

**Idempotencia.** El proceso puede re-ejecutarse sin duplicar datos. El script detecta los comprobantes ya cargados (mediante una clave normalizada tipo/punto-de-venta/número, robusta ante diferencias de formato en las celdas) y omite lo que ya existe, agregando solo lo nuevo. Esto hace que el sistema sea seguro de re-ejecutar ante fallos o corridas repetidas.

**Robustez ante datos incompletos.** Si un comprobante no tiene su archivo de detalle, o si un ítem tiene valores faltantes (neto/IVA vacío), el sistema no corrompe la planilla silenciosamente: carga la cabecera, marca el faltante, y lo reporta en la notificación para revisión manual.

**Manejo de errores en producción.** Un workflow de errores dedicado envía una alerta por Telegram si alguna corrida falla, indicando qué workflow falló y el mensaje de error. El sistema nunca falla en silencio.

**Coherencia trigger/proceso.** El schedule se configuró mensual para alinearse con el ciclo real de facturación, evitando ejecuciones innecesarias en vacío.

## Impacto

- **Ahorro estimado:** 3 horas por consolidación mensual.
- **Reducción de errores** de transcripción manual.
- **Trazabilidad:** cada corrida deja un registro y una notificación con el resumen.

## Stack

Python (pandas, openpyxl, xlrd) · Flask · Docker · Docker Compose · n8n · Telegram Bot API

## Posibles mejoras a futuro

- **Procesamiento incremental** para escalar a grandes volúmenes: procesar solo los subdiarios nuevos en lugar de releer todo (por ejemplo, archivando los ya consolidados).
- **Trigger por evento** (detección de archivo nuevo) como alternativa al schedule.
- Soporte para notas de crédito/débito de exportación (actualmente documentado como limitación conocida en el código).
