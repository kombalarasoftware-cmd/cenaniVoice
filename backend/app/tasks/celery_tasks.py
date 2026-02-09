"""
Celery Tasks for VoiceAI Platform
Handles background tasks for call management and campaign execution
"""

from celery import Celery, shared_task
from celery.utils.log import get_task_logger
from celery.exceptions import MaxRetriesExceededError
from datetime import datetime, timedelta
from typing import Optional
import asyncio
import traceback

from sqlalchemy import text
from app.core.config import settings

# Create Celery app
celery_app = Celery(
    "voiceai",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,  # 10 minutes max per task
    worker_prefetch_multiplier=1,  # One task at a time per worker
    worker_concurrency=10,  # 10 concurrent workers for calls
)

logger = get_task_logger(__name__)


class TransientError(Exception):
    """Transient error that can be retried"""
    pass


class PermanentError(Exception):
    """Permanent error that should not be retried"""
    pass


@shared_task(bind=True, max_retries=3, autoretry_for=(TransientError,), retry_backoff=True)
def make_call(self, call_data: dict):
    """
    Make a single outbound call

    Args:
        call_data: {
            "call_id": str,
            "phone_number": str,
            "customer_name": str,
            "agent_id": int,
            "campaign_id": int,
            "customer_data": dict
        }
    """
    from app.core.database import SessionLocal
    from app.models import Agent, Campaign, CallLog, PhoneNumber
    from app.models.models import CallStatus, CallOutcome

    db = SessionLocal()
    call_log: Optional[CallLog] = None

    try:
        call_id = call_data["call_id"]
        phone_number = call_data["phone_number"]
        customer_name = call_data.get("customer_name")
        agent_id = call_data["agent_id"]
        campaign_id = call_data["campaign_id"]
        customer_data = call_data.get("customer_data", {})

        logger.info(f"Making call {call_id} to {phone_number}")

        # Get agent config
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            raise PermanentError(f"Agent {agent_id} not found")

        # Create call log
        call_log = CallLog(
            call_sid=call_id,
            status=CallStatus.QUEUED,
            to_number=phone_number,
            customer_name=customer_name,
            campaign_id=campaign_id,
            agent_id=agent_id,
            started_at=datetime.utcnow()
        )
        db.add(call_log)
        db.commit()

        # Build agent config dict
        agent_config = {
            "voice": agent.voice,
            "language": agent.language,
            "temperature": agent.temperature,
            "vad_threshold": agent.vad_threshold,
            "prompt_role": agent.prompt_role,
            "prompt_personality": agent.prompt_personality,
            "prompt_language": agent.prompt_language,
            "prompt_flow": agent.prompt_flow,
            "prompt_tools": agent.prompt_tools,
            "prompt_safety": agent.prompt_safety,
            "prompt_rules": agent.prompt_rules,
            "record_calls": agent.record_calls,
            "human_transfer": agent.human_transfer,
            "max_duration": agent.max_duration,
        }

        # Make the call
        async def execute_call():
            from app.services import AudioBridge, ARIConfig

            bridge = AudioBridge(
                openai_api_key=settings.OPENAI_API_KEY,
                asterisk_config=ARIConfig(
                    host=settings.ASTERISK_HOST,
                    port=settings.ASTERISK_ARI_PORT,
                    username=settings.ASTERISK_ARI_USER,
                    password=settings.ASTERISK_ARI_PASSWORD
                ),
                on_call_complete=lambda session: handle_call_complete(session, db, call_log)
            )

            await bridge.start()

            channel_id = await bridge.originate_call(
                call_id=call_id,
                phone_number=phone_number,
                customer_name=customer_name or "",
                agent_config=agent_config,
                customer_data=customer_data
            )

            # Update call log
            call_log.status = CallStatus.RINGING
            db.commit()

            # Wait for call to complete (with timeout)
            timeout = agent.max_duration + 60
            start_time = datetime.utcnow()

            while channel_id in bridge.sessions:
                await asyncio.sleep(1)
                if (datetime.utcnow() - start_time).seconds > timeout:
                    await bridge.hangup_call(channel_id)
                    break

            await bridge.stop()

        # Run async code
        asyncio.run(execute_call())

        logger.info(f"Call {call_id} completed")
        return {"success": True, "call_id": call_id}

    except PermanentError as e:
        # Don't retry permanent errors
        logger.error(f"Permanent error in call: {e}")
        if call_log:
            call_log.status = CallStatus.FAILED
            call_log.ended_at = datetime.utcnow()
            db.commit()
        return {"success": False, "error": str(e), "permanent": True}

    except TransientError as e:
        # Let Celery handle retry
        logger.warning(f"Transient error in call (will retry): {e}")
        raise

    except Exception as e:
        # Log full traceback for unexpected errors
        logger.error(f"Unexpected error in call: {e}\n{traceback.format_exc()}")

        # Update call log on failure
        if call_log:
            call_log.status = CallStatus.FAILED
            call_log.ended_at = datetime.utcnow()
            db.commit()

        # Retry for network-like errors
        if self.request.retries < self.max_retries:
            try:
                raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
            except MaxRetriesExceededError:
                logger.error(f"Max retries exceeded for call {call_data.get('call_id')}")

        return {"success": False, "error": str(e)}

    finally:
        db.close()


