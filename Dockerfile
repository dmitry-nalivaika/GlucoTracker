FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (none beyond Python base needed for aiosqlite + httpx)
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml .
COPY src/ src/

# Install the package with all runtime dependencies
RUN pip install --no-cache-dir -e .

# Create persistent data directory (overridden by Azure Files mount in production)
RUN mkdir -p /app/data

# Run as non-root for security
RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app
USER appuser

# Environment defaults — all overridden by Container App secrets
ENV DATABASE_URL=sqlite+aiosqlite:////app/data/glucotrack.db
ENV STORAGE_ROOT=/app/data

CMD ["python", "-m", "glucotrack"]
