FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md install_model.py ./
COPY intelbrief ./intelbrief
COPY manifests ./manifests
COPY ui ./ui

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

ENV LLM_BACKEND=ollama \
    OLLAMA_BASE_URL=http://ollama:11434/v1 \
    LLM_MODEL=llama3.2 \
    API_HOST=0.0.0.0 \
    API_PORT=8000

EXPOSE 8000 8501

CMD ["python", "-m", "intelbrief"]
