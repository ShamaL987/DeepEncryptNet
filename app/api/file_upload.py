from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException
import uuid

router = APIRouter()

READY_DIR = Path("/data/files/captures/ready")
READY_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/api/ingest/batch")
async def upload_batch(file: UploadFile = File(...)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed.")

    unique_name = f"{uuid.uuid4().hex}_{file.filename}"
    target_path = READY_DIR / unique_name

    content = await file.read()
    target_path.write_bytes(content)

    return {
        "status": "accepted",
        "filename": unique_name,
        "saved_to": str(target_path),
    }