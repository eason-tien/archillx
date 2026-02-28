from __future__ import annotations
from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter(tags=["ui"])
BASE_DIR = Path(__file__).resolve().parent / "static"

@router.get("/ui", include_in_schema=False)
def ui_index():
    return FileResponse(BASE_DIR / "index.html")
