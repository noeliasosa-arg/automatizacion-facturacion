"""
app.py (V2 AI-Powered)

Mini-servidor mejorado que ejecuta consolidar_facturas.py y además ofrece
endpoints para extracción de datos de facturas con Claude.

Vive dentro del contenedor 'facturacion'. n8n (en su propio contenedor) le
pega HTTP POST a los endpoints de este servidor.

Nuevos endpoints en V2:
  POST /extract  -> recibe PDF/texto de factura, devuelve datos extraídos con Claude
  POST /run      -> (igual que v1) ejecuta consolidación completa
  GET  /health   -> chequeo de salud
"""

import subprocess
import sys
import os
import json
from pathlib import Path
from flask import Flask, jsonify, request

# Importar el extractor de facturas (V2)
try:
    from prompt_extractor import InvoiceExtractor
    HAS_EXTRACTOR = True
except ImportError:
    HAS_EXTRACTOR = False
    print("[WARN] prompt_extractor no disponible. Endpoint /extract no funcionará.")

app = Flask(__name__)

# Carpeta compartida (se monta en el docker-compose)
CARPETA = "/data/facturacion"
SCRIPT = "consolidar_facturas.py"

# Inicializar extractor (solo si tenemos API key de Anthropic)
extractor = None
if HAS_EXTRACTOR and os.getenv("ANTHROPIC_API_KEY"):
    try:
        extractor = InvoiceExtractor()
        print("[INFO] InvoiceExtractor inicializado con éxito.")
    except Exception as e:
        print(f"[WARN] No se pudo inicializar InvoiceExtractor: {e}")


@app.get("/health")
def health():
    """Chequeo simple para verificar que el servidor responde."""
    status = {
        "estado": "ok",
        "version": "2.0-ai-powered",
        "extractor_available": HAS_EXTRACTOR and extractor is not None,
    }
    return jsonify(status), 200


@app.post("/extract")
def extract_invoice():
    """
    Extrae datos de una factura (escaneada o texto plano) usando Claude.

    Espera en el body:
    {
      "invoice_text": "texto OCR o datos de la factura",
      "validate": true,
      "prepare_for_consolidation": true
    }

    Devuelve:
    {
      "ok": true/false,
      "extracted": {...datos extraídos...},
      "validation": {...resultado de validación...},
      "consolidated": {...preparado para consolidación...},
      "errors": [...]
    }
    """
    if not extractor:
        return jsonify({
            "ok": False,
            "error": "Extractor no disponible. Verificá que ANTHROPIC_API_KEY esté configurada.",
        }), 503

    try:
        data = request.get_json()
        invoice_text = data.get("invoice_text", "")
        validate = data.get("validate", True)
        prepare = data.get("prepare_for_consolidation", True)

        if not invoice_text:
            return jsonify({"ok": False, "error": "invoice_text es requerido"}), 400

        # Pipeline: extrae → valida → prepara
        result = extractor.extract_validate_prepare(invoice_text)

        return jsonify({
            "ok": result.get("success", False),
            "extracted": result.get("extracted"),
            "validation": result.get("validation") if validate else None,
            "consolidated": result.get("consolidated") if prepare else None,
        }), 200

    except Exception as e:
        return jsonify({
            "ok": False,
            "error": f"Error inesperado: {str(e)}",
        }), 500


@app.post("/run")
def run():
    """
    Ejecuta el script de consolidación (igual que v1).

    Procesa todos los subdiarios y comprobantes en la carpeta compartida.
    Devuelve:
    {
      "ok": true/false,
      "codigo": exit code,
      "salida": texto de salida del script
    }
    """
    try:
        proc = subprocess.run(
            [sys.executable, SCRIPT],
            cwd=CARPETA,
            capture_output=True,
            text=True,
            timeout=600,
        )
        salida = proc.stdout + (("\n[stderr]\n" + proc.stderr) if proc.stderr else "")
        return jsonify({
            "ok": proc.returncode == 0,
            "codigo": proc.returncode,
            "salida": salida.strip(),
        }), 200
    except subprocess.TimeoutExpired:
        return jsonify({
            "ok": False,
            "codigo": -1,
            "salida": "ERROR: el script tardó más de 10 minutos y se canceló.",
        }), 200
    except Exception as e:
        return jsonify({
            "ok": False,
            "codigo": -1,
            "salida": f"ERROR inesperado al ejecutar el script: {e}",
        }), 200


@app.post("/extract-and-consolidate")
def extract_and_consolidate():
    """
    Pipeline V2 completo en un endpoint:
    1. Extrae datos de factura con Claude
    2. Valida
    3. Corre el script de consolidación sobre la carpeta

    Espera:
    {
      "invoice_text": "...",
      "run_consolidation": true
    }

    Devuelve:
    {
      "extraction": {...},
      "consolidation": {...}
    }
    """
    if not extractor:
        return jsonify({
            "ok": False,
            "error": "Extractor no disponible.",
        }), 503

    try:
        data = request.get_json()
        invoice_text = data.get("invoice_text", "")
        run_consolidation = data.get("run_consolidation", False)

        if not invoice_text:
            return jsonify({"ok": False, "error": "invoice_text requerido"}), 400

        # Paso 1: Extrae
        extraction = extractor.extract_validate_prepare(invoice_text)

        result = {
            "ok": extraction.get("success", False),
            "extraction": extraction,
        }

        # Paso 2 (opcional): Corre consolidación si es válido
        if run_consolidation and extraction.get("success"):
            print("[INFO] Extracción exitosa. Ejecutando consolidación...")
            try:
                proc = subprocess.run(
                    [sys.executable, SCRIPT],
                    cwd=CARPETA,
                    capture_output=True,
                    text=True,
                    timeout=600,
                )
                consolidation_output = proc.stdout + (
                    ("\n[stderr]\n" + proc.stderr) if proc.stderr else ""
                )
                result["consolidation"] = {
                    "ok": proc.returncode == 0,
                    "codigo": proc.returncode,
                    "salida": consolidation_output.strip(),
                }
            except Exception as e:
                result["consolidation"] = {
                    "ok": False,
                    "error": f"Error en consolidación: {str(e)}",
                }

        return jsonify(result), 200

    except Exception as e:
        return jsonify({
            "ok": False,
            "error": f"Error: {str(e)}",
        }), 500


if __name__ == "__main__":
    # Escucha en todas las interfaces para que n8n (otro contenedor) lo alcance.
    port = int(os.getenv("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)
