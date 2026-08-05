FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install
COPY workers/cron_notifier/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy cron_notifier code
COPY shared/ /app/shared/
COPY workers/cron_notifier/ /app/workers/cron_notifier/

# Set Python path
ENV PYTHONPATH=/app

CMD ["python", "workers/cron_notifier/main.py"]
