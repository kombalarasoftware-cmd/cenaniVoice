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
import threading
import traceback

from sqlalchemy import text
from app.core.config import settings


# ---------------------------------------------------------------------------
# Circuit Breaker — per-provider failure tracking (in-memory, per-worker)
# ---------------------------------------------------------------------------

_circuit_lock = threading.Lock()
_circuit_state: dict = {}  # {"openai": {"failures": 0, "open_until": None}, ...}

CIRCUIT_FAILURE_THRESHOLD = 5   # consecutive failures to open circuit
CIRCUIT_COOLDOWN_SECONDS = 30   # seconds before retrying after circuit opens


def _circuit_is_open(provider: str) -> bool:
    """Check if the circuit breaker is open for a provider."""
    with _circuit_lock:
        state = _circuit_state.get(provider)
        if not state:
            return False
        if state.get("open_until") and datetime.utcnow() < state["open_until"]:
            return True
        # Cooldown expired — half-open, allow next attempt
        if state.get("open_until") and datetime.utcnow() >= state["open_until"]:
            state["failures"] = 0
            state["open_until"] = None
        return False


def _circuit_record_success(provider: str) -> None:
    """Record a successful call, resetting the failure counter."""
    with _circuit_lock:
        _circuit_state[provider] = {"failures": 0, "open_until": None}


def _circuit_record_failure(provider: str) -> None:
    """Record a failure; open the circuit if threshold is reached."""
    with _circuit_lock:
        state = _circuit_state.setdefault(provider, {"failures": 0, "open_until": None})
        state["failures"] += 1
        if state["failures"] >= CIRCUIT_FAILURE_THRESHOLD:
            state["open_until"] = datetime.utcnow() + timedelta(seconds=CIRCUIT_COOLDOWN_SECONDS)
            logger.warning(
                f"Circuit breaker OPEN for provider '{provider}' — "
                f"{state['failures']} consecutive failures, cooldown {CIRCUIT_COOLDOWN_SECONDS}s"
            )

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

        # Make the call using the provider factory
        async def execute_call():
            from app.services.provider_factory import get_provider

            provider_type = getattr(agent, "provider", "openai") or "openai"

            # Circuit breaker check
            if _circuit_is_open(provider_type):
                raise TransientError(
                    f"Circuit breaker open for provider '{provider_type}' — skipping call"
                )

            provider = get_provider(provider_type)

            # Update call log status
            call_log.status = CallStatus.RINGING
            call_log.provider = provider_type
            db.commit()

            result = await provider.initiate_call(
                agent=agent,
                phone_number=phone_number,
                caller_id=phone_number,
                customer_name=customer_name or "",
                customer_title="",
                conversation_history="",
                variables={"campaign_id": str(campaign_id)},
            )

            # Update call log with provider result
            if result.get("call_id"):
                call_log.call_sid = result["call_id"]
            if result.get("ultravox_call_id"):
                call_log.ultravox_call_id = result["ultravox_call_id"]
            db.commit()

        # Run async code
        asyncio.run(execute_call())

        # Record provider success for circuit breaker
        _provider = getattr(agent, "provider", "openai") or "openai"
        _circuit_record_success(_provider)

        logger.info(f"Call {call_id} completed")
        return {"success": True, "call_id": call_id}

    except PermanentError as e:
        # Don't retry permanent errors
        logger.error(f"Permanent error in call: {e}")
        if call_log:
            call_log.status = CallStatus.FAILED
            call_log.ended_at = datetime.utcnow()
            db.commit()
        return {"success": False, "error": "Call processing failed", "permanent": True}

    except TransientError as e:
        # Let Celery handle retry
        logger.warning(f"Transient error in call (will retry): {e}")
        raise

    except Exception as e:
        # Log full traceback for unexpected errors
        logger.error(f"Unexpected error in call: {e}\n{traceback.format_exc()}")

        # Record provider failure for circuit breaker
        _provider = "openai"
        if call_log and call_log.provider:
            _provider = call_log.provider
        _circuit_record_failure(_provider)

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

        return {"success": False, "error": "Call processing failed"}

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

        # Update agent statistics (total_calls, successful_calls, avg_duration)
        if call_log.agent_id:
            call_duration = call_log.duration or 0
            db.execute(
                text("""
                UPDATE agents
                SET total_calls = total_calls + 1,
                    successful_calls = successful_calls + :success_increment,
                    avg_duration = CASE
                        WHEN total_calls = 0 THEN :duration
                        ELSE (avg_duration * total_calls + :duration) / (total_calls + 1)
                    END
                WHERE id = :agent_id
                """),
                {
                    "agent_id": call_log.agent_id,
                    "success_increment": 1 if call_log.outcome == CallOutcome.SUCCESS else 0,
                    "duration": float(call_duration),
                }
            )

        db.commit()

        # Trigger Ultravox post-call data persistence (transcript + recording)
        if call_log.provider == "ultravox" and call_log.ultravox_call_id:
            try:
                persist_ultravox_call_data.apply_async(
                    args=[call_log.id],
                    countdown=5,  # Wait 5s for Ultravox to finalize data
                )
                logger.info(f"Queued persist_ultravox_call_data for call {call_log.id}")
            except Exception as pq_err:
                logger.warning(f"Failed to queue persist_ultravox_call_data: {pq_err}")

    except Exception as e:
        logger.error(f"Error in handle_call_complete: {e}\n{traceback.format_exc()}")
        db.rollback()
        raise


