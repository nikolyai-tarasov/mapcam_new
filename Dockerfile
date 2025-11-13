FROM python:3.13-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/root/.local/bin:${PATH}"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
    && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --upgrade pip poetry poetry-plugin-export

WORKDIR /app

COPY pyproject.toml poetry.lock* ./

RUN poetry export --without-hashes --format requirements.txt --output requirements.txt \
    && pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/app"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /wheels /wheels
COPY --from=builder /app/requirements.txt ./requirements.txt

RUN pip install --no-cache-dir /wheels/* \
    && rm -rf /wheels

COPY alembic.ini ./alembic.ini
COPY migrations ./migrations
COPY README.md pyproject.toml poetry.lock ./
COPY src ./src

EXPOSE 8000

CMD ["uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "8000"]

