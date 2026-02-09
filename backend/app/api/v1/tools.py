"""
AI Tool Endpoints for Ultravox HTTP Tools.

When Ultravox AI decides to call a tool during a conversation,
it makes an HTTP request to these endpoints. The results are
passed back to the AI to continue the conversation.

These endpoints are the HTTP counterparts of the handlers in
audio_bridge.py (used by OpenAI). Both paths share the same
tool definitions from tool_registry.py.
"""

import json
import logging
import re
from datetime import datetime
from typing import Optional

import aiohttp
from bs4 import BeautifulSoup
from fastapi import APIRouter, Request, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import CallLog, Lead

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tools", tags=["AI Tools"])


# ------------------------------------------------------------- Helpers

def _get_call_id_from_request(request: Request) -> Optional[str]:
    """Extract call ID from Ultravox request headers or query params."""
    # Ultravox may pass call context via headers
    call_id = request.headers.get("X-Ultravox-Call-Id")
    if not call_id:
        call_id = request.query_params.get("call_id")
    return call_id


def _find_call_log(db: Session, call_id: Optional[str]) -> Optional[CallLog]:
    """Find CallLog by Ultravox call ID or our internal UUID."""
    if not call_id:
        return None
    # Try ultravox_call_id first, then call_sid
    call_log = db.query(CallLog).filter(CallLog.ultravox_call_id == call_id).first()
    if not call_log:
        call_log = db.query(CallLog).filter(CallLog.call_sid == call_id).first()
    return call_log


# --------------------------------------------------------- Save Customer Data

class SaveCustomerDataRequest(BaseModel):
    data_type: str  # "name", "phone", "email", "address"
    value: str
    confirmed: bool = False
    details: Optional[dict] = None


@router.post("/save-customer-data")
async def save_customer_data(request: Request, db: Session = Depends(get_db)):
    """Save customer information during a call."""
    body = await request.json()
    call_id = _get_call_id_from_request(request)
    data_type = body.get("data_type", "")
    value = body.get("value", "")
    confirmed = body.get("confirmed", False)
    details = body.get("details", {})

    if not confirmed:
        return {"status": "pending", "message": "Customer has not confirmed yet. Please verify the data."}

    call_log = _find_call_log(db, call_id)

    if data_type == "name":
        if call_log:
            call_log.customer_name = value
            db.commit()
        logger.info(f"[{call_id}] Customer name saved: {value}")
        return {"status": "success", "message": f"Name saved: {value}"}

    elif data_type == "phone":
        digits = "".join(c for c in value if c.isdigit())
        if len(digits) < 10 or len(digits) > 15:
            return {"status": "error", "message": f"Phone number has {len(digits)} digits, expected 10-15. Please ask again."}
        logger.info(f"[{call_id}] Phone saved: {digits}")
        return {"status": "success", "message": f"Phone saved: {digits}"}

    elif data_type == "email":
        email = value.lower().strip()
        if "@" not in email or "." not in email:
            return {"status": "error", "message": "Invalid email format. Please ask again."}
        logger.info(f"[{call_id}] Email saved: {email}")
        return {"status": "success", "message": f"Email saved: {email}"}

    elif data_type == "address":
        logger.info(f"[{call_id}] Address saved: {value}")
        return {"status": "success", "message": "Address saved"}

    return {"status": "error", "message": f"Unknown data type: {data_type}"}


# --------------------------------------------------------- Schedule Callback

@router.post("/schedule-callback")
async def schedule_callback(request: Request, db: Session = Depends(get_db)):
    """Schedule a callback appointment."""
    body = await request.json()
    call_id = _get_call_id_from_request(request)
    date_str = body.get("date", "")
    time_str = body.get("time", "")
    reason = body.get("reason", "")
    confirmed = body.get("confirmed", False)

    if not confirmed:
        return {"status": "pending", "message": "Customer has not confirmed the schedule. Please verify date and time."}

    call_log = _find_call_log(db, call_id)
    if call_log:
        try:
            callback_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            call_log.callback_scheduled = callback_dt
            db.commit()
        except ValueError:
            pass

    logger.info(f"[{call_id}] Callback scheduled: {date_str} {time_str} - {reason}")
    return {"status": "success", "message": f"Callback scheduled for {date_str} at {time_str}"}


