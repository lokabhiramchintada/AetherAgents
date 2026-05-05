import os
import shutil
from typing import List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse

app = FastAPI()

BASE_DIR = os.path.abspath("storage")
APPS_DIR = os.path.join(BASE_DIR, "apps")
PLATFORM_DIR = os.path.join(BASE_DIR, "platform")

os.makedirs(APPS_DIR, exist_ok=True)
os.makedirs(PLATFORM_DIR, exist_ok=True)


# ----------------------------
# Helper: safe path join
# ----------------------------
def safe_join(base, *paths):
    final_path = os.path.abspath(os.path.join(base, *paths))
    if not final_path.startswith(base):
        raise HTTPException(400, "Invalid path")
    return final_path


# ----------------------------
# Helper: read file
# ----------------------------
def read_file_content(path):
    with open(path, "rb") as f:
        return f.read().decode("latin1")


# ----------------------------
# Helper: recursive directory read
# ----------------------------
def read_directory(base_root, target_path):
    result = []

    for root, _, files in os.walk(target_path):
        for f in files:
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, base_root)

            result.append({
                "path": rel_path,
                "content": read_file_content(full_path)
            })

    return result


# ----------------------------
# 1. PUSH FULL APP
# ----------------------------
@app.post("/push/app")
async def push_app(
    app_name: str = Form(...),
    paths: List[str] = Form(...),
    files: List[UploadFile] = File(...)
):
    if len(paths) != len(files):
        raise HTTPException(400, "paths and files mismatch")

    app_path = safe_join(APPS_DIR, app_name)

    # overwrite existing app
    if os.path.exists(app_path):
        shutil.rmtree(app_path)

    for rel_path, file in zip(paths, files):
        target_path = safe_join(app_path, rel_path)

        os.makedirs(os.path.dirname(target_path), exist_ok=True)

        content = await file.read()

        with open(target_path, "wb") as f:
            f.write(content)

    return {
        "status": "success",
        "app": app_name,
        "files_uploaded": len(files)
    }


# ----------------------------
# 2. CHECK APP EXISTS
# ----------------------------
@app.get("/app/{app_name}/exists")
def app_exists(app_name: str):
    app_path = safe_join(APPS_DIR, app_name)
    return {"exists": os.path.exists(app_path)}


# ----------------------------
# 3. PULL APP (FILE OR DIR)
# ----------------------------
@app.get("/pull/app")
def pull_app(app_name: str, path: str = ""):
    app_path = safe_join(APPS_DIR, app_name)

    if not os.path.exists(app_path):
        raise HTTPException(404, "App not found")

    target_path = safe_join(app_path, path)

    if not os.path.exists(target_path):
        raise HTTPException(404, "Path not found")

    # FILE
    if os.path.isfile(target_path):
        return JSONResponse({
            "type": "file",
            "path": path,
            "content": read_file_content(target_path)
        })

    # DIRECTORY
    return {
        "type": "directory",
        "base_path": path,
        "files": read_directory(app_path, target_path)
    }


# ----------------------------
# 4. PULL PLATFORM (FILE OR DIR)
# ----------------------------
@app.get("/pull/platform")
def pull_platform(path: str = ""):
    if not os.path.exists(PLATFORM_DIR):
        raise HTTPException(404, "Platform not found")

    target_path = safe_join(PLATFORM_DIR, path)

    if not os.path.exists(target_path):
        raise HTTPException(404, "Path not found")

    # FILE
    if os.path.isfile(target_path):
        return JSONResponse({
            "type": "file",
            "path": path,
            "content": read_file_content(target_path)
        })

    # DIRECTORY
    return {
        "type": "directory",
        "base_path": path,
        "files": read_directory(PLATFORM_DIR, target_path)
    }