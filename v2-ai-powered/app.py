"""
app.py
------
Mini-servidor que ejecuta consolidar_facturas.py cuando n8n se lo pide.

Vive dentro del contenedor 'facturacion'. n8n (en su propio contenedor) le
pega un HTTP POST a /run y este servidor:
  1. Ejecuta consolidar_facturas.py en la carpeta compartida.
  2. Captura toda su salida de texto (los print del script).
  3. Devuelve un JSON con: ok (bool), salida (texto), y codigo de salida.

n8n usa ese JSON para armar la notificación de Telegram.

Endpoints:
  GET  /health  -> chequeo simple ("estoy vivo"), sirve para probar la conexión.
  POST /run     -> corre el script y devuelve el resultado.
"""

import subprocess
import sys
from flask import Flask, jsonify

app = Flask(__name__)

# Carpeta compartida (se monta en el docker-compose). Es donde viven el script,
# la planilla base y las carpetas subdiarios/ y comprobantes/.
CARPETA = "/data/facturacion"
SCRIPT = "consolidar_facturas.py"


@app.get("/health")
def health():
    """Chequeo simple para verificar que el servidor responde."""
    return jsonify({"estado": "ok"}), 200


@app.post("/run")
def run():
    """Ejecuta el script de consolidación y devuelve su salida."""
    try:
        proc = subprocess.run(
            [sys.executable, SCRIPT],
            cwd=CARPETA,            # corre parado en la carpeta compartida
            capture_output=True,    # captura stdout y stderr
            text=True,              # como texto, no bytes
            timeout=600,            # 10 min de tope por si algo se cuelga
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


if __name__ == "__main__":
    # Escucha en todas las interfaces para que n8n (otro contenedor) lo alcance.
    app.run(host="0.0.0.0", port=8000)