def handle_call_complete(session, db, call_log):
    """Handle call completion callback with atomic updates"""
    from app.models.models import CallStatus, CallOutcome
    from app.models import Campaign

    try:
        call_log.status = CallStatus.COMPLETED
        call_log.ended_at = datetime.utcnow()

        if session.connected_at:
            call_log.connected_at = session.connected_at
            call_log.duration = int((session.ended_at - session.connected_at).total_seconds())

        # Set outcome
        outcome_map = {
            "success": CallOutcome.SUCCESS,
            "transferred": CallOutcome.TRANSFERRED,
            "callback": CallOutcome.CALLBACK_SCHEDULED,
            "no_interest": CallOutcome.SUCCESS,
            "wrong_number": CallOutcome.FAILED,
            "error": CallOutcome.FAILED
        }
        call_log.outcome = outcome_map.get(session.outcome, CallOutcome.SUCCESS)

        # Save transcription
        if session.transcription:
            call_log.transcription = "\n".join([
                f"{t['role'].upper()}: {t['text']}"
                for t in session.transcription
            ])

        call_log.summary = session.summary

        # Payment promise
        if session.payment_promise:
            call_log.payment_promise_amount = session.payment_promise.get("amount")
            if session.payment_promise.get("date"):
                call_log.payment_promise_date = datetime.strptime(
                    session.payment_promise["date"], "%Y-%m-%d"
                )

        # Callback scheduled
        if session.callback_scheduled:
            call_log.callback_scheduled = datetime.strptime(
                session.callback_scheduled, "%Y-%m-%d %H:%M"
            )

        # Update campaign stats with ATOMIC operations to prevent race condition
        if call_log.campaign_id:
            # Use SQL UPDATE with atomic increment instead of read-modify-write
            db.execute(
                text("""
                UPDATE campaigns
                SET completed_calls = completed_calls + 1,
                    active_calls = GREATEST(active_calls - 1, 0),
                    successful_calls = successful_calls + :success_increment,
                    failed_calls = failed_calls + :failed_increment
                WHERE id = :campaign_id
                """),
                {
                    "campaign_id": call_log.campaign_id,
                    "success_increment": 1 if call_log.outcome == CallOutcome.SUCCESS else 0,
                    "failed_increment": 1 if call_log.outcome == CallOutcome.FAILED else 0,
                }
            )

        db.commit()

    except Exception as e:
        logger.error(f"Error in handle_call_complete: {e}\n{traceback.format_exc()}")
        db.rollback()
        raise


