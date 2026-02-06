"""Recordings endpoints"""
from fastapi import APIRouter
router = APIRouter()

@router.get("")
async def list_recordings():
    return {"message": "List recordings"}

@router.get("/{recording_id}")
async def get_recording(recording_id: str):
    return {"message": f"Get recording {recording_id}"}

@router.get("/{recording_id}/audio")
async def stream_recording(recording_id: str):
    return {"message": f"Stream recording {recording_id}"}

@router.post("/{recording_id}/transcribe")
async def transcribe_recording(recording_id: str):
    return {"message": f"Transcribe recording {recording_id}"}