# --------------------------------------------------------- Set Sentiment

@router.post("/set-sentiment")
async def set_sentiment(request: Request, db: Session = Depends(get_db)):
    """Record customer sentiment."""
    body = await request.json()
    call_id = _get_call_id_from_request(request)
    sentiment = body.get("sentiment", "neutral")
    reason = body.get("reason", "")

    call_log = _find_call_log(db, call_id)
    if call_log:
        call_log.sentiment = sentiment
        db.commit()

    logger.info(f"[{call_id}] Sentiment: {sentiment} - {reason}")
    return {"status": "success", "message": f"Sentiment recorded: {sentiment}"}


# --------------------------------------------------------- Add Tags

@router.post("/add-tags")
async def add_tags(request: Request, db: Session = Depends(get_db)):
    """Add tags to the call."""
    body = await request.json()
    call_id = _get_call_id_from_request(request)
    tags = body.get("tags", [])

    call_log = _find_call_log(db, call_id)
    if call_log:
        existing = call_log.tags or []
        call_log.tags = list(set(existing + tags))
        db.commit()

    logger.info(f"[{call_id}] Tags added: {tags}")
    return {"status": "success", "message": f"Tags added: {', '.join(tags)}"}


# --------------------------------------------------------- Call Summary

@router.post("/call-summary")
async def call_summary(request: Request, db: Session = Depends(get_db)):
    """Generate and save call summary."""
    body = await request.json()
    call_id = _get_call_id_from_request(request)
    summary = body.get("summary", "")
    action_items = body.get("action_items", [])
    satisfaction = body.get("customer_satisfaction", "neutral")

    call_log = _find_call_log(db, call_id)
    if call_log:
        call_log.summary = summary
        db.commit()

    logger.info(f"[{call_id}] Summary: {summary[:100]}...")
    return {"status": "success", "message": "Call summary recorded"}


# --------------------------------------------------------- Record Payment

@router.post("/record-payment")
async def record_payment(request: Request, db: Session = Depends(get_db)):
    """Record a payment promise."""
    body = await request.json()
    call_id = _get_call_id_from_request(request)
    amount = body.get("amount", 0)
    date_str = body.get("date", "")
    confirmed = body.get("confirmed", False)

    if not confirmed:
        return {"status": "pending", "message": "Customer has not confirmed the payment. Please verify amount and date."}

    call_log = _find_call_log(db, call_id)
    if call_log:
        call_log.payment_promise_amount = amount
        try:
            call_log.payment_promise_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            pass
        db.commit()

    logger.info(f"[{call_id}] Payment promise: {amount} on {date_str}")
    return {"status": "success", "message": f"Payment promise recorded: {amount} on {date_str}"}


# --------------------------------------------------------- End Call

@router.post("/end-call")
async def end_call(request: Request, db: Session = Depends(get_db)):
    """Record call outcome/summary and trigger Ultravox hang-up."""
    body = await request.json()
    call_id = _get_call_id_from_request(request)
    outcome = body.get("outcome", "other")
    summary = body.get("summary", "")

    call_log = _find_call_log(db, call_id)
    if call_log:
        call_log.outcome = outcome
        call_log.summary = summary
        db.commit()

    logger.info(f"[{call_id}] End call: outcome={outcome}")

    # Send HangUp data message to Ultravox to disconnect the SIP call
    if call_id:
        try:
            from app.services.ultravox_service import UltravoxService
            svc = UltravoxService()
            await svc.end_call(call_id)
            logger.info(f"[{call_id}] Ultravox HangUp sent via end_call tool")
        except Exception as e:
            logger.warning(f"[{call_id}] Ultravox HangUp failed (may already be ended): {e}")

    return {"status": "success", "message": f"Call ending with outcome: {outcome}"}


# --------------------------------------------------------- Transfer to Human

@router.post("/transfer-to-human")
async def transfer_to_human(request: Request, db: Session = Depends(get_db)):
    """Log transfer reason before cold-transfer occurs."""
    body = await request.json()
    call_id = _get_call_id_from_request(request)
    reason = body.get("reason", "Customer request")

    call_log = _find_call_log(db, call_id)
    if call_log:
        call_log.outcome = "transferred"
        call_log.summary = f"Transferred: {reason}"
        db.commit()

    logger.info(f"[{call_id}] Transfer to human: {reason}")
    return {"status": "success", "message": f"Transfer logged: {reason}"}