@shared_task
def start_campaign_calls(campaign_id: int):
    """
    Start processing calls for a campaign
    """
    from app.core.database import SessionLocal
    from app.models import Campaign, PhoneNumber, NumberList
    from app.models.models import CampaignStatus

    db = SessionLocal()

    try:
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            logger.error(f"Campaign {campaign_id} not found")
            return

        if campaign.status != CampaignStatus.RUNNING:
            logger.info(f"Campaign {campaign_id} is not running")
            return

        # Get phone numbers to call
        max_retries = campaign.agent.max_retries if campaign.agent else 3
        numbers = db.query(PhoneNumber).filter(
            PhoneNumber.number_list_id == campaign.number_list_id,
            PhoneNumber.is_valid == True,
            PhoneNumber.call_attempts < max_retries
        ).all()

        logger.info(f"Campaign {campaign_id}: {len(numbers)} numbers to call")

        # Check call hours with null safety
        now = datetime.now()

        call_hours_start = campaign.call_hours_start or "09:00"
        call_hours_end = campaign.call_hours_end or "20:00"

        try:
            start_hour, start_min = map(int, call_hours_start.split(":"))
            end_hour, end_min = map(int, call_hours_end.split(":"))
        except (ValueError, AttributeError):
            logger.warning(f"Invalid call hours format for campaign {campaign_id}, using defaults")
            start_hour, start_min = 9, 0
            end_hour, end_min = 20, 0

        call_start = now.replace(hour=start_hour, minute=start_min, second=0, microsecond=0)
        call_end = now.replace(hour=end_hour, minute=end_min, second=0, microsecond=0)

        if not (call_start <= now <= call_end):
            logger.info(f"Campaign {campaign_id}: Outside call hours")
            return

        # Check active day
        active_days = campaign.active_days or [1, 2, 3, 4, 5]
        if now.isoweekday() not in active_days:
            logger.info(f"Campaign {campaign_id}: Not an active day")
            return

        # Queue calls respecting concurrent limit
        import uuid

        active_tasks = campaign.active_calls
        available_slots = campaign.concurrent_calls - active_tasks

        for number in numbers[:available_slots]:
            call_id = str(uuid.uuid4())

            # Queue the call
            make_call.delay({  # type: ignore[attr-defined]
                "call_id": call_id,
                "phone_number": number.phone,
                "customer_name": number.name,
                "agent_id": campaign.agent_id,
                "campaign_id": campaign.id,
                "customer_data": number.custom_data or {}
            })

            # Update number with atomic increment
            db.execute(
                text("""
                UPDATE phone_numbers
                SET call_attempts = call_attempts + 1,
                    last_call_at = :now
                WHERE id = :number_id
                """),
                {"number_id": number.id, "now": datetime.utcnow()}
            )

            # Update campaign active calls atomically
            db.execute(
                text("""
                UPDATE campaigns
                SET active_calls = active_calls + 1
                WHERE id = :campaign_id
                """),
                {"campaign_id": campaign.id}
            )

        db.commit()

        logger.info(f"Campaign {campaign_id}: Queued {min(len(numbers), available_slots)} calls")

    except Exception as e:
        logger.error(f"Error in start_campaign_calls: {e}\n{traceback.format_exc()}")
        db.rollback()

    finally:
        db.close()


@shared_task
def process_campaign_batch():
    """
    Periodic task to process all running campaigns
    Run every 30 seconds to maintain call volume
    """
    from app.core.database import SessionLocal
    from app.models import Campaign
    from app.models.models import CampaignStatus

    db = SessionLocal()

    try:
        campaigns = db.query(Campaign).filter(
            Campaign.status == CampaignStatus.RUNNING
        ).all()

        for campaign in campaigns:
            start_campaign_calls.delay(campaign.id)  # type: ignore[attr-defined]

        logger.info(f"Processing {len(campaigns)} running campaigns")

    except Exception as e:
        logger.error(f"Error in process_campaign_batch: {e}\n{traceback.format_exc()}")

    finally:
        db.close()


@shared_task
def check_campaign_completion():
    """
    Check if campaigns are complete
    Run every minute
    """
    from app.core.database import SessionLocal
    from app.models import Campaign
    from app.models.models import CampaignStatus

    db = SessionLocal()

    try:
        campaigns = db.query(Campaign).filter(
            Campaign.status == CampaignStatus.RUNNING
        ).all()

        for campaign in campaigns:
            if campaign.completed_calls >= campaign.total_numbers:
                campaign.status = CampaignStatus.COMPLETED
                logger.info(f"Campaign {campaign.id} completed")

        db.commit()

    except Exception as e:
        logger.error(f"Error in check_campaign_completion: {e}\n{traceback.format_exc()}")
        db.rollback()

    finally:
        db.close()


@shared_task
def transcribe_recording(call_id: int):
    """
    Transcribe a call recording using Whisper
    """
    from app.core.database import SessionLocal
    from app.models import CallLog
    import openai
    import boto3

    db = SessionLocal()

    try:
        call = db.query(CallLog).filter(CallLog.id == call_id).first()
        if not call or not call.recording_url:
            logger.warning(f"Call {call_id} not found or no recording URL")
            return {"success": False, "reason": "no_recording"}

        # Download recording from MinIO
        s3_client = boto3.client(
            's3',
            endpoint_url=f"http://{settings.MINIO_ENDPOINT}",
            aws_access_key_id=settings.MINIO_ACCESS_KEY,
            aws_secret_access_key=settings.MINIO_SECRET_KEY
        )

        # Extract file path from URL
        recording_key = call.recording_url.split("/")[-1]

        # Download to temp file
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            s3_client.download_file(
                settings.MINIO_BUCKET_RECORDINGS,
                recording_key,
                tmp_file.name
            )
            tmp_path = tmp_file.name

        # Transcribe with Whisper
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

        with open(tmp_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="tr"  # Turkish
            )

        # Update call log
        call.transcription = transcript.text
        db.commit()

        # Cleanup temp file
        import os
        os.unlink(tmp_path)

        logger.info(f"Transcribed call {call_id}")
        return {"success": True, "call_id": call_id}

    except Exception as e:
        logger.error(f"Error transcribing call {call_id}: {e}\n{traceback.format_exc()}")
        return {"success": False, "error": str(e)}

    finally:
        db.close()


