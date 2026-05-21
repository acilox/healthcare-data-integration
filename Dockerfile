FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev libaio1 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN pip install --upgrade pip && pip install --prefix=/install .

FROM python:3.11-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 libaio1 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1000 clinical_etl \
    && useradd --uid 1000 --gid clinical_etl --shell /bin/bash --create-home clinical_etl

WORKDIR /app
COPY --from=builder /install /usr/local
COPY --chown=clinical_etl:clinical_etl src/ ./src/
COPY --chown=clinical_etl:clinical_etl data/sample/ ./data/sample/

USER clinical_etl
ENTRYPOINT ["python", "-m", "clinical_etl.main"]
CMD ["--help"]
