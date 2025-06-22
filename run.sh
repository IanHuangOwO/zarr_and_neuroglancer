#!/bin/bash

# Prompt for data directory
read -p "Enter the full path to your data directory (e.g., /home/user/data): " USER_INPUT

# Resolve to absolute path and normalize slashes
HOST_DATA_PATH=$(realpath "$USER_INPUT" 2>/dev/null)

# Validate path
if [ ! -d "$HOST_DATA_PATH" ]; then
  echo "Error: Path does not exist. Exiting..."
  exit 1
fi

# Normalize code path to absolute as well
HOST_CODE_PATH=$(realpath "./converter")
CONTAINER_CODE_PATH="/workspace/converter"
CONTAINER_DATA_PATH="/workspace/datas"
CONTAINER_NAME="zarr_neuroglancer"
CONTAINER_WORKSPACE_PATH="/workspace"
COMPOSE_FILE="./docker-compose.yml"

# Generate docker-compose.yml
echo "Generating docker-compose.yml..."
cat > "$COMPOSE_FILE" <<EOF
services:
  ${CONTAINER_NAME}:
    container_name: ${CONTAINER_NAME}
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
      - "7000:7000"
    volumes:
      - "${HOST_CODE_PATH}:${CONTAINER_CODE_PATH}"
      - "${HOST_DATA_PATH}:${CONTAINER_DATA_PATH}"
    working_dir: ${CONTAINER_WORKSPACE_PATH}
    command: uvicorn server:app --host 0.0.0.0 --port 8000
EOF

# Define cleanup function
cleanup() {
  echo -e "\nStopping and cleaning up Docker container..."
  docker-compose down
  if [ -f "$COMPOSE_FILE" ]; then
    rm "$COMPOSE_FILE"
    echo "Removed generated docker-compose.yml"
  fi
}
trap cleanup EXIT

# Start the container
echo "Starting container via docker-compose up --build..."
docker-compose up --build