@shared_task
def load_hopper(campaign_id: int):
    """
    Load the dial hopper for a campaign from its assigned dial lists.

    Queries DialListEntries from all active CampaignLists for the campaign.
    Filters for dialable entries (NEW or CALLBACK-ready, non-DNC).
    Limits hopper size to 2x concurrent_calls to avoid memory bloat.
    """
    from app.core.database import SessionLocal
    from app.models.models import (
        Campaign, CampaignList, DialListEntry, DialHopper, DNCList,
        CampaignStatus, DialEntryStatus,
    )

    db = SessionLocal()

    try:
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign or campaign.status != CampaignStatus.RUNNING:
            return

        # How many entries should be in the hopper at most
        hopper_limit = (campaign.concurrent_calls or 10) * 2

        # Count current waiting entries in hopper
        current_waiting = (
            db.query(DialHopper)
            .filter(DialHopper.campaign_id == campaign_id, DialHopper.status == "waiting")
            .count()
        )

        slots_needed = hopper_limit - current_waiting
        if slots_needed <= 0:
            return

        # Get active list IDs for this campaign
        active_list_ids = [
            row[0]
            for row in db.query(CampaignList.list_id)
            .filter(CampaignList.campaign_id == campaign_id, CampaignList.active == True)
            .all()
        ]

        if not active_list_ids:
            # Fallback: use legacy number_list_id if no campaign_lists assigned
            logger.info(f"Campaign {campaign_id}: No campaign_lists, skipping hopper load")
            return

        # Pre-load DNC numbers
        dnc_numbers = set(row[0] for row in db.query(DNCList.phone_number).all())

        # IDs already in the hopper to avoid duplicates
        hopper_entry_ids = set(
            row[0]
            for row in db.query(DialHopper.entry_id)
            .filter(DialHopper.campaign_id == campaign_id, DialHopper.status.in_(["waiting", "dialing"]))
            .all()
        )

        now = datetime.utcnow()

        # Query dialable entries: NEW or (CALLBACK with next_callback_at <= now)
        entries = (
            db.query(DialListEntry)
            .filter(
                DialListEntry.list_id.in_(active_list_ids),
                DialListEntry.dnc_flag == False,
                DialListEntry.call_attempts < DialListEntry.max_attempts,
                DialListEntry.id.notin_(hopper_entry_ids) if hopper_entry_ids else True,
            )
            .filter(
                (DialListEntry.status == DialEntryStatus.NEW)
                | (
                    (DialListEntry.status == DialEntryStatus.CALLBACK)
                    & (DialListEntry.next_callback_at <= now)
                )
            )
            .order_by(DialListEntry.priority.desc(), DialListEntry.id)
            .limit(slots_needed)
            .all()
        )

        inserted = 0
        for entry in entries:
            # Double-check DNC at insertion time
            if entry.phone_number in dnc_numbers:
                entry.dnc_flag = True
                entry.status = DialEntryStatus.DNC
                continue

            hopper_entry = DialHopper(
                campaign_id=campaign_id,
                entry_id=entry.id,
                priority=entry.priority,
                status="waiting",
            )
            db.add(hopper_entry)
            inserted += 1

        db.commit()
        logger.info(f"Campaign {campaign_id}: Loaded {inserted} entries into hopper")

    except Exception as e:
        logger.error(f"Error in load_hopper: {e}\n{traceback.format_exc()}")
        db.rollback()
    finally:
        db.close()


