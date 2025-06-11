# Dockerfile for Neuroglancer with FastAPI backend
# Based on Python 3.10 slim image

# docker build -t neuroglancer-server .
# docker run -it -p 8000:8000 -p 7000:7000 -v D:\Lab\others\YA_HAN:/neuroglancer/data" neuroglancer-server

FROM python:3.10-slim

# Install basic tools needed by Neuroglancer
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /neuro-server

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your source code
COPY . .

# Expose FastAPI (8000) and Neuroglancer (7000)
EXPOSE 8000
EXPOSE 7000
