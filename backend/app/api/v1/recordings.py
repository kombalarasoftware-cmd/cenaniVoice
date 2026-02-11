from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import redis.asyncio as aioredis
import io
import struct
import os

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models import CallLog, User
from app.schemas import RecordingResponse

router = APIRouter(prefix="/recordings", tags=["Recordings"])

REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")


@router.get("", response_model=List[RecordingResponse])
async def list_recordings(
    campaign_id: Optional[int] = None,
    agent_id: Optional[int] = None,
    sentiment: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List call recordings"""
    query = db.query(CallLog).join(CallLog.campaign).filter(
        CallLog.campaign.has(owner_id=current_user.id),
        CallLog.recording_url.isnot(None)
    )
    
    if campaign_id:
        query = query.filter(CallLog.campaign_id == campaign_id)
    if agent_id:
        query = query.filter(CallLog.agent_id == agent_id)
    if sentiment:
        query = query.filter(CallLog.sentiment == sentiment)
    if date_from:
        query = query.filter(CallLog.created_at >= date_from)
    if date_to:
        query = query.filter(CallLog.created_at <= date_to)
    if search:
        query = query.filter(
            (CallLog.customer_name.ilike(f"%{search}%")) |
            (CallLog.to_number.ilike(f"%{search}%"))
        )
    
    calls = query.order_by(CallLog.created_at.desc()).offset(skip).limit(limit).all()
    
    # Map to recording response
    recordings = []
    for call in calls:
        recordings.append(RecordingResponse(
            id=call.id,
            call_sid=call.call_sid,
            to_number=call.to_number or "",
            customer_name=call.customer_name,
            campaign_name=call.campaign.name if call.campaign else None,
            agent_name=call.agent.name if call.agent else None,
            duration=call.recording_duration or call.duration,
            status="completed",
            sentiment=call.sentiment,
            recording_url=call.recording_url,
            transcription=call.transcription,
            created_at=call.created_at
        ))
    
    return recordings


@router.get("/{recording_id}")
async def get_recording(
    recording_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get recording details"""
    call = db.query(CallLog).join(CallLog.campaign).filter(
        CallLog.id == recording_id,
        CallLog.campaign.has(owner_id=current_user.id),
        CallLog.recording_url.isnot(None)
    ).first()
    
    if not call:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    return {
        "id": call.id,
        "call_sid": call.call_sid,
        "phone_number": call.to_number,
        "customer_name": call.customer_name,
        "campaign": {
            "id": call.campaign.id,
            "name": call.campaign.name
        } if call.campaign else None,
        "agent": {
            "id": call.agent.id,
            "name": call.agent.name
        } if call.agent else None,
        "duration": call.recording_duration or call.duration,
        "sentiment": call.sentiment,
        "intent": call.intent,
        "summary": call.summary,
        "recording_url": call.recording_url,
        "transcription": call.transcription,
        "metadata": call.call_metadata,
        "created_at": call.created_at
    }


@router.get("/{recording_id}/download")
async def download_recording(
    recording_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get download URL for recording"""
    call = db.query(CallLog).join(CallLog.campaign).filter(
        CallLog.id == recording_id,
        CallLog.campaign.has(owner_id=current_user.id),
        CallLog.recording_url.isnot(None)
    ).first()
    
    if not call:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    # TODO: Generate presigned URL from MinIO
    return {
        "download_url": call.recording_url,
        "expires_in": 3600
    }


@router.delete("/{recording_id}")
async def delete_recording(
    recording_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a recording"""
    call = db.query(CallLog).join(CallLog.campaign).filter(
        CallLog.id == recording_id,
        CallLog.campaign.has(owner_id=current_user.id),
        CallLog.recording_url.isnot(None)
    ).first()
    
    if not call:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    # TODO: Delete from MinIO storage
    
    call.recording_url = None
    call.recording_duration = None
    db.commit()
    
    return {"message": "Recording deleted"}


@router.post("/{recording_id}/transcribe")
async def transcribe_recording(
    recording_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Request transcription for a recording"""
    call = db.query(CallLog).join(CallLog.campaign).filter(
        CallLog.id == recording_id,
        CallLog.campaign.has(owner_id=current_user.id),
        CallLog.recording_url.isnot(None)
    ).first()
    
    if not call:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    if call.transcription:
        return {"message": "Recording already has transcription"}
    
    # TODO: Queue transcription task
    
    return {"message": "Transcription queued"}


@router.post("/{recording_id}/analyze")
async def analyze_recording(
    recording_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Analyze recording for sentiment and intent"""
    call = db.query(CallLog).join(CallLog.campaign).filter(
        CallLog.id == recording_id,
        CallLog.campaign.has(owner_id=current_user.id)
    ).first()
    
    if not call:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    if not call.transcription:
        raise HTTPException(status_code=400, detail="No transcription available")
    
    # TODO: Queue analysis task
    
    return {"message": "Analysis queued"}


def _build_wav(pcm_data: bytes, sample_rate: int = 24000, channels: int = 1, bits_per_sample: int = 16) -> io.BytesIO:
    """Build a WAV file from raw PCM data."""
    data_size = len(pcm_data)
    byte_rate = sample_rate * channels * bits_per_sample // 8
    block_align = channels * bits_per_sample // 8

    wav_buf = io.BytesIO()
    # RIFF header
    wav_buf.write(b"RIFF")
    wav_buf.write(struct.pack("<I", data_size + 36))
    wav_buf.write(b"WAVE")
    # fmt subchunk
    wav_buf.write(b"fmt ")
    wav_buf.write(struct.pack("<I", 16))  # subchunk size
    wav_buf.write(struct.pack("<H", 1))   # PCM
    wav_buf.write(struct.pack("<H", channels))
    wav_buf.write(struct.pack("<I", sample_rate))
    wav_buf.write(struct.pack("<I", byte_rate))
    wav_buf.write(struct.pack("<H", block_align))
    wav_buf.write(struct.pack("<H", bits_per_sample))
    # data subchunk
    wav_buf.write(b"data")
    wav_buf.write(struct.pack("<I", data_size))
    wav_buf.write(pcm_data)
    wav_buf.seek(0)
    return wav_buf


def _mix_stereo(input_pcm: bytes, output_pcm: bytes) -> bytes:
    """
    Mix input (customer) and output (agent) mono PCM16 streams into a stereo PCM16 stream.
    Left channel = customer, Right channel = agent.
    Pads the shorter stream with silence.
    """
    # Each sample is 2 bytes (16-bit)
    input_samples = len(input_pcm) // 2
    output_samples = len(output_pcm) // 2
    max_samples = max(input_samples, output_samples)

    # Pad shorter stream with silence
    input_padded = input_pcm + b"\x00\x00" * (max_samples - input_samples)
    output_padded = output_pcm + b"\x00\x00" * (max_samples - output_samples)

    # Interleave: L(customer) R(agent) L R ...
    stereo = bytearray(max_samples * 4)  # 2 channels * 2 bytes per sample
    for i in range(max_samples):
        offset_mono = i * 2
        offset_stereo = i * 4
        stereo[offset_stereo:offset_stereo + 2] = input_padded[offset_mono:offset_mono + 2]
        stereo[offset_stereo + 2:offset_stereo + 4] = output_padded[offset_mono:offset_mono + 2]

    return bytes(stereo)


@router.get("/{call_uuid}/download")
async def download_call_recording(
    call_uuid: str,
    channel: Optional[str] = Query("stereo", description="Channel: input (customer), output (agent), or stereo (both)"),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Download recording for a call by UUID.
    Audio is stored in Redis during the call.
    
    channel options:
    - "input": Customer audio only (mono)
    - "output": Agent/AI audio only (mono)
    - "stereo": Both channels mixed (L=customer, R=agent)
    """
    try:
        redis = await aioredis.from_url(REDIS_URL, decode_responses=False)

        input_key = f"call_audio_input:{call_uuid}"
        output_key = f"call_audio_output:{call_uuid}"

        input_data = await redis.get(input_key)
        output_data = await redis.get(output_key)

        # Backward compatibility: try old key format
        if not output_data:
            legacy_key = f"call_audio:{call_uuid}"
            output_data = await redis.get(legacy_key)

        await redis.close()

        if not input_data and not output_data:
            raise HTTPException(status_code=404, detail="Recording not found or expired")

        sample_rate = 24000

        if channel == "input":
            if not input_data:
                raise HTTPException(status_code=404, detail="Customer audio not available")
            wav_file = _build_wav(input_data, sample_rate, channels=1)
            filename = f"recording-{call_uuid}-customer.wav"

        elif channel == "output":
            if not output_data:
                raise HTTPException(status_code=404, detail="Agent audio not available")
            wav_file = _build_wav(output_data, sample_rate, channels=1)
            filename = f"recording-{call_uuid}-agent.wav"

        else:  # stereo (default)
            # If only one channel available, return it as mono
            if input_data and output_data:
                stereo_pcm = _mix_stereo(input_data, output_data)
                wav_file = _build_wav(stereo_pcm, sample_rate, channels=2)
                filename = f"recording-{call_uuid}-stereo.wav"
            elif output_data:
                wav_file = _build_wav(output_data, sample_rate, channels=1)
                filename = f"recording-{call_uuid}-agent.wav"
            elif input_data:
                wav_file = _build_wav(input_data, sample_rate, channels=1)
                filename = f"recording-{call_uuid}-customer.wav"
            else:
                raise HTTPException(status_code=404, detail="No audio available")

        return StreamingResponse(
            wav_file,
            media_type="audio/wav",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
