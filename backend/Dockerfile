# ============================================
# PRODUCTION DOCKERFILE FOR AI VIDEO SAAS
# ============================================
# Uses pre-built base image with ML dependencies for FAST deployments (~2-3 min)
#
# FIRST TIME SETUP (only once):
# 1. Build the base image: gcloud builds submit --tag gcr.io/shortcutai-backend/ai-video-base:v1 -f Dockerfile.base .
# 2. Then deploy normally: gcloud run deploy ai-video-backend --source . --region us-central1 --allow-unauthenticated
# ============================================

FROM gcr.io/shortcutai-backend/ai-video-base:v1

WORKDIR /app

# Install ONLY light dependencies (fast - ~30 seconds)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
ENV CACHE_BUSTER=20260820_2105
COPY . .

# Port configuration
ENV PORT=8080

# Run the application
CMD uvicorn main:app --host 0.0.0.0 --port $PORT
