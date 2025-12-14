FROM python:3.12-slim

# Install system dependencies for psycopg2
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .
COPY healthcheck.py .

HEALTHCHECK --interval=10m --timeout=20s --start-period=10m --retries=3 \
  CMD ["python", "-u", "healthcheck.py"]

CMD ["python", "-u", "main.py"]
