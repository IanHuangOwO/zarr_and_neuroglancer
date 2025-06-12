# This script sets up a Docker container for Zarr Neuroglancer with VS Code DevContainer support.
# It builds the Docker image if it doesn't exist, removes any existing container with the same name,
# and runs the container with the necessary bind mounts for workspace and data directories.
# Ensure Docker is running before executing this script.

# Docker information
$ImageName = "zarr_neuroglancer:latest"
$ContainerName = "zarr_neuroglancer"

# Convert relative path to absolute
$HostWorkspaceDir = "D:/iansaididontcare/Lab/zarr_and_neuroglancer" # Adjust this path as needed
$ContainerWorkspacePath = "/zarr_neuroglancer"

# Data path
$HostDataPath = "D:/iansaididontcare/Lab/others/YA_HAN" # Adjust this path as needed
$ContainerDataPath = "/zarr_neuroglancer/data"

# 🔧 DevContainer config generation
$DevContainerDir = ".devcontainer"
$DevContainerFile = "$DevContainerDir\devcontainer.json"

Write-Host "Generating .devcontainer/devcontainer.json..."
New-Item -ItemType Directory -Force -Path $DevContainerDir | Out-Null
Set-Content -Path $DevContainerFile -Value @"
{
  "name": "$ContainerName",
  "image": "$ImageName",
  "workspaceFolder": "$ContainerWorkspacePath",
  "mounts": [
    "source=${HostWorkspaceDir},target=${ContainerWorkspacePath},type=bind",
    "source=${HostDataPath},target=${ContainerDataPath},type=bind"
  ],
  "customizations": {
    "vscode": {
      "settings": {
        "python.pythonPath": "/usr/local/bin/python"
      },
      "extensions": [
        "ms-python.python"
      ]
    }
  }
}
"@

# 🐳 Build image if it doesn't exist
if (-not (docker images -q $ImageName)) {
    Write-Host "Building Docker image: $ImageName"
    docker build -t $ImageName .
} else {
    Write-Host "Docker image '$ImageName' already exists"
}

# 🚮 Remove existing container if it exists
if (docker ps -a --format "{{.Names}}" | Select-String -Pattern "^$ContainerName$") {
    Write-Host "Removing existing container named '$ContainerName'"
    docker rm -f $ContainerName
}

# 🐳 Run Docker container with bind mounts
$DockerArgs = @(
    "run", "-it", "--rm",
    "--name", $ContainerName,
    "-p", "8000:8000",
    "-p", "7000:7000",
    "-v", "${HostWorkspaceDir}:${ContainerWorkspacePath}",
    "-v", "${HostDataPath}:${ContainerDataPath}",
    "-w", "$ContainerWorkspacePath",
    $ImageName,
    "bash"
)

Write-Host "Running container '$ContainerName'"
& docker @DockerArgs