@shared_task
def start_campaign_calls(campaign_id: int):
    """
    Start processing calls for a campaign using the hopper system.

    Pulls entries from dial_hopper (status=waiting), creates call tasks,
    and records DialAttempt entries on completion.
    Falls back to legacy PhoneNumber query if no hopper entries found.
    """
    from app.core.database import SessionLocal
    from app.models import Campaign, PhoneNumber, NumberList, Agent
    from app.models.models import (
        CampaignStatus, DialHopper, DialListEntry, DialAttempt, DialEntryStatus,
    )

    db = SessionLocal()

    try:
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            logger.error(f"Campaign {campaign_id} not found")
            return

        if campaign.status != CampaignStatus.RUNNING:
            logger.info(f"Campaign {campaign_id} is not running")
            return

        # Check call hours
        now = datetime.now()

        call_hours_start = campaign.call_hours_start or "09:00"
        call_hours_end = campaign.call_hours_end or "20:00"

        try:
            start_hour, start_min = map(int, call_hours_start.split(":"))
            end_hour, end_min = map(int, call_hours_end.split(":"))
        except (ValueError, AttributeError):
            logger.warning(f"Invalid call hours for campaign {campaign_id}, using defaults")
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

        # Calculate available slots based on dialing mode
        active_tasks = campaign.active_calls or 0
        concurrent_limit = campaign.concurrent_calls or 10
        dialing_mode = getattr(campaign, "dialing_mode", "power") or "power"

        if dialing_mode == "progressive":
            # Progressive: only dial 1 call when no active calls (1:1 agent ratio)
            available_slots = 1 if active_tasks == 0 else 0
        else:
            # Power mode (default): fill up to concurrent limit
            available_slots = concurrent_limit - active_tasks

        if available_slots <= 0:
            return

        # Determine provider from agent settings
        provider_type = "openai"
        if campaign.agent:
            provider_type = getattr(campaign.agent, "provider", "openai") or "openai"

        # Circuit breaker check — skip campaign if provider is down
        if _circuit_is_open(provider_type):
            logger.warning(f"Campaign {campaign_id}: Circuit breaker open for {provider_type}, skipping")
            return

        # --- Try hopper-based dialing first ---
        hopper_entries = (
            db.query(DialHopper)
            .filter(DialHopper.campaign_id == campaign_id, DialHopper.status == "waiting")
            .order_by(DialHopper.priority.desc(), DialHopper.inserted_at)
            .limit(available_slots)
            .all()
        )

        if hopper_entries:
            import uuid

            queued = 0
            for hopper in hopper_entries:
                entry = db.get(DialListEntry, hopper.entry_id)
                if not entry:
                    hopper.status = "done"
                    continue

                call_id = str(uuid.uuid4())

                # Mark hopper entry as dialing
                hopper.status = "dialing"

                # Update the dial list entry
                entry.call_attempts += 1
                entry.last_attempt_at = datetime.utcnow()
                entry.status = DialEntryStatus.CONTACTED

                # Create DialAttempt record
                attempt = DialAttempt(
                    entry_id=entry.id,
                    campaign_id=campaign_id,
                    attempt_number=entry.call_attempts,
                    result="pending",
                    started_at=datetime.utcnow(),
                )
                db.add(attempt)
                db.flush()  # Get attempt.id

                # Build customer name from entry
                customer_name = " ".join(
                    filter(None, [entry.first_name, entry.last_name])
                ) or ""

                # Queue the call
                make_call.delay({  # type: ignore[attr-defined]
                    "call_id": call_id,
                    "phone_number": entry.phone_number,
                    "customer_name": customer_name,
                    "agent_id": campaign.agent_id,
                    "campaign_id": campaign.id,
                    "customer_data": entry.custom_fields or {},
                    "provider": provider_type,
                    "dial_attempt_id": attempt.id,
                    "hopper_id": hopper.id,
                    "entry_id": entry.id,
                })

                # Update campaign active calls atomically
                db.execute(
                    text("""
                    UPDATE campaigns
                    SET active_calls = active_calls + 1
                    WHERE id = :campaign_id
                    """),
                    {"campaign_id": campaign.id},
                )

                queued += 1

            db.commit()

            # Reload hopper if running low
            remaining = (
                db.query(DialHopper)
                .filter(DialHopper.campaign_id == campaign_id, DialHopper.status == "waiting")
                .count()
            )
            if remaining < (campaign.concurrent_calls or 10):
                load_hopper.delay(campaign_id)  # type: ignore[attr-defined]

            logger.info(f"Campaign {campaign_id}: Queued {queued} calls from hopper")
            return

        # --- Fallback: legacy PhoneNumber-based dialing ---
        if campaign.number_list_id:
            max_retries = campaign.agent.max_retries if campaign.agent else 3
            numbers = db.query(PhoneNumber).filter(
                PhoneNumber.number_list_id == campaign.number_list_id,
                PhoneNumber.is_valid == True,
                PhoneNumber.call_attempts < max_retries,
            ).all()

            import uuid

            for number in numbers[:available_slots]:
                call_id = str(uuid.uuid4())

                make_call.delay({  # type: ignore[attr-defined]
                    "call_id": call_id,
                    "phone_number": number.phone,
                    "customer_name": number.name,
                    "agent_id": campaign.agent_id,
                    "campaign_id": campaign.id,
                    "customer_data": number.custom_data or {},
                    "provider": provider_type,
                })

                db.execute(
                    text("""
                    UPDATE phone_numbers
                    SET call_attempts = call_attempts + 1,
                        last_call_at = :now
                    WHERE id = :number_id
                    """),
                    {"number_id": number.id, "now": datetime.utcnow()},
                )

                db.execute(
                    text("""
                    UPDATE campaigns
                    SET active_calls = active_calls + 1
                    WHERE id = :campaign_id
                    """),
                    {"campaign_id": campaign.id},
                )

            db.commit()
            logger.info(f"Campaign {campaign_id}: Queued {min(len(numbers), available_slots)} calls (legacy)")

    except Exception as e:
        logger.error(f"Error in start_campaign_calls: {e}\n{traceback.format_exc()}")
        db.rollback()

    finally:
        db.close()


