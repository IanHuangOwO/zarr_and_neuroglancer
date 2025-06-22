from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

DATA_DIR = "./datas"

@app.get("/{file_path:path}")
def serve_file(file_path: str):
    full_path = os.path.join(DATA_DIR, file_path)
    
    if os.path.isdir(full_path):
        # Optional: List directory contents
        return JSONResponse({
            "directory": file_path,
            "contents": os.listdir(full_path)
        })
    
    if os.path.isfile(full_path):
        return FileResponse(full_path)
    
    raise HTTPException(status_code=404, detail="File not found")