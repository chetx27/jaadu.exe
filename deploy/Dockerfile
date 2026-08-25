FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY config ./config
COPY frontend ./frontend
COPY data ./data
RUN pip install --no-cache-dir -e .
ENV JAADU_HOST=0.0.0.0 JAADU_PORT=8000
EXPOSE 8000
CMD ["python", "-m", "jaadu", "serve", "--host", "0.0.0.0", "--port", "8000"]
