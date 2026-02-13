"""
Greeting Processor Service
==========================
Processes greeting messages with dynamic variables

Available Variables:
- {customer_name} - Customer's full name
- {first_name} - Customer's first name
- {last_name} - Customer's last name
- {company} - Company name
- {phone} - Phone number
- {date} - Current date
- {time} - Current time
- {day} - Day of week
- {agent_name} - Agent name
- {amount} - Payment amount (if available)
- {due_date} - Due date (if available)

Custom variables from Excel columns are also supported:
- {column_name} - Any custom field from PhoneNumber.custom_data

Example:
    "Merhaba {first_name}, ben {agent_name}. Bugün {company} adına arıyorum."
"""

import re
from datetime import datetime
from typing import Dict, Optional, Any

from app.services.prompt_constants import (
    TITLE_TRANSLATIONS,
    TITLE_AFTER_NAME,
    DAY_NAMES,
    MONTH_NAMES,
)


def get_system_variables(language: str = "tr") -> Dict[str, str]:
    """Get current system variables with language-aware day/month names"""
    now = datetime.now()
    
    # Use centralized day/month names from prompt_constants
    days = DAY_NAMES.get(language, DAY_NAMES.get("en", []))
    months = MONTH_NAMES.get(language, MONTH_NAMES.get("en", []))
    
    day_name = days[now.weekday()] if days and now.weekday() < len(days) else ""
    month_name = months[now.month - 1] if months and (now.month - 1) < len(months) else ""
    
    return {
        "date": now.strftime("%d.%m.%Y"),
        "time": now.strftime("%H:%M"),
        "day": day_name,
        "month": month_name,
        "year": str(now.year),
    }


def extract_first_name(full_name: Optional[str]) -> str:
    """Extract first name from full name"""
    if not full_name:
        return ""
    parts = full_name.strip().split()
    return parts[0] if parts else ""


def extract_last_name(full_name: Optional[str]) -> str:
    """Extract last name from full name"""
    if not full_name:
        return ""
    parts = full_name.strip().split()
    return parts[-1] if len(parts) > 1 else ""


def _build_addressed_name(
    first_name: str,
    raw_title: str,
    language: str,
) -> str:
    """Build a language-aware addressed name with title.

    Examples:
        Turkish : "Cenani Bey"  or  "Cenani Hanım"
        English : "Mr Cenani"   or  "Mrs Cenani"
        German  : "Herr Cenani" or  "Frau Cenani"
    """
    if not first_name:
        return ""
    translations = TITLE_TRANSLATIONS.get(language, TITLE_TRANSLATIONS.get("en", {}))
    localized = translations.get(raw_title, raw_title)
    if not localized:
        return first_name
    if language in TITLE_AFTER_NAME:
        return f"{first_name} {localized}"
    return f"{localized} {first_name}"


def process_greeting(
    template: str,
    customer_data: Optional[Dict[str, Any]] = None,
    agent_name: str = "VoiceAI",
    custom_variables: Optional[Dict[str, str]] = None,
    language: str = "tr",
) -> str:
    """
    Process greeting template with dynamic variables.

    The ``language`` parameter controls:
    - Day/month names ({day}, {month})
    - Title translation ({customer_title} → Bey/Hanım, Mr/Mrs, Herr/Frau …)
    - Title-name ordering ({addressed_name} → "Cenani Bey" vs "Mr Cenani")

    Args:
        template: Greeting template with {variable} placeholders
        customer_data: Customer information dict (name, customer_title, custom_data …)
        agent_name: Name of the AI agent
        custom_variables: Additional custom variables
        language: Agent language code ("tr", "en", "de", …)

    Returns:
        Processed greeting string
    """
    if not template:
        return ""
    
    # Build variables dictionary
    variables: Dict[str, str] = {}
    
    # 1. System variables (date, time, etc.) — language-aware
    variables.update(get_system_variables(language))
    
    # 2. Agent variables
    variables["agent_name"] = agent_name
    
    # 3. Customer variables
    if customer_data:
        full_name = customer_data.get("name", "")
        first_name = extract_first_name(full_name)
        last_name = extract_last_name(full_name)
        raw_title = customer_data.get("customer_title", "")  # "Mr" or "Mrs"

        variables["customer_name"] = full_name
        variables["first_name"] = first_name
        variables["last_name"] = last_name
        variables["phone"] = customer_data.get("phone", "")

        # Language-aware title translation
        if raw_title:
            translations = TITLE_TRANSLATIONS.get(language, TITLE_TRANSLATIONS.get("en", {}))
            variables["customer_title"] = translations.get(raw_title, raw_title)
        else:
            variables["customer_title"] = ""

        # Language-aware addressed name  (e.g. "Cenani Bey" or "Mr Cenani")
        variables["addressed_name"] = _build_addressed_name(first_name, raw_title, language)

        # Custom data from Excel columns
        custom_data = customer_data.get("custom_data", {})
        if custom_data:
            for key, value in custom_data.items():
                # Normalize key (lowercase, replace spaces with underscore)
                normalized_key = key.lower().replace(" ", "_")
                variables[normalized_key] = str(value) if value else ""

                # Also add common aliases
                if normalized_key in ["sirket", "şirket", "firma"]:
                    variables["company"] = str(value)
                elif normalized_key in ["tutar", "miktar", "borc"]:
                    variables["amount"] = str(value)
                elif normalized_key in ["vade", "son_tarih", "odeme_tarihi"]:
                    variables["due_date"] = str(value)
                elif normalized_key in ["title", "hitap", "unvan", "cinsiyet"]:
                    # Override title from custom data
                    raw_title = str(value)
                    translations = TITLE_TRANSLATIONS.get(language, TITLE_TRANSLATIONS.get("en", {}))
                    variables["customer_title"] = translations.get(raw_title, raw_title)
                    variables["addressed_name"] = _build_addressed_name(first_name, raw_title, language)
    
    # 4. Additional custom variables
    if custom_variables:
        variables.update(custom_variables)
    
    # 5. Replace variables in template
    result = template
    
    # Find all {variable} patterns
    pattern = r'\{([^}]+)\}'
    
    def replace_var(match):
        var_name = match.group(1).lower().strip()
        return variables.get(var_name, match.group(0))  # Keep original if not found
    
    result = re.sub(pattern, replace_var, result)
    
    return result
