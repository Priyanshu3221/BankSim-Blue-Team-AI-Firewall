# BankSim: Blue-Team AI Firewall — Backend Dockerfile for Google Cloud Run
#
# Build context: backend/ directory (matches Google Cloud Run Developer Connect
# when the Dockerfile is located inside backend/)
#
# Local build command:
#   docker build -t banksim-backend backend
#   (or: cd backend && docker build -t banksim-backend .)
#
# Google Cloud Run / Developer Connect:
#   Source context directory: backend
#   Dockerfile path: Dockerfile (or backend/Dockerfile depending on UI prompt)

FROM python:3.11-slim

# Working directory inside the container
WORKDIR /app

# Python runtime configuration:
# - PYTHONDONTWRITEBYTECODE: Prevents creation of transient .pyc files
# - PYTHONUNBUFFERED: Stream logs directly to Cloud Logging without buffering
# - PYTHONPATH: Ensures `/app` is on sys.path so `backend.*` imports resolve correctly
# - PORT: Default port required by Cloud Run contract
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8080

# Step 1: Install Python dependencies first for optimal Docker layer caching
COPY requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/backend/requirements.txt

# Step 2: Copy backend application code into /app/backend
COPY . /app/backend/

# Step 3: Security hardening — Run as an unprivileged non-root user
# Create dedicated group and user, initialize SQLite data directory, and set permissions
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/sh -M -d /app appuser && \
    mkdir -p /app/backend/data && \
    chown -R appuser:appgroup /app

# Switch to unprivileged runtime user
USER appuser

# Container port documentation (Cloud Run dynamically sets $PORT)
EXPOSE 8080

# Step 4: Application startup command
# Uses 'exec' so Uvicorn runs as PID 1 to handle SIGTERM signals gracefully during container teardown.
# Shell evaluation expands ${PORT:-8080} to honor Cloud Run's dynamic port assignment.
CMD ["sh", "-c", "exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
