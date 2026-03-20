FROM python:3.14-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

ENV POETRY_VERSION=2.3.2
RUN pip install --no-cache-dir poetry==$POETRY_VERSION

WORKDIR /app

COPY graph/pyproject.toml /app/graph/
COPY graph/poetry.lock /app/graph/poetry.lock

COPY parser/pyproject.toml /app/parser/
COPY parser/poetry.lock /app/parser/poetry.lock

COPY ecosystem_analyzer/pyproject.toml /app/ecosystem_analyzer/
COPY ecosystem_analyzer/poetry.lock /app/ecosystem_analyzer/poetry.lock

RUN poetry -C /app/graph config virtualenvs.create false \
    && poetry -C /app/graph install --only main --no-root

RUN poetry -C /app/parser config virtualenvs.create false \
    && poetry -C /app/parser install --only main --no-root

RUN poetry -C /app/ecosystem_analyzer config virtualenvs.create false \
    && poetry -C /app/ecosystem_analyzer install --only main --no-root

COPY graph /app/graph
COPY parser /app/parser
COPY ecosystem_analyzer /app/ecosystem_analyzer

RUN poetry -C /app/ecosystem_analyzer install --only main --no-root

EXPOSE 8000

CMD ["uvicorn", "ecosystem_analyzer.main:app", "--host", "0.0.0.0", "--port", "8000"]