@shared_task
def process_campaign_batch():
    """
    Periodic task to process all running campaigns.
    Run every 30 seconds to maintain call volume.
    Loads hopper first, then dispatches calls.
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
            # Ensure hopper is loaded before dispatching calls
            load_hopper.delay(campaign.id)  # type: ignore[attr-defined]
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

        # Download recording from MinIO using centralized service
        from app.services.minio_service import minio_service

        recording_key = call.recording_url
        recording_data = minio_service.download_bytes(
            settings.MINIO_BUCKET_RECORDINGS,
            recording_key,
        )

        if not recording_data:
            logger.warning(f"Recording not found in MinIO: {recording_key}")
            return {"success": False, "reason": "recording_not_found"}

        # Write to temp file for Whisper
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            tmp_file.write(recording_data)
            tmp_path = tmp_file.name

        # Transcribe with Whisper
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

        # Determine language from agent settings, default to English
        language = "en"
        if call.agent_id:
            from app.models import Agent
            agent = db.query(Agent).filter(Agent.id == call.agent_id).first()
            if agent and agent.language:
                language = agent.language

        with open(tmp_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language=language
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
        return {"success": False, "error": "Transcription failed"}

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
                {"webhook_id": webhook_id, "error": type(e).__name__}
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
                {"webhook_id": webhook_id, "error": type(e).__name__}
            )
            db.commit()

        return {"success": False, "error": "Webhook delivery failed"}

    finally:
        db.close()


@shared_task
def process_callbacks():
    """
    Periodic task to re-queue callback entries into the hopper.

    Every 5 minutes, checks for DialListEntries with status=CALLBACK
    and next_callback_at <= now, then adds them to the hopper for
    re-dialing.
    """
    from app.core.database import SessionLocal
    from app.models.models import (
        Campaign, CampaignList, DialListEntry, DialHopper,
        CampaignStatus, DialEntryStatus,
    )

    db = SessionLocal()

    try:
        now = datetime.utcnow()

        # Find all running campaigns
        running_campaigns = (
            db.query(Campaign)
            .filter(Campaign.status == CampaignStatus.RUNNING)
            .all()
        )

        total_requeued = 0

        for campaign in running_campaigns:
            # Get active list IDs for this campaign
            active_list_ids = [
                row[0]
                for row in db.query(CampaignList.list_id)
                .filter(CampaignList.campaign_id == campaign.id, CampaignList.active == True)
                .all()
            ]

            if not active_list_ids:
                continue

            # IDs already in the hopper
            hopper_entry_ids = set(
                row[0]
                for row in db.query(DialHopper.entry_id)
                .filter(
                    DialHopper.campaign_id == campaign.id,
                    DialHopper.status.in_(["waiting", "dialing"]),
                )
                .all()
            )

            # Find callback-ready entries
            callback_entries = (
                db.query(DialListEntry)
                .filter(
                    DialListEntry.list_id.in_(active_list_ids),
                    DialListEntry.status == DialEntryStatus.CALLBACK,
                    DialListEntry.next_callback_at <= now,
                    DialListEntry.dnc_flag == False,
                    DialListEntry.call_attempts < DialListEntry.max_attempts,
                    DialListEntry.id.notin_(hopper_entry_ids) if hopper_entry_ids else True,
                )
                .order_by(DialListEntry.priority.desc())
                .limit(50)  # Cap per campaign per cycle
                .all()
            )

            for entry in callback_entries:
                hopper_entry = DialHopper(
                    campaign_id=campaign.id,
                    entry_id=entry.id,
                    priority=entry.priority + 10,  # Boost priority for callbacks
                    status="waiting",
                )
                db.add(hopper_entry)
                total_requeued += 1

        db.commit()

        if total_requeued:
            logger.info(f"Callbacks: Re-queued {total_requeued} entries into hoppers")

    except Exception as e:
        logger.error(f"Error in process_callbacks: {e}\n{traceback.format_exc()}")
        db.rollback()
    finally:
        db.close()


@shared_task
def cleanup_orphan_calls():
    """
    Periodic task to find and clean up orphaned calls.

    Looks for calls stuck in RINGING or CONNECTED status for > 10 minutes
    and marks them as FAILED. Creates an error DialAttempt if linked.
    Also cleans up stale hopper entries stuck in 'dialing' status.
    """
    from app.core.database import SessionLocal
    from app.models.models import (
        CallLog, CallStatus, CallOutcome, DialHopper,
        DialAttempt, DialListEntry, DialEntryStatus,
    )

    db = SessionLocal()

    try:
        cutoff = datetime.utcnow() - timedelta(minutes=10)

        # Find orphaned calls
        orphaned_calls = (
            db.query(CallLog)
            .filter(
                CallLog.status.in_([CallStatus.RINGING, CallStatus.CONNECTED]),
                CallLog.started_at < cutoff,
            )
            .all()
        )

        cleaned = 0
        for call in orphaned_calls:
            call.status = CallStatus.FAILED
            call.outcome = CallOutcome.FAILED
            call.ended_at = datetime.utcnow()
            call.hangup_cause = "orphan_cleanup"

            # Create DialAttempt error record if linked
            if call.dial_attempt_id:
                attempt = db.get(DialAttempt, call.dial_attempt_id)
                if attempt:
                    attempt.result = "failed"
                    attempt.hangup_cause = "orphan_cleanup_timeout"
                    attempt.ended_at = datetime.utcnow()

                    # Update the entry status back to allow retry
                    entry = db.get(DialListEntry, attempt.entry_id)
                    if entry and entry.call_attempts < entry.max_attempts:
                        entry.status = DialEntryStatus.NEW
                    elif entry:
                        entry.status = DialEntryStatus.FAILED

            # Update campaign active calls
            if call.campaign_id:
                db.execute(
                    text("""
                    UPDATE campaigns
                    SET active_calls = GREATEST(active_calls - 1, 0),
                        failed_calls = failed_calls + 1
                    WHERE id = :campaign_id
                    """),
                    {"campaign_id": call.campaign_id},
                )

            cleaned += 1

        # Clean up stale hopper entries (stuck in 'dialing' for > 10 min)
        stale_hopper_count = (
            db.query(DialHopper)
            .filter(
                DialHopper.status == "dialing",
                DialHopper.inserted_at < cutoff,
            )
            .update({"status": "done"})
        )

        db.commit()

        if cleaned or stale_hopper_count:
            logger.info(
                f"Cleanup: {cleaned} orphan calls, {stale_hopper_count} stale hopper entries"
            )

    except Exception as e:
        logger.error(f"Error in cleanup_orphan_calls: {e}\n{traceback.format_exc()}")
        db.rollback()
    finally:
        db.close()


@shared_task
def manage_campaign_schedule():
    """
    Periodic task to auto-start and auto-stop campaigns based on their schedule.

    - SCHEDULED campaigns with scheduled_start <= now → set to RUNNING
    - RUNNING campaigns with scheduled_end <= now → set to COMPLETED
    Runs every 60 seconds.
    """
    from app.core.database import SessionLocal
    from app.models.models import Campaign, CampaignStatus

    db = SessionLocal()

    try:
        now = datetime.utcnow()

        # Auto-start scheduled campaigns
        campaigns_to_start = (
            db.query(Campaign)
            .filter(
                Campaign.status == CampaignStatus.SCHEDULED,
                Campaign.scheduled_start <= now,
            )
            .all()
        )

        for campaign in campaigns_to_start:
            campaign.status = CampaignStatus.RUNNING
            logger.info(f"Auto-started campaign {campaign.id} ({campaign.name})")

        # Auto-stop campaigns past their end time
        campaigns_to_stop = (
            db.query(Campaign)
            .filter(
                Campaign.status == CampaignStatus.RUNNING,
                Campaign.scheduled_end != None,
                Campaign.scheduled_end <= now,
            )
            .all()
        )

        for campaign in campaigns_to_stop:
            campaign.status = CampaignStatus.COMPLETED
            logger.info(f"Auto-completed campaign {campaign.id} ({campaign.name}) — past scheduled_end")

        db.commit()

    except Exception as e:
        logger.error(f"Error in manage_campaign_schedule: {e}\n{traceback.format_exc()}")
        db.rollback()
    finally:
        db.close()


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def persist_ultravox_call_data(self, call_log_id: int):
    """
    Fetch transcript and recording URL from Ultravox API and persist to DB.
    Called after an Ultravox call ends (from webhook or handle_call_complete).

    This ensures Ultravox call data is permanently stored in PostgreSQL
    and won't be lost if Ultravox purges old data.
    """
    from app.core.database import SessionLocal
    from app.models.models import CallLog

    db = SessionLocal()
    try:
        call_log = db.query(CallLog).filter(CallLog.id == call_log_id).first()
        if not call_log:
            logger.warning(f"persist_ultravox_call_data: CallLog {call_log_id} not found")
            return

        if call_log.provider != "ultravox" or not call_log.ultravox_call_id:
            logger.info(f"persist_ultravox_call_data: CallLog {call_log_id} is not an Ultravox call, skipping")
            return

        ultravox_call_id = call_log.ultravox_call_id

        # Fetch transcript from Ultravox API
        if not call_log.transcription:
            try:
                from app.services.ultravox_service import UltravoxService
                service = UltravoxService()
                loop = asyncio.new_event_loop()
                try:
                    messages = loop.run_until_complete(service.get_call_messages(ultravox_call_id))
                finally:
                    loop.close()

                if messages:
                    lines = []
                    for msg in messages:
                        role = msg.get("role", "unknown")
                        text_content = msg.get("text", "")
                        if text_content and text_content.strip():
                            lines.append(f"[{role}]: {text_content}")
                    if lines:
                        call_log.transcription = "\n".join(lines)
                        logger.info(f"persist_ultravox_call_data: Saved transcript ({len(lines)} messages) for call {call_log_id}")
            except Exception as t_err:
                logger.warning(f"persist_ultravox_call_data: Transcript fetch failed for {call_log_id}: {t_err}")

        # Fetch recording URL from Ultravox API and download to MinIO
        if not call_log.recording_url:
            try:
                from app.services.ultravox_service import UltravoxService
                service = UltravoxService()
                loop = asyncio.new_event_loop()
                try:
                    recording_url = loop.run_until_complete(service.get_call_recording(ultravox_call_id))
                finally:
                    loop.close()

                if recording_url:
                    # Try to download and store in MinIO for permanent storage
                    try:
                        import requests as req_lib
                        from app.services.minio_service import minio_service
                        resp = req_lib.get(recording_url, timeout=60)
                        if resp.status_code == 200:
                            recording_key = f"recordings/{call_log.call_sid}.wav"
                            minio_service.client.put_object(
                                minio_service.bucket_recordings,
                                recording_key,
                                data=__import__('io').BytesIO(resp.content),
                                length=len(resp.content),
                                content_type="audio/wav",
                            )
                            call_log.recording_url = recording_key
                            logger.info(f"persist_ultravox_call_data: Recording saved to MinIO for call {call_log_id}")
                        else:
                            # Store the Ultravox URL as fallback
                            call_log.recording_url = recording_url
                            logger.info(f"persist_ultravox_call_data: Stored Ultravox recording URL for call {call_log_id}")
                    except Exception as minio_err:
                        # Fallback: store the Ultravox URL directly
                        call_log.recording_url = recording_url
                        logger.warning(f"persist_ultravox_call_data: MinIO upload failed, stored URL: {minio_err}")
            except Exception as r_err:
                logger.warning(f"persist_ultravox_call_data: Recording fetch failed for {call_log_id}: {r_err}")

        db.commit()
        logger.info(f"persist_ultravox_call_data: Completed for call {call_log_id}")

    except Exception as e:
        logger.error(f"persist_ultravox_call_data error: {e}\n{traceback.format_exc()}")
        db.rollback()
        raise self.retry(exc=e)
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
    "process-callbacks": {
        "task": "app.tasks.celery_tasks.process_callbacks",
        "schedule": 300.0,  # Every 5 minutes
    },
    "cleanup-orphan-calls": {
        "task": "app.tasks.celery_tasks.cleanup_orphan_calls",
        "schedule": 300.0,  # Every 5 minutes
    },
    "manage-campaign-schedule": {
        "task": "app.tasks.celery_tasks.manage_campaign_schedule",
        "schedule": 60.0,  # Every minute
    },
}
