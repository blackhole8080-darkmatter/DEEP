# DEEP Dockerfile — production-ready container
# Stage 1: build the modern TypeScript UI
# Stage 2: Python runtime with all dependencies

# ── Stage 1: Build frontend ───────────────────────────────────────────────────
FROM node:22-alpine AS frontend-builder
WORKDIR /app/interface/web
COPY interface/web/package*.json ./
RUN npm ci
COPY interface/web/ ./
RUN npm run build

# ── Stage 2: Python runtime ───────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

# System deps for scientific Python + audio + vision
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    libssl-dev \
    libpq-dev \
    tesseract-ocr \
    ffmpeg \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python deps
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Copy built frontend from stage 1
COPY --from=frontend-builder /app/interface/static/app-dist ./interface/static/app-dist

# Ensure data/logs dirs exist
RUN mkdir -p data logs

# Entrypoint
ENV PYTHONUNBUFFERED=1
EXPOSE 7768
CMD ["python", "-m", "uvicorn", "interface.server:app", "--host", "0.0.0.0", "--port", "7768"]
