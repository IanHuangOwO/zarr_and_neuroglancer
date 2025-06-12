# This script sets up a Docker container for Zarr Neuroglancer with VS Code DevContainer support.
# It builds the Docker image if it doesn't exist, removes any existing container with the same name,
# and runs the container with the necessary bind mounts for workspace and data directories.
# Ensure Docker is running before executing this script.

# Docker information
$ContainerName = "zarr_neuroglancer"
$ContainerWorkspacePath = "/workspace"

# Convert relative path to absolute
$HostCodeDir = "D:/iansaididontcare/Lab/zarr_and_neuroglancer/code" # Adjust this path as needed
$ContainerCodePath = "/workspace/code"

# Data path
$HostDataPath = "D:/iansaididontcare/Lab/others/YA_HAN" # Adjust this path as needed
$ContainerDataPath = "/workspace/data"

# Docker Compose file generation
$ComposeFile = "./docker-compose.yml"

Write-Host "Generating docker-compose.yml..."
Set-Content -Path $ComposeFile -Value @"
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
    command: uvicorn code.server:app --host 0.0.0.0 --port 8000
"@

# DevContainer config generation
$DevContainerDir  = ".devcontainer"
$DevContainerFile = Join-Path $DevContainerDir "devcontainer.json"
Write-Host "Generating .devcontainer/devcontainer.json..."
if (-not (Test-Path $DevContainerDir -PathType Container)) {
    New-Item -ItemType Directory -Path $DevContainerDir | Out-Null
}
Set-Content -Path $DevContainerFile -Value @"
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
"@

# 4) Build and start fresh; on exit (normal or Ctrl+C), the cleanup block will fire
Write-Host "Starting container via docker-compose up --build…"
docker-compose up --build