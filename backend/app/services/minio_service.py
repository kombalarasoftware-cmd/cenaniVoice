"""
MinIO Object Storage Service

Provides centralized MinIO/S3 operations for the VoiceAI platform:
- Bucket management (create, check)
- File upload/download
- Presigned URL generation
- Recording management (Redis audio → WAV → MinIO)
"""

import io
import struct
import logging
from typing import Optional, BinaryIO

import boto3
from botocore.exceptions import ClientError

from app.core.config import settings

logger = logging.getLogger(__name__)


class MinIOService:
    """Centralized MinIO/S3 client for all storage operations."""

    def __init__(self):
        self._client = None

    @property
    def client(self):
        """Lazy-init S3 client."""
        if self._client is None:
            self._client = boto3.client(
                "s3",
                endpoint_url=f"http://{settings.MINIO_ENDPOINT}",
                aws_access_key_id=settings.MINIO_ACCESS_KEY,
                aws_secret_access_key=settings.MINIO_SECRET_KEY,
                region_name="us-east-1",
            )
        return self._client

    # ------------------------------------------------------------------
    # Bucket Management
    # ------------------------------------------------------------------

    def ensure_buckets(self) -> dict[str, bool]:
        """
        Create required buckets if they don't exist.
        Returns dict of bucket_name -> created (True) or already_exists (False).
        """
        buckets = [
            settings.MINIO_BUCKET_RECORDINGS,
            settings.MINIO_BUCKET_EXPORTS,
        ]
        results = {}
        for bucket in buckets:
            try:
                self.client.head_bucket(Bucket=bucket)
                results[bucket] = False  # already exists
                logger.debug(f"Bucket '{bucket}' already exists")
            except ClientError as e:
                error_code = int(e.response["Error"]["Code"])
                if error_code == 404:
                    try:
                        self.client.create_bucket(Bucket=bucket)
                        results[bucket] = True
                        logger.info(f"Created bucket '{bucket}'")
                    except Exception as create_err:
                        logger.error(f"Failed to create bucket '{bucket}': {create_err}")
                        results[bucket] = False
                else:
                    logger.error(f"Error checking bucket '{bucket}': {e}")
                    results[bucket] = False
        return results

    # ------------------------------------------------------------------
    # Upload / Download
    # ------------------------------------------------------------------

    def upload_bytes(
        self,
        bucket: str,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        """
        Upload bytes to MinIO. Returns the object key.
        """
        self.client.put_object(
            Bucket=bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        logger.info(f"Uploaded {len(data)} bytes → {bucket}/{key}")
        return key

    def upload_file(
        self,
        bucket: str,
        key: str,
        file_obj: BinaryIO,
        content_type: str = "application/octet-stream",
    ) -> str:
        """
        Upload a file-like object to MinIO. Returns the object key.
        """
        self.client.upload_fileobj(
            file_obj,
            bucket,
            key,
            ExtraArgs={"ContentType": content_type},
        )
        logger.info(f"Uploaded file → {bucket}/{key}")
        return key

    def download_bytes(self, bucket: str, key: str) -> Optional[bytes]:
        """
        Download an object from MinIO as bytes.
        Returns None if not found.
        """
        try:
            response = self.client.get_object(Bucket=bucket, Key=key)
            return response["Body"].read()
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                logger.warning(f"Object not found: {bucket}/{key}")
                return None
            raise

    def get_presigned_url(
        self,
        bucket: str,
        key: str,
        expires_in: int = 3600,
    ) -> Optional[str]:
        """
        Generate a presigned download URL.
        expires_in: seconds until URL expires (default 1 hour).
        """
        try:
            url = self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": key},
                ExpiresIn=expires_in,
            )
            return url
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL for {bucket}/{key}: {e}")
            return None

    def delete_object(self, bucket: str, key: str) -> bool:
        """Delete an object from MinIO."""
        try:
            self.client.delete_object(Bucket=bucket, Key=key)
            logger.info(f"Deleted {bucket}/{key}")
            return True
        except ClientError as e:
            logger.error(f"Failed to delete {bucket}/{key}: {e}")
            return False

    def object_exists(self, bucket: str, key: str) -> bool:
        """Check if an object exists in MinIO."""
        try:
            self.client.head_object(Bucket=bucket, Key=key)
            return True
        except ClientError:
            return False

    def list_objects(
        self,
        bucket: str,
        prefix: str = "",
        max_keys: int = 1000,
    ) -> list[dict]:
        """List objects in a bucket with optional prefix filter."""
        try:
            response = self.client.list_objects_v2(
                Bucket=bucket,
                Prefix=prefix,
                MaxKeys=max_keys,
            )
            return [
                {
                    "key": obj["Key"],
                    "size": obj["Size"],
                    "last_modified": obj["LastModified"].isoformat(),
                }
                for obj in response.get("Contents", [])
            ]
        except ClientError as e:
            logger.error(f"Failed to list objects in {bucket}: {e}")
            return []

    # ------------------------------------------------------------------
    # Audio / Recording Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def pcm_to_wav(pcm_data: bytes, sample_rate: int = 8000, channels: int = 1, sample_width: int = 2) -> bytes:
        """
        Convert raw PCM audio data to WAV format.
        Default: 8kHz, mono, 16-bit (standard telephony).
        """
        data_size = len(pcm_data)
        # WAV header: 44 bytes
        header = struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF",
            36 + data_size,           # File size - 8
            b"WAVE",
            b"fmt ",
            16,                        # Chunk size
            1,                         # PCM format
            channels,
            sample_rate,
            sample_rate * channels * sample_width,  # Byte rate
            channels * sample_width,   # Block align
            sample_width * 8,          # Bits per sample
            b"data",
            data_size,
        )
        return header + pcm_data

    async def save_recording_from_redis(
        self,
        call_uuid: str,
        sample_rate: int = 8000,
    ) -> Optional[str]:
        """
        Fetch audio buffers from Redis, merge into WAV, upload to MinIO.
        Returns the recording key (path) or None if no audio data.
        """
        import redis.asyncio as redis_async

        redis_url = f"redis://:{settings.REDIS_PASSWORD}@redis:6379/0"
        r = redis_async.from_url(redis_url, decode_responses=False)

        try:
            # Fetch input (customer) and output (agent) audio
            input_key = f"call_audio_input:{call_uuid}"
            output_key = f"call_audio_output:{call_uuid}"

            input_audio = await r.get(input_key) or b""
            output_audio = await r.get(output_key) or b""

            if not input_audio and not output_audio:
                logger.info(f"[{call_uuid[:8]}] No audio data in Redis, skipping recording")
                return None

            # Mix input and output audio (simple interleave for stereo,
            # or use the longer one for mono)
            # For simplicity, combine both channels into a single mono mix
            combined = self._mix_audio(input_audio, output_audio)

            # Convert to WAV
            wav_data = self.pcm_to_wav(combined, sample_rate=sample_rate)

            # Upload to MinIO
            recording_key = f"calls/{call_uuid}.wav"
            self.upload_bytes(
                bucket=settings.MINIO_BUCKET_RECORDINGS,
                key=recording_key,
                data=wav_data,
                content_type="audio/wav",
            )

            # Calculate duration
            duration_secs = len(combined) / (sample_rate * 2)  # 16-bit = 2 bytes/sample
            logger.info(
                f"[{call_uuid[:8]}] 🎙️ Recording saved to MinIO: "
                f"{recording_key} ({len(wav_data)} bytes, {duration_secs:.1f}s)"
            )

            # Cleanup Redis audio buffers
            await r.delete(input_key, output_key)
            logger.debug(f"[{call_uuid[:8]}] Redis audio buffers cleaned up")

            return recording_key

        except Exception as e:
            logger.error(f"[{call_uuid[:8]}] Failed to save recording: {e}")
            return None
        finally:
            await r.close()

    @staticmethod
    def _mix_audio(input_audio: bytes, output_audio: bytes) -> bytes:
        """
        Mix two PCM16 mono streams into one mono stream.
        If one is shorter, pads with silence.
        """
        # Ensure even length (16-bit samples = 2 bytes each)
        if len(input_audio) % 2 != 0:
            input_audio = input_audio[:-1]
        if len(output_audio) % 2 != 0:
            output_audio = output_audio[:-1]

        # If only one channel has data, return it directly
        if not input_audio:
            return output_audio
        if not output_audio:
            return input_audio

        # Mix by averaging samples
        import array

        in_samples = array.array("h")
        in_samples.frombytes(input_audio)

        out_samples = array.array("h")
        out_samples.frombytes(output_audio)

        # Pad shorter array
        max_len = max(len(in_samples), len(out_samples))
        while len(in_samples) < max_len:
            in_samples.append(0)
        while len(out_samples) < max_len:
            out_samples.append(0)

        # Mix (average with clipping protection)
        mixed = array.array("h")
        for i in range(max_len):
            sample = (in_samples[i] + out_samples[i]) // 2
            mixed.append(max(-32768, min(32767, sample)))

        return mixed.tobytes()


# Singleton instance
minio_service = MinIOService()
