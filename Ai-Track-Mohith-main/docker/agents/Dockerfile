FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc curl && \
    rm -rf /var/lib/apt/lists/*

COPY hirelogic_agent/requirements.txt ./
COPY hirelogic_agent/ .

RUN pip install --no-cache-dir \
    google-adk[eval] \
    python-dotenv \
    httpx \
    pytest \
    pytest-asyncio && \
    pip install --no-cache-dir -r requirements.txt

CMD ["python", "backend_chat.py"]
