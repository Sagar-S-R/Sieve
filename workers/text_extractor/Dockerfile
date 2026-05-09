FROM python:3.11-slim

WORKDIR /app

# Upgrade pip first
RUN pip install --upgrade pip

# Copy requirements and install
COPY workers/text_extractor/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared schemas
COPY shared/ /app/shared/

# Copy text_extractor code
COPY workers/text_extractor/ /app/workers/text_extractor/

# Set Python path
ENV PYTHONPATH=/app

CMD ["python", "workers/text_extractor/main.py"]
