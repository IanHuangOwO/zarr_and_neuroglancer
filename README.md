Hello
# 🧠 Zarr Neuroglancer Viewer

This project visualizes Zarr image data in a Neuroglancer viewer served via FastAPI.

---

## 🚀 Quick Start (Recommended)

### 1. Install Docker

Download and install Docker for your system:

- [Docker Desktop for Windows/macOS](https://www.docker.com/products/docker-desktop)
- For Ubuntu/Linux:

```bash
sudo apt update
sudo apt install docker.io docker-compose
sudo systemctl enable docker
sudo systemctl start docker
```

Verify Docker is working:

```bash
docker --version
docker-compose --version
```

---

### 2. Run the App

#### For Linux/macOS:

```bash
chmod +x run.sh
./run.sh
```

#### For Windows (PowerShell):

```powershell
./run.ps1
```

You’ll be prompted to enter the path to your **Zarr dataset directory**. The script will handle everything from Docker build to startup.

---

## 🛠️ What the Script Does

- Dynamically generates a `docker-compose.yml`
- Mounts your dataset into the container
- Launches `viewer.py` and a FastAPI server
- Cleans up Docker resources after exit

---

## 🧪 Optional: Manual Docker Commands

If you prefer to run everything manually:

```bash
docker build -t zarr-neuroglancer .
docker run -it -p 8000:8000 -v /your/data:/workspace/datas zarr-neuroglancer
```

---

## 📁 Serving Your Data

Your Zarr data should be located in the directory you specify when prompted. By default, it will be mounted inside the container at:

```
/workspace/datas
```

Update `viewer.py` if needed to reflect how your data should be displayed.

---

## 📜 License

MIT License