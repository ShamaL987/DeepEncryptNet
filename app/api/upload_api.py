from pathlib import Path
import uuid

from fastapi import APIRouter, Request, UploadFile, File, HTTPException, Depends, Header
from sqlalchemy.orm import Session

from app.api import get_settings_manager_from_request
from app.database.db import get_db
from app.utils.validator import validate_ingest_api_token

router = APIRouter(prefix="/file-upload", tags=["File Upload"])


@router.post("/ingest")
async def upload_batch(
    request: Request, file: UploadFile = File(...),
    db: Session = Depends(get_db),
    x_api_key: str | None = Header(default=None)
):
    validate_ingest_api_token(db=db, raw_token=x_api_key)

    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed.")

    settings_manager = get_settings_manager_from_request(request)
    runtime_config = settings_manager.get_runtime_config()

    ready_dir_value = runtime_config["flow_daemon"].get("ready_dir")
    if not ready_dir_value:
        raise HTTPException(status_code=500, detail="ready_dir is not configured.")

    ready_dir = Path(ready_dir_value)
    ready_dir.mkdir(parents=True, exist_ok=True)

    safe_filename = Path(file.filename).name
    unique_name = f"{uuid.uuid4().hex}_{safe_filename}"
    target_path = ready_dir / unique_name

    try:
        content = await file.read()
        target_path.write_bytes(content)
    finally:
        await file.close()

    return {
        "status": "accepted",
        "filename": unique_name,
        "saved_to": str(target_path),
    }