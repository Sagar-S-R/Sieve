FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install
COPY api_gateway/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy api_gateway code and shared module
COPY api_gateway/ /app/api_gateway/
COPY shared/ /app/shared/

# Set Python path
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8000

CMD ["uvicorn", "api_gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]
