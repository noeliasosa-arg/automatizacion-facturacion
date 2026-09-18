# Dockerfile — contenedor 'facturacion' V2 AI-Powered
# ---------------------------------------------------------
# Igual que V1 pero con la librería de Anthropic (Claude) incluida.
# La API key se pasa como variable de entorno en docker-compose,
# nunca se hardcodea en la imagen.

FROM python:3.12-slim

WORKDIR /app

# Instalar dependencias (incluyendo anthropic SDK para Claude)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar archivos del servidor y extractor
COPY app_v2.py app.py
COPY prompt_extractor.py .
COPY prompt_extractor_config.py .

# El script consolidar_facturas.py vive en la carpeta compartida
# (/data/facturacion), no en la imagen. Así podés editarlo sin
# reconstruir la imagen.

EXPOSE 8000

CMD ["python", "app.py"]