@shared_task
def analyze_call_sentiment(call_id: int):
    """
    Analyze call sentiment and extract intents
    """
    from app.core.database import SessionLocal
    from app.models import CallLog
    import openai

    db = SessionLocal()

    try:
        call = db.query(CallLog).filter(CallLog.id == call_id).first()
        if not call or not call.transcription:
            return {"success": False, "reason": "no_transcription"}

        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """Analyze the following call transcription and provide:
                    1. Overall sentiment (positive, neutral, negative)
                    2. Customer intent
                    3. Brief summary (1-2 sentences)

                    Respond in JSON format:
                    {"sentiment": "...", "intent": "...", "summary": "..."}"""
                },
                {"role": "user", "content": call.transcription}
            ],
            response_format={"type": "json_object"}
        )

        import json
        content = response.choices[0].message.content
        if content is None:
            logger.warning(f"No content in AI response for call {call_id}")
            return {"success": False, "reason": "no_content"}

        result = json.loads(content)

        call.sentiment = result.get("sentiment")
        call.intent = result.get("intent")
        if not call.summary:
            call.summary = result.get("summary")

        db.commit()

        logger.info(f"Analyzed call {call_id}: {result}")
        return {"success": True, "result": result}

    except Exception as e:
        logger.error(f"Error analyzing call {call_id}: {e}\n{traceback.format_exc()}")
        return {"success": False, "error": str(e)}

    finally:
        db.close()


@shared_task(bind=True, max_retries=3)
def send_webhook(self, webhook_id: int, event: str, data: dict):
    """
    Send webhook notification with retry logic
    """
    from app.core.database import SessionLocal
    from app.models import WebhookEndpoint
    import httpx
    import hmac
    import hashlib
    import json

    db = SessionLocal()
    webhook = None

    try:
        webhook = db.query(WebhookEndpoint).filter(WebhookEndpoint.id == webhook_id).first()
        if not webhook or not webhook.is_active:
            return {"success": False, "reason": "webhook_inactive"}

        webhook_events = webhook.events or []
        if event not in webhook_events:
            return {"success": False, "reason": "event_not_subscribed"}

        payload = {
            "event": event,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data
        }

        # Create signature
        payload_str = json.dumps(payload, sort_keys=True)
        secret_key = webhook.secret or ""
        signature = hmac.new(
            secret_key.encode(),
            payload_str.encode(),
            hashlib.sha256
        ).hexdigest()

        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Signature": signature,
            "X-Webhook-Event": event
        }

        # Send request with timeout
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                webhook.url,
                json=payload,
                headers=headers
            )

        # Update stats atomically
        success = response.status_code < 400

        db.execute(
            text("""
            UPDATE webhook_endpoints
            SET total_deliveries = total_deliveries + 1,
                failed_deliveries = failed_deliveries + :failed_increment,
                last_delivery_at = :now,
                last_error = :error
            WHERE id = :webhook_id
            """),
            {
                "webhook_id": webhook_id,
                "failed_increment": 0 if success else 1,
                "now": datetime.utcnow(),
                "error": None if success else f"HTTP {response.status_code}"
            }
        )
        db.commit()

        if not success:
            raise TransientError(f"Webhook returned HTTP {response.status_code}")

        return {"success": True}

    except (httpx.TimeoutException, httpx.ConnectError) as e:
        # Network errors are retryable
        logger.warning(f"Webhook network error: {e}")
        if webhook:
            db.execute(
                text("""
                UPDATE webhook_endpoints
                SET failed_deliveries = failed_deliveries + 1,
                    last_error = :error
                WHERE id = :webhook_id
                """),
                {"webhook_id": webhook_id, "error": str(e)}
            )
            db.commit()

        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))

    except Exception as e:
        logger.error(f"Webhook error: {e}\n{traceback.format_exc()}")
        if webhook:
            db.execute(
                text("""
                UPDATE webhook_endpoints
                SET failed_deliveries = failed_deliveries + 1,
                    last_error = :error
                WHERE id = :webhook_id
                """),
                {"webhook_id": webhook_id, "error": str(e)}
            )
            db.commit()

        return {"success": False, "error": str(e)}

    finally:
        db.close()


# Celery Beat Schedule
celery_app.conf.beat_schedule = {
    "process-campaigns": {
        "task": "app.tasks.celery_tasks.process_campaign_batch",
        "schedule": 30.0,  # Every 30 seconds
    },
    "check-completion": {
        "task": "app.tasks.celery_tasks.check_campaign_completion",
        "schedule": 60.0,  # Every minute
    },
}
