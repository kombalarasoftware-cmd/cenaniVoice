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


# Turkish day names
TURKISH_DAYS = {
    0: "Pazartesi",
    1: "Salı",
    2: "Çarşamba",
    3: "Perşembe",
    4: "Cuma",
    5: "Cumartesi",
    6: "Pazar"
}

# Turkish month names
TURKISH_MONTHS = {
    1: "Ocak",
    2: "Şubat",
    3: "Mart",
    4: "Nisan",
    5: "Mayıs",
    6: "Haziran",
    7: "Temmuz",
    8: "Ağustos",
    9: "Eylül",
    10: "Ekim",
    11: "Kasım",
    12: "Aralık"
}


def get_system_variables(language: str = "tr") -> Dict[str, str]:
    """Get current system variables with language-aware day/month names"""
    now = datetime.now()
    
    # Use centralized day/month names from prompt_constants
    days = DAY_NAMES.get(language, DAY_NAMES.get("en", []))
    months = MONTH_NAMES.get(language, MONTH_NAMES.get("en", []))
    
    # Fallback to Turkish legacy if language not in DAY_NAMES
    day_name = days[now.weekday()] if days and now.weekday() < len(days) else TURKISH_DAYS.get(now.weekday(), "")
    month_name = months[now.month - 1] if months and (now.month - 1) < len(months) else TURKISH_MONTHS.get(now.month, "")
    
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


def validate_greeting_template(template: str) -> Dict[str, Any]:
    """
    Validate a greeting template and return info about used variables
    
    Returns:
        {
            "valid": bool,
            "variables_used": list,
            "unknown_variables": list,
            "preview": str  # Preview with sample data
        }
    """
    known_variables = {
        "customer_name", "first_name", "last_name", "customer_title",
        "addressed_name", "company", "phone", "date", "time", "day", "month", "year",
        "agent_name", "amount", "due_date"
    }
    
    # Find all variables
    pattern = r'\{([^}]+)\}'
    matches = re.findall(pattern, template)
    
    variables_used = []
    unknown_variables = []
    
    for var in matches:
        var_lower = var.lower().strip()
        variables_used.append(var_lower)
        if var_lower not in known_variables:
            # Could be a custom Excel column, not necessarily unknown
            unknown_variables.append(var_lower)
    
    # Generate preview with sample data
    sample_data = {
        "name": "Ahmet Yılmaz",
        "phone": "+905551234567",
        "customer_title": "Mr",
        "custom_data": {
            "company": "ABC Şirketi",
            "amount": "1.500 TL",
            "due_date": "15.02.2026"
        }
    }
    
    preview = process_greeting(template, sample_data, "Solar Agent")
    
    return {
        "valid": True,
        "variables_used": list(set(variables_used)),
        "unknown_variables": unknown_variables,
        "preview": preview
    }


def get_available_variables() -> Dict[str, str]:
    """Get list of available variables with descriptions"""
    return {
        "customer_name": "Customer's full name",
        "first_name": "Customer's first name",
        "last_name": "Customer's last name",
        "customer_title": "Localized title (Bey/Hanım, Mr/Mrs, Herr/Frau)",
        "addressed_name": "Title + name in correct order (e.g. Cenani Bey, Mr Cenani)",
        "company": "Company name",
        "phone": "Phone number",
        "date": "Today's date (DD.MM.YYYY)",
        "time": "Current time (HH:MM)",
        "day": "Day of the week",
        "month": "Month name",
        "year": "Year",
        "agent_name": "AI Agent's name",
        "amount": "Payment amount (from Excel)",
        "due_date": "Due date (from Excel)",
    }


# Example usage
if __name__ == "__main__":
    # Test greeting
    template = """
Merhaba {first_name}, ben {agent_name}. 
Bugün {day} günü, {company} adına arıyorum.
{amount} tutarındaki ödemeniz {due_date} tarihinde yapılması gerekiyor.
Size nasıl yardımcı olabilirim?
"""
    
    customer = {
        "name": "Mehmet Kaya",
        "phone": "+905559876543",
        "custom_data": {
            "company": "XYZ Ltd.",
            "amount": "2.350 TL",
            "due_date": "20.02.2026"
        }
    }
    
    result = process_greeting(template, customer, "Ödeme Asistanı")
    print(result)
    
    # Validate
    validation = validate_greeting_template(template)
    print("\nValidation:", validation)