# --------------------------------------------------------- Search Web Source

@router.post("/search-web-source")
async def search_web_source(request: Request, db: Session = Depends(get_db)):
    """Search agent's configured web sources."""
    body = await request.json()
    call_id = _get_call_id_from_request(request)
    query = body.get("query", "")
    source_name = body.get("source_name", "")

    if not query:
        return {"status": "error", "message": "Search query is required", "results": []}

    # Get agent's web_sources from call log → agent
    call_log = _find_call_log(db, call_id)
    web_sources = []
    if call_log and call_log.agent:
        web_sources = getattr(call_log.agent, "web_sources", None) or []

    if not web_sources:
        return {
            "status": "error",
            "message": "No web sources configured for this agent.",
            "results": [],
        }

    results = []
    for source in web_sources:
        if source_name and source.get("name", "") != source_name:
            continue
        url = source.get("url", "")
        if not url:
            continue
        try:
            content = await _fetch_web_content(url, query)
            if content:
                results.append({
                    "source": source.get("name", url),
                    "content": content[:2000],
                })
        except Exception as e:
            logger.error(f"Web fetch error for {url}: {e}")

    if results:
        return {"status": "success", "results": results, "message": f"{len(results)} source(s) found"}
    return {"status": "error", "results": [], "message": "No relevant information found"}


# --------------------------------------------------------- Search Documents

@router.post("/search-documents")
async def search_documents_tool(request: Request, db: Session = Depends(get_db)):
    """Semantic search across uploaded documents (pgvector)."""
    body = await request.json()
    call_id = _get_call_id_from_request(request)
    query = body.get("query", "")

    if not query:
        return {"status": "error", "message": "Search query is required", "results": []}

    call_log = _find_call_log(db, call_id)
    agent_id = call_log.agent_id if call_log else None
    if not agent_id:
        return {"status": "error", "message": "Agent not found", "results": []}

    try:
        from app.services.document_service import DocumentService
        from app.core.database import AsyncSessionLocal

        # Need async session for document search
        async with AsyncSessionLocal() as async_db:
            service = DocumentService(async_db)
            results = await service.semantic_search(agent_id=agent_id, query=query, limit=5)

        if results:
            formatted = [
                {
                    "content": r["content"],
                    "source": r["document_filename"],
                    "relevance": f"{r['score']:.2f}",
                }
                for r in results
            ]
            return {"status": "success", "results": formatted, "message": f"{len(results)} document(s) matched"}
        return {"status": "error", "results": [], "message": "No matching documents found"}

    except Exception as e:
        logger.error(f"Document search error: {e}")
        return {"status": "error", "message": f"Document search error: {str(e)}", "results": []}


# --------------------------------------------------------- Confirm Appointment

@router.post("/confirm-appointment")
async def confirm_appointment(request: Request, db: Session = Depends(get_db)):
    """Create and confirm an appointment."""
    body = await request.json()
    call_id = _get_call_id_from_request(request)
    customer_name = body.get("customer_name", "")
    customer_phone = body.get("customer_phone", "")
    customer_address = body.get("customer_address", "")
    appointment_date = body.get("appointment_date", "")
    appointment_time = body.get("appointment_time", "")
    appointment_type = body.get("appointment_type", "consultation")
    notes = body.get("notes", "")

    if not customer_name or not appointment_date or not appointment_time:
        return {"status": "error", "message": "Customer name, date and time are required"}

    try:
        from app.models.models import Appointment, AppointmentType, AppointmentStatus

        parsed_date = datetime.strptime(appointment_date, "%Y-%m-%d")

        type_map = {
            "consultation": AppointmentType.CONSULTATION,
            "site_visit": AppointmentType.SITE_VISIT,
            "installation": AppointmentType.INSTALLATION,
            "maintenance": AppointmentType.MAINTENANCE,
            "demo": AppointmentType.DEMO,
            "other": AppointmentType.OTHER,
        }
        apt_type = type_map.get(appointment_type, AppointmentType.CONSULTATION)

        call_log = _find_call_log(db, call_id)
        agent_id = call_log.agent_id if call_log else None
        campaign_id = call_log.campaign_id if call_log else None

        appointment = Appointment(
            agent_id=agent_id,
            call_id=call_id,
            campaign_id=campaign_id,
            customer_name=customer_name,
            customer_phone=customer_phone,
            customer_address=customer_address,
            appointment_type=apt_type,
            appointment_date=parsed_date,
            appointment_time=appointment_time,
            status=AppointmentStatus.CONFIRMED,
            notes=notes,
            confirmed_at=datetime.utcnow(),
        )
        db.add(appointment)
        db.commit()

        logger.info(f"[{call_id}] Appointment: {customer_name} {appointment_date} {appointment_time}")
        return {
            "status": "success",
            "message": f"Appointment confirmed: {customer_name}, {appointment_date} at {appointment_time}",
        }

    except ValueError:
        return {"status": "error", "message": f"Invalid date format: {appointment_date}. Use YYYY-MM-DD."}
    except Exception as e:
        logger.error(f"Appointment creation error: {e}")
        return {"status": "error", "message": f"Appointment error: {str(e)}"}


