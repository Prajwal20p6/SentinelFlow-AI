FROM python:3.11-slim

WORKDIR /app

# Install system utilities for health check
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app files
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .
COPY enkryptai ./enkryptai

# Expose port
EXPOSE 8000

# Health check (hitting our live endpoint)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Run app using Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
