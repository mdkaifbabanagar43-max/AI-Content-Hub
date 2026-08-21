$PROJECT_ID = "shortcutai-backend"
$IMAGE_TAG = "gcr.io/$PROJECT_ID/ai-video-backend"
$REGION = "us-central1"

Write-Host "Starting Fast Build and Deploy..." -ForegroundColor Cyan

# Step 1: Build
Write-Host "Step 1: Building Container Image..." -ForegroundColor Yellow
gcloud builds submit --config cloudbuild.yaml --substitutions=_IMAGE_NAME=$IMAGE_TAG
if ($LASTEXITCODE -ne 0) {
    Write-Host "Build Failed!" -ForegroundColor Red
    exit 1
}

# Step 2: Deploy
Write-Host "Step 2: Deploying to Cloud Run..." -ForegroundColor Yellow
gcloud run deploy ai-video-backend --image $IMAGE_TAG --platform managed --region $REGION --allow-unauthenticated --memory 4Gi --cpu 2 --no-cpu-throttling --max-instances 1 --port 8080 --timeout 3600
if ($LASTEXITCODE -ne 0) {
    Write-Host "Deployment Failed!" -ForegroundColor Red
    exit 1
}

Write-Host "Deployment Complete!" -ForegroundColor Green
