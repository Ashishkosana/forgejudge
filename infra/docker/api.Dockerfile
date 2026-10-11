FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY pyproject.toml README.md ./
COPY alembic.ini ./
COPY backend ./backend
COPY scripts ./scripts
RUN pip install --no-cache-dir .
RUN useradd --system --uid 10001 --create-home app

USER app
EXPOSE 8000
CMD ["uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000"]