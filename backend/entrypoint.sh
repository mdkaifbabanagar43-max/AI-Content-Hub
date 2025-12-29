#!/bin/sh
echo "----------------------------------------"
echo "🚀 STARTING AI VIDEO BACKEND CONTAINER"
echo "----------------------------------------"
echo "Current Directory: $(pwd)"
echo "Listing files:"
ls -F
echo "----------------------------------------"
echo "Environment Variables:"
env
echo "----------------------------------------"
echo "Starting Uvicorn..."
exec uvicorn main:app --host 0.0.0.0 --port $PORT
