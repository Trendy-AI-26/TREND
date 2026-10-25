# Frontend build stage
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci --frozen-lockfile

COPY frontend/ ./

ARG NEXT_PUBLIC_STORAGE_PUBLIC_URL
ARG NEXT_SERVER_API_URL=http://127.0.0.1:8000
ENV NEXT_PUBLIC_STORAGE_PUBLIC_URL=$NEXT_PUBLIC_STORAGE_PUBLIC_URL
ENV NEXT_SERVER_API_URL=$NEXT_SERVER_API_URL

RUN npm run build

# Backend dependency stage
FROM python:3.13-slim AS backend-deps

WORKDIR /tmp

COPY backend/requirements.txt ./
RUN pip install --user --no-cache-dir -r requirements.txt

# Runtime stage
FROM python:3.13-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    tini \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js from NodeSource repository
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && apt-get remove -y curl \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# Copy Python dependencies from backend-deps stage
COPY --from=backend-deps /root/.local /home/appuser/.local
ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Copy backend code
COPY --chown=appuser:appuser backend/app /app/backend/app
COPY --chown=appuser:appuser backend/db /app/backend/db

# Copy frontend artifacts from build stage
COPY --from=frontend-builder --chown=appuser:appuser /app/frontend/.next/standalone /app/frontend
COPY --from=frontend-builder --chown=appuser:appuser /app/frontend/.next/static /app/frontend/.next/static
COPY --from=frontend-builder --chown=appuser:appuser /app/frontend/public /app/frontend/public

# Copy entrypoint script
COPY --chown=appuser:appuser scripts/container-entrypoint.sh /app/scripts/container-entrypoint.sh
RUN chmod +x /app/scripts/container-entrypoint.sh

# Runtime server-side calls use the same backend as the build-time rewrite.
ARG NEXT_SERVER_API_URL=http://127.0.0.1:8000
ENV NEXT_SERVER_API_URL=$NEXT_SERVER_API_URL

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python3 -c "import os,urllib.request,sys;bp=os.environ.get('BACKEND_PORT','8000');fp=os.environ.get('FRONTEND_PORT','3000');r1=urllib.request.urlopen(f'http://localhost:{bp}/health');r2=urllib.request.urlopen(f'http://localhost:{fp}');sys.exit(0 if r1.status==200 and r2.status==200 else 1)" || exit 1

# Switch to non-root user
USER appuser

EXPOSE 3000 8000

ENTRYPOINT ["tini", "--"]
CMD ["/app/scripts/container-entrypoint.sh"]
