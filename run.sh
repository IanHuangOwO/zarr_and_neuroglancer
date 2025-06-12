#!/bin/bash

# This script sets up a Docker container for Zarr Neuroglancer with VS Code DevContainer support.
# It builds the Docker image if it doesn't exist, removes any existing container with the same name,
# and runs the container with the necessary bind mounts for workspace and data directories.

set -e  # Exit immediately if a command exits with a non-zero status

# Docker information
ContainerName="zarr_neuroglancer"
ContainerWorkspacePath="/workspace"

# Host paths (update these paths for Linux/Mac or use WSL if on Windows)
HostCodeDir="/root/home/iansaididontcare/Lab/zarr_and_neuroglancer/codes"
ContainerCodePath="/workspace/codes"

HostDataPath=/root/home/iansaididontcare/Lab/others/YA_HAN"
ContainerDataPath="/workspace/datas"

# Docker Compose file generation
ComposeFile="./docker-compose.yml"

echo "Generating docker-compose.yml..."
cat > "$ComposeFile" <<EOF
services:
  ${ContainerName}:
    container_name: ${ContainerName}
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
      - "7000:7000"
    volumes:
      - "${HostCodeDir}:${ContainerCodePath}"
      - "${HostDataPath}:${ContainerDataPath}"
    working_dir: ${ContainerWorkspacePath}
    command: uvicorn codes.server:app --host 0.0.0.0 --port 8000
EOF

# DevContainer config generation
DevContainerDir=".devcontainer"
DevContainerFile="${DevContainerDir}/devcontainer.json"

echo "Generating ${DevContainerFile}..."
mkdir -p "$DevContainerDir"

cat > "$DevContainerFile" <<EOF
{
  "name": "${ContainerName}",
  "service": "${ContainerName}",
  "dockerComposeFile": ".${ComposeFile}",
  "workspaceFolder": "${ContainerWorkspacePath}",
  "forwardPorts": [8000, 7000],
  "customizations": {
    "vscode": {
      "settings": {
        "python.pythonPath": "/usr/local/bin/python"
      },
      "extensions": [
        "ms-python.python",
        "ms-python.vscode-pylance"
      ]
    }
  }
}
EOF

# Remove any existing container with the same name
if docker ps -a --format '{{.Names}}' | grep -q "^${ContainerName}$"; then
  echo "Removing existing container ${ContainerName}..."
  docker rm -f "${ContainerName}"
fi

# Build and start container
echo "Starting container via docker-compose up --build..."
docker-compose up --build