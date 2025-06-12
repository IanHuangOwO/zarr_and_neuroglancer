# Dockerfile for Neuroglancer with FastAPI backend and Zarr-Tiff Format Transform
# Based on Python 3.10 slim image
FROM python:3.10-slim

# # Install basic tools needed by Neuroglancer
# RUN apt-get update && apt-get install -y \
#     curl \
#     git \
#     && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Expose Neuroglancer (7000) and FastAPI (8000)
EXPOSE 7000
EXPOSE 8000