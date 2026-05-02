FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for curl_cffi
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY config.json .
COPY sha3_wasm_bg.7b9ca65ddd.wasm .
COPY templates/ templates/

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
