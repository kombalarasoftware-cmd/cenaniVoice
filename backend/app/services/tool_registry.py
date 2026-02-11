"""
Universal Tool Registry for Voice AI Platform.

Central definition of ALL available tools, provider-agnostic.
Both OpenAI Realtime and Ultravox providers use this registry
as the single source of truth.

Adding a new AI provider? Just implement a converter that reads
from TOOL_DEFINITIONS and transforms to your provider's format.

Adding a new tool?
  1. Add it to TOOL_DEFINITIONS below
  2. Add a handler in audio_bridge.py  _handle_tool_call()  (OpenAI path)
  3. Add an HTTP endpoint in api/v1/tools.py               (Ultravox path)
  4. Done — both providers now have the tool automatically.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


# =============================================================================
# UNIVERSAL TOOL DEFINITIONS
# =============================================================================
#
# Each tool has:
#   name              – unique identifier (used as function name)
#   description       – what the AI model should know about the tool
#   parameters        – dict of param_name → JSON Schema property
#   required          – list of required parameter names
#   category          – grouping: core | data_capture | search | appointment
#                       | lead | utility | survey
#   condition         – agent_config key that must be truthy to include
#                       (None = always included)
#   ultravox_endpoint – HTTP path suffix for Ultravox webhook callback
# =============================================================================

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    # ── Core Call Control ────────────────────────────────────────────────
    {
        "name": "end_call",
        "description": (
            "Görüşmeyi sonlandır. End the call and disconnect. "
            "Call this when the conversation is complete or the customer wants to end the call. "
            "Record the outcome and a brief summary. "
            "After calling this tool, say goodbye and stop speaking. "
            "The call will be automatically disconnected."
        ),
        "parameters": {
            "outcome": {
                "type": "string",
                "enum": [
                    "success",
                    "no_interest",
                    "wrong_number",
                    "callback",
                    "other",
                ],
                "description": "Görüşme sonucu / Call outcome",
            },
            "summary": {
                "type": "string",
                "description": "Görüşme özeti / Brief call summary",
            },
        },
        "required": ["outcome"],
        "category": "core",
        "condition": None,
        "ultravox_endpoint": "/end-call",
    },
    {
        "name": "transfer_to_human",
        "description": (
            "Müşteri yetkili bir kişiyle görüşmek istediğinde veya "
            "çözülemeyen bir sorun olduğunda çağrıyı operatöre aktar. "
            "Transfer the call to a human operator."
        ),
        "parameters": {
            "reason": {
                "type": "string",
                "description": "Transfer nedeni / Transfer reason",
            },
        },
        "required": ["reason"],
        "category": "core",
        "condition": None,
        "ultravox_endpoint": "/transfer-to-human",
    },
    {
        "name": "schedule_callback",
        "description": (
            "Müşteri daha sonra aranmak istediğinde geri arama planla. "
            "Schedule a callback when the customer wants to be called later."
        ),
        "parameters": {
            "datetime": {
                "type": "string",
                "description": "Geri arama zamanı (YYYY-MM-DD HH:MM) / Callback datetime",
            },
            "notes": {
                "type": "string",
                "description": "Ek notlar / Additional notes",
            },
        },
        "required": ["datetime"],
        "category": "core",
        "condition": None,
        "ultravox_endpoint": "/schedule-callback",
    },
    {
        "name": "record_payment_promise",
        "description": (
            "Müşteri ödeme sözü verdiğinde kaydet. "
            "Record a customer's payment promise with amount and date."
        ),
        "parameters": {
            "amount": {
                "type": "number",
                "description": "Ödeme tutarı / Payment amount",
            },
            "date": {
                "type": "string",
                "description": "Ödeme tarihi (YYYY-MM-DD) / Payment date",
            },
            "notes": {
                "type": "string",
                "description": "Ek notlar / Additional notes",
            },
        },
        "required": ["amount", "date"],
        "category": "core",
        "condition": None,
        "ultravox_endpoint": "/record-payment",
    },

    # ── Data Capture ─────────────────────────────────────────────────────
    {
        "name": "save_customer_data",
        "description": (
            "Müşteri bilgilerini kaydet (isim, telefon, e-posta, adres). "
            "Save customer information. Call after the customer confirms."
        ),
        "parameters": {
            "data_type": {
                "type": "string",
                "enum": ["name", "phone", "email", "address"],
                "description": "Kaydedilen veri tipi / Type of data being saved",
            },
            "value": {
                "type": "string",
                "description": "Veri değeri / The data value",
            },
            "confirmed": {
                "type": "boolean",
                "description": "Müşteri onayladı mı / Whether customer confirmed",
            },
        },
        "required": ["data_type", "value"],
        "category": "data_capture",
        "condition": None,
        "ultravox_endpoint": "/save-customer-data",
    },
    {
        "name": "set_call_sentiment",
        "description": (
            "Görüşme sırasında müşterinin genel duygu durumunu kaydet. "
            "Record the customer's overall sentiment near the end of the call."
        ),
        "parameters": {
            "sentiment": {
                "type": "string",
                "enum": ["positive", "neutral", "negative"],
                "description": "Müşteri duygu durumu / Customer sentiment",
            },
            "reason": {
                "type": "string",
                "description": "Kısa açıklama / Brief explanation",
            },
        },
        "required": ["sentiment"],
        "category": "data_capture",
        "condition": None,
        "ultravox_endpoint": "/set-sentiment",
    },
    {
        "name": "add_call_tags",
        "description": (
            "Görüşmeye etiket ekle. Add tags based on conversation content. "
            "Examples: interested, callback, complaint, info_request, hot_lead."
        ),
        "parameters": {
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Etiket listesi / List of tags",
            },
        },
        "required": ["tags"],
        "category": "data_capture",
        "condition": None,
        "ultravox_endpoint": "/add-tags",
    },
    {
        "name": "generate_call_summary",
        "description": (
            "Görüşme özeti oluştur. Call right before the call ends. "
            "Summarize topics discussed, decisions made, and next steps."
        ),
        "parameters": {
            "summary": {
                "type": "string",
                "description": "Görüşme özeti (max 200 kelime) / Call summary",
            },
            "action_items": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Yapılacaklar listesi / Action items",
            },
            "customer_satisfaction": {
                "type": "string",
                "enum": [
                    "very_satisfied",
                    "satisfied",
                    "neutral",
                    "dissatisfied",
                    "very_dissatisfied",
                ],
                "description": "Tahmini müşteri memnuniyeti / Estimated satisfaction",
            },
        },
        "required": ["summary"],
        "category": "data_capture",
        "condition": None,
        "ultravox_endpoint": "/call-summary",
    },
    {
        "name": "capture_lead",
        "description": (
            "Potansiyel müşteri bilgilerini kaydet. "
            "Capture lead information including interest type and customer statement."
        ),
        "parameters": {
            "customer_name": {
                "type": "string",
                "description": "Müşteri adı / Customer name",
            },
            "customer_phone": {
                "type": "string",
                "description": "Müşteri telefonu / Customer phone",
            },
            "customer_email": {
                "type": "string",
                "description": "Müşteri e-posta / Customer email",
            },
            "interest_type": {
                "type": "string",
                "enum": [
                    "callback",
                    "address_collection",
                    "purchase_intent",
                    "demo_request",
                    "quote_request",
                    "subscription",
                    "information",
                    "other",
                ],
                "description": "İlgi tipi / Interest type",
            },
            "customer_statement": {
                "type": "string",
                "description": "Müşteri ifadesi / Customer statement",
            },
            "priority": {
                "type": "integer",
                "description": "Öncelik (1-5, 1=en yüksek) / Priority",
            },
            "notes": {
                "type": "string",
                "description": "Ek notlar / Additional notes",
            },
        },
        "required": ["customer_name", "interest_type"],
        "category": "lead",
        "condition": None,
        "ultravox_endpoint": "/capture-lead",
    },

    # ── Search / Knowledge ───────────────────────────────────────────────
    {
        "name": "search_web_source",
        "description": (
            "Agent'a tanımlanmış web kaynaklarında arama yap. "
            "Search configured web sources for relevant information."
        ),
        "parameters": {
            "query": {
                "type": "string",
                "description": "Arama sorgusu / Search query",
            },
            "source_name": {
                "type": "string",
                "description": "Belirli bir kaynak adı (opsiyonel) / Specific source name",
            },
        },
        "required": ["query"],
        "category": "search",
        "condition": None,
        "ultravox_endpoint": "/search-web-source",
    },
    {
        "name": "search_documents",
        "description": (
            "Yüklenmiş dokümanlarda semantik arama yap. "
            "Perform semantic search across uploaded documents using AI embeddings."
        ),
        "parameters": {
            "query": {
                "type": "string",
                "description": "Arama sorgusu / Search query",
            },
        },
        "required": ["query"],
        "category": "search",
        "condition": None,
        "ultravox_endpoint": "/search-documents",
    },

    # ── Appointment ──────────────────────────────────────────────────────
    {
        "name": "confirm_appointment",
        "description": (
            "Müşteri ile randevu oluştur ve onayla. "
            "Create and confirm an appointment with the customer."
        ),
        "parameters": {
            "customer_name": {
                "type": "string",
                "description": "Müşteri adı / Customer name",
            },
            "customer_phone": {
                "type": "string",
                "description": "Müşteri telefonu / Customer phone",
            },
            "customer_address": {
                "type": "string",
                "description": "Müşteri adresi / Customer address",
            },
            "appointment_date": {
                "type": "string",
                "description": "Randevu tarihi (YYYY-MM-DD) / Appointment date",
            },
            "appointment_time": {
                "type": "string",
                "description": "Randevu saati (HH:MM) / Appointment time",
            },
            "appointment_type": {
                "type": "string",
                "enum": [
                    "consultation",
                    "site_visit",
                    "installation",
                    "maintenance",
                    "demo",
                    "other",
                ],
                "description": "Randevu tipi / Appointment type",
            },
            "notes": {
                "type": "string",
                "description": "Ek notlar / Additional notes",
            },
        },
        "required": ["customer_name", "appointment_date", "appointment_time"],
        "category": "appointment",
        "condition": None,
        "ultravox_endpoint": "/confirm-appointment",
    },

    # ── DNC / Campaign Management ───────────────────────────────────────
    {
        "name": "register_dnc",
        "description": (
            "Register a phone number on the Do-Not-Call list. "
            "Use when the customer explicitly requests to not be called again. "
            "This permanently prevents future calls to this number."
        ),
        "parameters": {
            "phone_number": {
                "type": "string",
                "description": "Phone number to add to DNC list",
            },
            "reason": {
                "type": "string",
                "description": "Reason for DNC registration (e.g. customer request, wrong number)",
            },
        },
        "required": ["phone_number"],
        "category": "core",
        "condition": None,
        "ultravox_endpoint": "/register-dnc",
    },
    {
        "name": "add_campaign_note",
        "description": (
            "Add a note to the current call record. "
            "Use to save important observations, customer requests, "
            "or follow-up items discovered during the conversation."
        ),
        "parameters": {
            "note_text": {
                "type": "string",
                "description": "Note content to save to the call record",
            },
        },
        "required": ["note_text"],
        "category": "data_capture",
        "condition": None,
        "ultravox_endpoint": "/add-campaign-note",
    },

    # ── Utility ──────────────────────────────────────────────────────────
    {
        "name": "get_caller_datetime",
        "description": (
            "Arayan kişinin yerel tarih ve saatini öğren. "
            "Get the caller's local date/time based on phone number timezone. "
            "Useful for appropriate greetings and scheduling."
        ),
        "parameters": {},
        "required": [],
        "category": "utility",
        "condition": None,
        "ultravox_endpoint": "/get-caller-datetime",
    },
    {
        "name": "verify_contact_info",
        "description": (
            "Müşteriden alınan iletişim bilgisini doğrula ve formatla. "
            "Verify and format contact information (phone, email, name, address). "
            "Supports TR/DE/EN formats."
        ),
        "parameters": {
            "info_type": {
                "type": "string",
                "enum": ["phone", "email", "name", "address"],
                "description": "Bilgi tipi / Information type",
            },
            "raw_value": {
                "type": "string",
                "description": "Ham değer / Raw value from customer",
            },
            "language": {
                "type": "string",
                "enum": ["tr", "de", "en", "auto"],
                "description": "Dil / Language (auto for auto-detect)",
            },
        },
        "required": ["info_type", "raw_value"],
        "category": "utility",
        "condition": None,
        "ultravox_endpoint": "/verify-contact-info",
    },

    # ── Survey ───────────────────────────────────────────────────────────
    {
        "name": "submit_survey_answer",
        "description": (
            "Anket cevabını kaydet ve sonraki soruyu al. "
            "Submit a survey answer and get the next question."
        ),
        "parameters": {
            "question_id": {
                "type": "string",
                "description": "Soru ID / Question ID",
            },
            "answer": {
                "type": "string",
                "description": "Cevap / Answer",
            },
            "answer_value": {
                "type": "number",
                "description": "Sayısal cevap değeri (puanlama soruları için) / Numeric value for rating questions",
            },
        },
        "required": ["question_id", "answer"],
        "category": "survey",
        "condition": "survey_config",
        "ultravox_endpoint": "/submit-survey-answer",
    },
    {
        "name": "survey_control",
        "description": (
            "Anketi başlat veya iptal et. "
            "Start or abort a survey."
        ),
        "parameters": {
            "action": {
                "type": "string",
                "enum": ["start", "abort"],
                "description": "Aksiyon / Action",
            },
            "reason": {
                "type": "string",
                "description": "Neden (iptal durumunda) / Reason if aborting",
            },
        },
        "required": ["action"],
        "category": "survey",
        "condition": "survey_config",
        "ultravox_endpoint": "/survey-control",
    },
]


# =============================================================================
# HELPER: filter tools by agent config
# =============================================================================

def get_tools_for_agent(agent_config: dict) -> list[dict]:
    """
    Return tool definitions applicable to this agent.

    Tools whose ``condition`` key names a falsy value in *agent_config*
    are excluded; everything else is included.
    """
    tools = []
    for tool_def in TOOL_DEFINITIONS:
        condition = tool_def.get("condition")
        if condition and not agent_config.get(condition):
            continue
        tools.append(tool_def)
    return tools


# =============================================================================
# OPENAI FORMAT CONVERTER
# =============================================================================

def to_openai_tools(agent_config: dict) -> list[dict]:
    """
    Convert universal tool definitions to OpenAI Realtime
    function-calling format.

    Returns a list ready for ``session.tools`` in the OpenAI
    Realtime API configuration.
    """
    applicable = get_tools_for_agent(agent_config)
    openai_tools: list[dict] = []

    for tool_def in applicable:
        properties: dict = {}
        required: list[str] = []

        for param_name, param_schema in tool_def.get("parameters", {}).items():
            properties[param_name] = param_schema

        for req in tool_def.get("required", []):
            required.append(req)

        tool = {
            "type": "function",
            "name": tool_def["name"],
            "description": tool_def["description"],
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }
        openai_tools.append(tool)

    return openai_tools


# =============================================================================
# ULTRAVOX FORMAT CONVERTER
# =============================================================================

def to_ultravox_tools(agent_config: dict, webhook_base: str) -> list[dict]:
    """
    Convert universal tool definitions to Ultravox HTTP tool format.

    Also appends Ultravox built-in tools (``hangUp``, ``coldTransfer``).

    Args:
        agent_config: Agent settings dict
        webhook_base: Base URL for HTTP callbacks (must be HTTPS)

    Returns:
        List of Ultravox tool definitions
    """
    applicable = get_tools_for_agent(agent_config)
    ultravox_tools: list[dict] = []

    for tool_def in applicable:
        dynamic_params: list[dict] = []

        for param_name, param_schema in tool_def.get("parameters", {}).items():
            dynamic_params.append({
                "name": param_name,
                "location": "PARAMETER_LOCATION_BODY",
                "schema": param_schema,
                "required": param_name in tool_def.get("required", []),
            })

        endpoint = tool_def.get("ultravox_endpoint", f"/{tool_def['name']}")

        tool = {
            "temporaryTool": {
                "modelToolName": tool_def["name"],
                "description": tool_def["description"],
                "dynamicParameters": dynamic_params,
                "http": {
                    "baseUrlPattern": f"{webhook_base}{endpoint}",
                    "httpMethod": "POST",
                },
            }
        }
        ultravox_tools.append(tool)

    # ── Ultravox built-in tools ──────────────────────────────────────────
    ultravox_tools.append({"toolName": "hangUp"})
    # coldTransfer requires parameterOverrides with 'target' SIP URI
    # Only add if agent has a transfer target configured
    transfer_number = agent_config.get("transfer_number")
    if transfer_number:
        from app.core.config import settings as app_settings
        ultravox_tools.append({
            "toolName": "coldTransfer",
            "parameterOverrides": {
                "target": f"sip:{transfer_number}@{app_settings.SIP_TRUNK_HOST}:{app_settings.SIP_TRUNK_PORT}"
            }
        })

    return ultravox_tools