# --------------------------------------------------------- Capture Lead

@router.post("/capture-lead")
async def capture_lead(request: Request, db: Session = Depends(get_db)):
    """Capture a potential lead."""
    body = await request.json()
    call_id = _get_call_id_from_request(request)
    customer_name = body.get("customer_name", "")
    interest_type = body.get("interest_type", "information")

    if not customer_name or not interest_type:
        return {"status": "error", "message": "Customer name and interest type are required"}

    try:
        from app.models.models import LeadStatus, LeadInterestType

        interest_map = {
            "callback": LeadInterestType.CALLBACK,
            "address_collection": LeadInterestType.ADDRESS_COLLECTION,
            "purchase_intent": LeadInterestType.PURCHASE_INTENT,
            "demo_request": LeadInterestType.DEMO_REQUEST,
            "quote_request": LeadInterestType.QUOTE_REQUEST,
            "subscription": LeadInterestType.SUBSCRIPTION,
            "information": LeadInterestType.INFORMATION,
            "other": LeadInterestType.OTHER,
        }
        lead_interest = interest_map.get(interest_type, LeadInterestType.INFORMATION)

        call_log = _find_call_log(db, call_id)
        agent_id = call_log.agent_id if call_log else None
        campaign_id = call_log.campaign_id if call_log else None

        lead = Lead(
            agent_id=agent_id,
            call_id=call_id,
            campaign_id=campaign_id,
            customer_name=customer_name,
            customer_phone=body.get("customer_phone", ""),
            customer_email=body.get("customer_email", ""),
            customer_address=body.get("customer_address", ""),
            interest_type=lead_interest,
            customer_statement=body.get("customer_statement", ""),
            status=LeadStatus.NEW,
            priority=body.get("priority", 2),
            notes=body.get("notes", ""),
        )
        db.add(lead)
        db.commit()

        logger.info(f"[{call_id}] Lead captured: {customer_name} - {interest_type}")
        return {"status": "success", "message": f"Lead captured: {customer_name} - {interest_type}"}

    except Exception as e:
        logger.error(f"Lead capture error: {e}")
        return {"status": "error", "message": f"Lead capture error: {str(e)}"}


# --------------------------------------------------------- Get Caller Datetime

