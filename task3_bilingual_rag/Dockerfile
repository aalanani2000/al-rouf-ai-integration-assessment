FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY documents/ ./documents/

RUN mkdir -p /data

EXPOSE 8001

ENV RAG_INDEX_CACHE=/data/embeddings_cache.json

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
