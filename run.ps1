$ImageName = "neuroglancer-server:latest"
$ContainerName = "neuro-server"
$HostDataPath = "D:/Lab/others/YA_HAN"  # Use forward slashes
$ContainerDataPath = "/neuro-server/data"

# 🐳 Build image
Write-Host "Building Docker image: $ImageName"
docker build -t $ImageName .

# 🚮 Remove existing container if it exists
if (docker ps -a --format "{{.Names}}" | Select-String -Pattern "^$ContainerName$") {
    Write-Host "Removing existing container named '$ContainerName'"
    docker rm -f $ContainerName
}

# 🐳 Build and run Docker container
$DockerCommand = "docker run -it --rm --name $ContainerName -p 8000:8000 -p 7000:7000 -v `"$HostDataPath`:$ContainerDataPath`" $ImageName bash"

Write-Host "Running container '$ContainerName'"
Invoke-Expression $DockerCommand