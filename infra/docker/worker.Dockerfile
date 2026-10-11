FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY pyproject.toml README.md ./
COPY backend ./backend
RUN pip install --no-cache-dir .
RUN useradd --system --uid 10001 --create-home app

USER app
CMD ["python", "-m", "backend.worker.main"]