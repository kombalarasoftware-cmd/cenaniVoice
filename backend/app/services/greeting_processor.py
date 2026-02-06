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


def get_system_variables() -> Dict[str, str]:
    """Get current system variables"""
    now = datetime.now()
    
    return {
        "date": now.strftime("%d.%m.%Y"),
        "time": now.strftime("%H:%M"),
        "day": TURKISH_DAYS.get(now.weekday(), ""),
        "month": TURKISH_MONTHS.get(now.month, ""),
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


def process_greeting(
    template: str,
    customer_data: Optional[Dict[str, Any]] = None,
    agent_name: str = "VoiceAI",
    custom_variables: Optional[Dict[str, str]] = None
) -> str:
    """
    Process greeting template with dynamic variables
    
    Args:
        template: Greeting template with {variable} placeholders
        customer_data: Customer information from PhoneNumber model
        agent_name: Name of the AI agent
        custom_variables: Additional custom variables
        
    Returns:
        Processed greeting string
    """
    if not template:
        return ""
    
    # Build variables dictionary
    variables: Dict[str, str] = {}
    
    # 1. System variables (date, time, etc.)
    variables.update(get_system_variables())
    
    # 2. Agent variables
    variables["agent_name"] = agent_name
    
    # 3. Customer variables
    if customer_data:
        full_name = customer_data.get("name", "")
        variables["customer_name"] = full_name
        variables["first_name"] = extract_first_name(full_name)
        variables["last_name"] = extract_last_name(full_name)
        variables["phone"] = customer_data.get("phone", "")
        
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
        "customer_name", "first_name", "last_name", "company",
        "phone", "date", "time", "day", "month", "year",
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
        "customer_name": "Müşterinin tam adı",
        "first_name": "Müşterinin adı",
        "last_name": "Müşterinin soyadı",
        "company": "Şirket adı",
        "phone": "Telefon numarası",
        "date": "Bugünün tarihi (GG.AA.YYYY)",
        "time": "Şu anki saat (SS:DD)",
        "day": "Haftanın günü (Pazartesi, Salı, ...)",
        "month": "Ay adı (Ocak, Şubat, ...)",
        "year": "Yıl",
        "agent_name": "AI Agent'ın adı",
        "amount": "Ödeme tutarı (Excel'den)",
        "due_date": "Vade tarihi (Excel'den)",
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