@router.post("/get-caller-datetime")
async def get_caller_datetime(request: Request, db: Session = Depends(get_db)):
    """Get caller's local datetime based on phone number timezone."""
    call_id = _get_call_id_from_request(request)

    try:
        import phonenumbers
        import pytz

        customer_phone = ""
        call_log = _find_call_log(db, call_id)
        if call_log:
            customer_phone = call_log.phone_number or ""

        timezone_str = "Europe/Istanbul"

        if customer_phone:
            try:
                parsed = phonenumbers.parse(customer_phone, None)
                country_code = phonenumbers.region_code_for_number(parsed)
                country_tzs = pytz.country_timezones.get(country_code, [])
                if country_tzs:
                    timezone_str = country_tzs[0]
            except Exception:
                pass

        tz = pytz.timezone(timezone_str)
        now = datetime.now(tz)

        hour = now.hour
        if 5 <= hour < 12:
            greeting = "Günaydın"
        elif 12 <= hour < 18:
            greeting = "İyi günler"
        elif 18 <= hour < 22:
            greeting = "İyi akşamlar"
        else:
            greeting = "İyi geceler"

        return {
            "status": "success",
            "datetime": now.strftime("%Y-%m-%d %H:%M"),
            "timezone": timezone_str,
            "greeting": greeting,
            "message": f"Caller's local time: {now.strftime('%H:%M')} ({timezone_str}). Suggested greeting: {greeting}",
        }

    except Exception as e:
        logger.error(f"Get caller datetime error: {e}")
        now = datetime.utcnow()
        return {
            "status": "success",
            "datetime": now.strftime("%Y-%m-%d %H:%M"),
            "timezone": "UTC",
            "greeting": "Merhaba",
            "message": f"Default time used: {now.strftime('%H:%M')} (UTC)",
        }


# --------------------------------------------------------- Verify Contact Info

@router.post("/verify-contact-info")
async def verify_contact_info(request: Request):
    """Verify and format contact information."""
    body = await request.json()
    info_type = body.get("info_type", "")
    raw_value = body.get("raw_value", "").strip()
    language = body.get("language", "auto")

    if not info_type or not raw_value:
        return {"status": "error", "message": "info_type and raw_value are required"}

    if info_type == "phone":
        digits = re.sub(r"[^\d+]", "", raw_value)
        if len(digits) < 10 or len(digits) > 16:
            return {
                "status": "error",
                "valid": False,
                "message": f"Phone has {len(digits)} digits, expected 10-15.",
            }
        return {"status": "success", "valid": True, "formatted": digits, "message": f"Phone verified: {digits}"}

    elif info_type == "email":
        email = raw_value.lower().strip()
        if "@" not in email or "." not in email.split("@")[-1]:
            return {"status": "error", "valid": False, "message": "Invalid email format"}
        return {"status": "success", "valid": True, "formatted": email, "message": f"Email verified: {email}"}

    elif info_type == "name":
        formatted = raw_value.strip().title()
        return {"status": "success", "valid": True, "formatted": formatted, "message": f"Name: {formatted}"}

    elif info_type == "address":
        return {"status": "success", "valid": True, "formatted": raw_value.strip(), "message": "Address recorded"}

    return {"status": "error", "message": f"Unknown info type: {info_type}"}


# --------------------------------------------------------- Submit Survey Answer

@router.post("/submit-survey-answer")
async def submit_survey_answer(request: Request, db: Session = Depends(get_db)):
    """Submit a survey answer and return the next question."""
    body = await request.json()
    call_id = _get_call_id_from_request(request)
    question_id = body.get("question_id", "")
    answer = body.get("answer", "")
    answer_value = body.get("answer_value")

    if not question_id or not answer:
        return {"status": "error", "message": "question_id and answer are required"}

    try:
        from app.models.models import SurveyResponse, SurveyStatus

        call_log = _find_call_log(db, call_id)
        agent_id = call_log.agent_id if call_log else None
        campaign_id = call_log.campaign_id if call_log else None

        # Look up survey config from agent
        survey_config = {}
        if call_log and call_log.agent:
            survey_config = getattr(call_log.agent, "survey_config", {}) or {}
        questions = survey_config.get("questions", [])
        question_map = {q.get("id"): q for q in questions}
        current_question = question_map.get(question_id)

        if not current_question:
            return {"status": "error", "message": f"Question not found: {question_id}"}

        # Find or create survey response
        survey_response = db.query(SurveyResponse).filter(
            SurveyResponse.call_id == call_id,
            SurveyResponse.agent_id == agent_id,
        ).first()

        if not survey_response:
            survey_response = SurveyResponse(
                call_id=call_id,
                agent_id=agent_id,
                campaign_id=campaign_id,
                status=SurveyStatus.IN_PROGRESS,
                answers=[],
                total_questions=len(questions),
                started_at=datetime.utcnow(),
            )
            db.add(survey_response)

        answers = survey_response.answers or []
        answers.append({
            "question_id": question_id,
            "question_text": current_question.get("text", ""),
            "answer": answer,
            "answer_value": answer_value,
            "answered_at": datetime.utcnow().isoformat(),
        })
        survey_response.answers = answers
        survey_response.questions_answered = len(answers)

        # Determine next question
        next_question_id = current_question.get("next")
        survey_complete = next_question_id is None

        if survey_complete:
            survey_response.status = SurveyStatus.COMPLETED
            survey_response.completed_at = datetime.utcnow()

        db.commit()

        if survey_complete:
            return {
                "status": "success",
                "survey_complete": True,
                "message": survey_config.get("completion_message", "Survey completed. Thank you!"),
            }

        next_q = question_map.get(next_question_id, {})
        return {
            "status": "success",
            "survey_complete": False,
            "next_question": {
                "id": next_question_id,
                "type": next_q.get("type", ""),
                "text": next_q.get("text", ""),
            },
            "message": "Answer recorded",
        }

    except Exception as e:
        logger.error(f"Survey answer error: {e}")
        return {"status": "error", "message": f"Survey error: {str(e)}"}


