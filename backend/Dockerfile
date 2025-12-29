# Use official Python runtime as a parent image
FROM python:3.10-slim

# Set environment variables
# PREVENT Python from writing pyc files to disc
ENV PYTHONDONTWRITEBYTECODE 1
# PREVENT Python from buffering stdout and stderr
ENV PYTHONUNBUFFERED 1

# Install system dependencies required for MoviePy, FFmpeg, and ImageMagick
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    imagemagick \
    libgl1 \
    libegl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*


# Fix ImageMagick policy to allow reading/writing common formats for video text
# Handles both ImageMagick 6 and 7 paths
RUN if [ -f /etc/ImageMagick-6/policy.xml ]; then \
    sed -i 's/none/read,write/g' /etc/ImageMagick-6/policy.xml && \
    sed -i '/<policy domain="path" rights="none" pattern="@\*"/d' /etc/ImageMagick-6/policy.xml; \
    fi && \
    if [ -f /etc/ImageMagick-7/policy.xml ]; then \
    sed -i 's/none/read,write/g' /etc/ImageMagick-7/policy.xml && \
    sed -i '/<policy domain="path" rights="none" pattern="@\*"/d' /etc/ImageMagick-7/policy.xml; \
    fi

# Set work directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Expose the port (Cloud Run sets this env variable, default 8080)
ENV PORT 8080

# Run the application
# We use shell form to expand ${PORT}
CMD uvicorn main:app --host 0.0.0.0 --port $PORT
