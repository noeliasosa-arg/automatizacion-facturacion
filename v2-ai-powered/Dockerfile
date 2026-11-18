# Dockerfile — contenedor 'facturacion'
# --------------------------------------
# Imagen Python estándar con las librerías que usa el script + Flask para
# el mini-servidor. Parte de python:3.12-slim (imagen oficial, liviana, SIN
# los problemas de la imagen distroless de n8n: acá pip funciona normal).

FROM python:3.12-slim

# Carpeta de trabajo dentro del contenedor.
WORKDIR /app

# Instalar las dependencias. Se copia primero requirements.txt solo para
# aprovechar la cache de Docker: si el código cambia pero las librerías no,
# no se reinstala todo de nuevo.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el mini-servidor al contenedor.
COPY app.py .

# El script consolidar_facturas.py NO se copia acá: vive en la carpeta
# compartida (/data/facturacion), que se monta desde Windows en el
# docker-compose. Así podés editarlo sin reconstruir la imagen.

# Puerto donde escucha el mini-servidor.
EXPOSE 8000

# Comando de arranque: levanta el servidor Flask.
CMD ["python", "app.py"]
