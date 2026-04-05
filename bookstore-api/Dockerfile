FROM python:3.12-slim AS builder

WORKDIR /build
RUN pip install hatchling
COPY pyproject.toml .
RUN pip install --no-cache-dir --prefix=/install ".[dev]" 2>/dev/null || true
COPY pyproject.toml README.md ./
COPY app/ ./app/
RUN pip install --no-cache-dir --prefix=/install .

# ─── Runtime ──────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/install/bin:$PATH" \
    PYTHONPATH="/install/lib/python3.12/site-packages:/app"

COPY --from=builder /install /install
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .

RUN addgroup --system app && adduser --system --group app
USER app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