# --------------------------------------------------------- Survey Control

@router.post("/survey-control")
async def survey_control(request: Request, db: Session = Depends(get_db)):
    """Start or abort a survey."""
    body = await request.json()
    call_id = _get_call_id_from_request(request)
    action = body.get("action", "")
    reason = body.get("reason", "")

    try:
        from app.models.models import SurveyResponse, SurveyStatus

        call_log = _find_call_log(db, call_id)
        agent_id = call_log.agent_id if call_log else None
        campaign_id = call_log.campaign_id if call_log else None

        survey_config = {}
        if call_log and call_log.agent:
            survey_config = getattr(call_log.agent, "survey_config", {}) or {}
        questions = survey_config.get("questions", [])

        if action == "start":
            survey_response = SurveyResponse(
                call_id=call_id,
                agent_id=agent_id,
                campaign_id=campaign_id,
                status=SurveyStatus.IN_PROGRESS,
                answers=[],
                total_questions=len(questions),
                started_at=datetime.utcnow(),
            )
            db.add(survey_response)
            db.commit()

            start_id = survey_config.get("start_question") or (questions[0].get("id") if questions else None)
            first_q = next((q for q in questions if q.get("id") == start_id), None)

            if not first_q:
                return {"status": "error", "message": "No survey questions found"}

            return {
                "status": "success",
                "message": "Survey started",
                "first_question": {
                    "id": start_id,
                    "type": first_q.get("type", ""),
                    "text": first_q.get("text", ""),
                },
                "total_questions": len(questions),
            }

        elif action == "abort":
            survey_response = db.query(SurveyResponse).filter(
                SurveyResponse.call_id == call_id,
                SurveyResponse.agent_id == agent_id,
                SurveyResponse.status == SurveyStatus.IN_PROGRESS,
            ).first()
            if survey_response:
                survey_response.status = SurveyStatus.ABANDONED
                survey_response.completed_at = datetime.utcnow()
                db.commit()

            return {"status": "success", "message": survey_config.get("abort_message", "Survey aborted"), "reason": reason}

        return {"status": "error", "message": f"Unknown action: {action}"}

    except Exception as e:
        logger.error(f"Survey control error: {e}")
        return {"status": "error", "message": f"Survey error: {str(e)}"}


# --------------------------------------------------------- Web Content Helper

async def _fetch_web_content(url: str, query: str) -> str:
    """Fetch and extract relevant content from a web page."""
    try:
        async with aiohttp.ClientSession() as session:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status != 200:
                    return ""
                html = await response.text()

        soup = BeautifulSoup(html, "html.parser")
        for el in soup(["script", "style", "nav", "footer", "header"]):
            el.decompose()
        text = soup.get_text(separator="\n", strip=True)

        if query:
            query_words = query.lower().split()
            paragraphs = text.split("\n\n")
            relevant = []
            for para in paragraphs:
                score = sum(1 for w in query_words if w in para.lower())
                if score > 0:
                    relevant.append((score, para))
            relevant.sort(key=lambda x: x[0], reverse=True)
            if relevant:
                text = "\n\n".join(p[1] for p in relevant[:5])

        return text[:3000]

    except Exception as e:
        logger.error(f"Web fetch error: {url} - {e}")
        return ""
