FROM python:3.14-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

ENV POETRY_VERSION=2.3.2
RUN pip install --no-cache-dir poetry==$POETRY_VERSION

WORKDIR /app

COPY pyproject.toml poetry.lock ./

RUN poetry config virtualenvs.create false \
    && poetry install --only main --no-root

COPY . ./ecosystem_analyzer

EXPOSE 8000

CMD ["uvicorn", "ecosystem_analyzer.main:app", "--host", "0.0.0.0", "--port", "8000"]