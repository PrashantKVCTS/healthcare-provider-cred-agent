# ==============================================================================
# Multi-Stage Production Dockerfile for Healthcare Credentialing Approval Agent
# Security Hardened: Non-root user, slim base, HIPAA-compliant configuration
# ==============================================================================

# Stage 1: Build & Dependency Wheel Cache
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt


# Stage 2: Minimal Secure Runtime
FROM python:3.11-slim AS runtime

# Set security and Python environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/app" \
    PORT=8000

WORKDIR /app

# Install curl for container health check
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create a non-privileged dedicated service user (HIPAA / CIS Benchmark compliance)
RUN groupadd -g 1001 appgroup && \
    useradd -u 1001 -g appgroup -s /bin/bash -m appuser

# Copy installed Python packages from builder stage
COPY --from=builder /root/.local /home/appuser/.local
ENV PATH="/home/appuser/.local/bin:$PATH"

# Copy application source code
COPY --chown=appuser:appgroup agents/ /app/agents/
COPY --chown=appuser:appgroup api/ /app/api/
COPY --chown=appuser:appgroup appian/ /app/appian/
COPY --chown=appuser:appgroup config/ /app/config/
COPY --chown=appuser:appgroup data/ /app/data/
COPY --chown=appuser:appgroup models/ /app/models/
COPY --chown=appuser:appgroup services/ /app/services/
COPY --chown=appuser:appgroup ui/ /app/ui/
COPY --chown=appuser:appgroup run_agent.py /app/run_agent.py

# Switch to non-root user
USER appuser

# Expose API and Streamlit ports
EXPOSE 8000 8501

# Container Healthcheck (pings Appian health endpoint)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Default runtime: Launch production Uvicorn server with 4 worker processes
CMD ["uvicorn", "api.appian_api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
