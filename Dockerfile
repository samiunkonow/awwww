# Usa una imagen oficial de Python 3.12 como base
FROM python:3.12-slim

# Establece el directorio de trabajo en /app
WORKDIR /app

# Copia los archivos del proyecto a /app
COPY . .

# Actualiza e instala FFmpeg y otras dependencias necesarias
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Instala las dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Expone el puerto necesario (Railway maneja esto automáticamente)
EXPOSE 8080

# Comando para ejecutar el bot
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]