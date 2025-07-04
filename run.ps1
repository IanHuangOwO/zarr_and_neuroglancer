# Prompt user for the host data directory
$UserInput = Read-Host "Enter the full path to your data directory (e.g., D:/path/to/data)"

# Normalize slashes (convert \ to /) and resolve to absolute path
$NormalizedPath = $UserInput -replace '\\', '/'
$ResolvedPath = Resolve-Path $NormalizedPath -ErrorAction SilentlyContinue

# Validate input
if (-not $ResolvedPath) {
    Write-Error "The specified path does not exist. Exiting..."
    exit 1
}

$HostDataPath = $ResolvedPath.Path -replace '\\', '/'

# Docker information
$ContainerName = "zarr_neuroglancer"
$ContainerWorkspacePath = "/workspace"

# Fixed code directory
$HostCodeDir = "./image_io"
$ContainerCodePath = "/workspace/image_io"

# Container data mount path
$ContainerDataPath = "/workspace/datas"

# Docker Compose file path
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
    command: uvicorn server:app --host 0.0.0.0 --port 8000 
"@

# Start the Docker container using docker-compose 
try {
    Write-Host "Starting container via docker-compose up --build..."
    docker-compose up --build # (access inside the docker: docker exec -it zarr_neuroglancer /bin/bash)
}
finally {
    Write-Host "`nStopping and cleaning up Docker container..."
    docker-compose down

    if (Test-Path $ComposeFile) {
        Remove-Item $ComposeFile -Force
        Write-Host "Removed generated docker-compose.yml"
    }
}