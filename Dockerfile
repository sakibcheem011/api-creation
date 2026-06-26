# Multi-stage build to keep the production image slim
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install dependencies to a user-local directory to easily copy to final image
RUN pip install --no-cache-dir --user -r requirements.txt

# Final production image
FROM python:3.11-slim

WORKDIR /app

# Copy installed dependencies and configure path
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy application source code
COPY . /app

# Set recommended python environments for containers
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PORT=8000

EXPOSE 8000

# Run FastAPI using dynamic port binding (Render standard)
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
