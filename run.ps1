# ----- Prompt user for the data directory -----
$UserInput = Read-Host "Enter the path to your data directory (e.g., D:/path/to/data)"

# Normalize slashes (convert \ to /) and resolve to absolute path
$NormalizedPath = $UserInput -replace '\\', '/'
$ResolvedPath = Resolve-Path $NormalizedPath -ErrorAction SilentlyContinue

# Validate input
if (-not $ResolvedPath) {
    Write-Error "The specified path does not exist. Exiting..."
    exit 1
}


# ----- Docker information -----
$ContainerName = "neuroglancer"
$ContainerWorkspacePath = "/workspace"

$HostDataPath = $ResolvedPath.Path -replace '\\', '/'
$ContainerDataPath = "/workspace/datas"


# ----- Docker Compose file path -----
$ComposeFile = "./docker-compose.yml"

Write-Host "Generating docker-compose.yml..."
Set-Content -Path $ComposeFile -Value @"
services:
  ${ContainerName}:
    container_name: ${ContainerName}
    build:
      context: ./
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
      - "7000:7000"
    volumes:
      - "${HostDataPath}:${ContainerDataPath}"
    working_dir: ${ContainerWorkspacePath}
    command: sh -c "python viewer.py & uvicorn server:app --host 0.0.0.0 --port 8000 --workers 4 --loop uvloop --no-access-log"
"@

# ----- Start the Docker container ----- 
try {
    Write-Host "Starting container via docker-compose up --build..."
    docker compose up --build
}
finally {
    Write-Host "`nStopping and cleaning up Docker container..."
    docker compose down

    if (Test-Path $ComposeFile) {
        Remove-Item $ComposeFile -Force
        Write-Host "Removed generated docker-compose.yml"
    }

    Write-Host "Pruning unused Docker images..."
    docker image prune -f
}