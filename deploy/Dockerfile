FROM python:3.11-slim

RUN useradd --create-home --uid 10001 jaadu
WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY config ./config
COPY frontend ./frontend

# Do not COPY data/: local parquet and registry must not enter the image.
RUN mkdir -p data/raw data/processed data/registry experiments/results \
    && pip install --no-cache-dir -e . \
    && chown -R jaadu:jaadu /app

ENV JAADU_HOST=0.0.0.0 \
    JAADU_PORT=8000 \
    PYTHONUNBUFFERED=1 \
    JAADU_VERTEX_BASELINE=0 \
    PYTHONDONTWRITEBYTECODE=1

USER jaadu
EXPOSE 8000
CMD ["python", "-m", "jaadu", "serve", "--host", "0.0.0.0", "--port", "8000"]
