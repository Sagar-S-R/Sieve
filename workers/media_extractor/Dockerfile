FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for PyMuPDF
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip to latest version
RUN pip install --upgrade pip

# Copy requirements and install
COPY workers/media_extractor/requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Copy shared schemas
COPY shared/ /app/shared/

# Copy media_extractor code
COPY workers/media_extractor/ /app/workers/media_extractor/

# Set Python path
ENV PYTHONPATH=/app

CMD ["python", "workers/media_extractor/main.py"]
