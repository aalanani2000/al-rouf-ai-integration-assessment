FROM python:3.12-slim

WORKDIR /app

# Install dependencies first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Data directory for SQLite persistence (mount a volume here in production)
RUN mkdir -p /data

EXPOSE 8000

ENV QUOTES_DB_PATH=/data/quotes.db

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
