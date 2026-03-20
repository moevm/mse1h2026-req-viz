FROM python:3.14-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

ENV POETRY_VERSION=2.3.2
RUN pip install --no-cache-dir poetry==$POETRY_VERSION

WORKDIR /app

COPY graph /app/graph

COPY ecosystem_analyzer/pyproject.toml ecosystem_analyzer/poetry.lock /app/ecosystem_analyzer/

RUN poetry -C /app/ecosystem_analyzer config virtualenvs.create false \
    && poetry -C /app/ecosystem_analyzer install --only main --no-root

COPY ecosystem_analyzer /app/ecosystem_analyzer

EXPOSE 8000

CMD ["uvicorn", "ecosystem_analyzer.main:app", "--host", "0.0.0.0", "--port", "8000"]