# Dockerfile for Neuroglancer with FastAPI backend and Zarr-Tiff Format Transform
# Based on Python 3.10 slim image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install Package dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Set working directory
WORKDIR /workspace

# Copy viewer and server code
COPY viewer.py .
COPY server.py .