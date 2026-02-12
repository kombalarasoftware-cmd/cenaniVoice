"""
Shared constants for the universal prompt builder.

Centralizes duplicated constants from ultravox_provider.py, asterisk_bridge.py,
and openai_realtime.py into a single source of truth.
"""

# ============================================================================
# TITLE TRANSLATIONS - Language-aware Mr/Mrs forms
# Superset from asterisk_bridge.py (12 languages)
# ============================================================================
TITLE_TRANSLATIONS: dict[str, dict[str, str]] = {
    "tr": {"Mr": "Bey", "Mrs": "Hanım"},
    "en": {"Mr": "Mr", "Mrs": "Mrs"},
    "de": {"Mr": "Herr", "Mrs": "Frau"},
    "fr": {"Mr": "Monsieur", "Mrs": "Madame"},
    "es": {"Mr": "Señor", "Mrs": "Señora"},
    "it": {"Mr": "Signore", "Mrs": "Signora"},
    "pt": {"Mr": "Senhor", "Mrs": "Senhora"},
    "nl": {"Mr": "Meneer", "Mrs": "Mevrouw"},
    "ar": {"Mr": "السيد", "Mrs": "السيدة"},
    "zh": {"Mr": "先生", "Mrs": "女士"},
    "ja": {"Mr": "様", "Mrs": "様"},
    "ko": {"Mr": "님", "Mrs": "님"},
}

# Languages where title comes AFTER the name (e.g. "Cenani Bey")
# All others: title BEFORE the name (e.g. "Mr Cenani")
TITLE_AFTER_NAME: set[str] = {"tr", "ja", "ko", "zh"}


# ============================================================================
# LOCALIZED DAY AND MONTH NAMES
# ============================================================================
DAY_NAMES: dict[str, list[str]] = {
    "tr": ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"],
    "en": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
    "de": ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"],
}

MONTH_NAMES: dict[str, list[str]] = {
    "tr": [
        "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
        "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
    ],
    "en": [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ],
    "de": [
        "Januar", "Februar", "März", "April", "Mai", "Juni",
        "Juli", "August", "September", "Oktober", "November", "Dezember",
    ],
}


# ============================================================================
# AMD (ANSWERING MACHINE DETECTION) INSTRUCTIONS
# Per-language detection rules from ultravox_provider.py
# ============================================================================
AMD_PROMPT_INSTRUCTIONS: dict[str, str] = {
    "tr": (
        "Bu bir dış arama. Karşı tarafta bir telesekreter, sesli yanıt sistemi veya "
        "otomatik karşılama olup olmadığını İLK 5 SANİYE içinde tespit etmelisin.\n"
        "Telesekreter İŞARETLERİ:\n"
        "- Önceden kaydedilmiş uzun bir mesaj çalınıyorsa\n"
        "- 'Mesajınızı bırakın', 'Şu anda müsait değiliz', 'Lütfen mesaj bırakın' gibi ifadeler duyarsan\n"
        "- 'Bip' sesi duyarsan\n"
        "- Karşı taraf hiç konuşmuyorsa ve sadece müzik veya bekleme tonu varsa\n"
        "Telesekreter tespit edersen HEMEN `end_call` aracını çağır. "
        "Mesaj bırakmaya ÇALIŞMA, sadece kapat."
    ),
    "en": (
        "This is an outbound call. You MUST detect within the FIRST 5 SECONDS whether "
        "the other side is an answering machine, voicemail system, or automated greeting.\n"
        "ANSWERING MACHINE SIGNS:\n"
        "- A long pre-recorded message is playing\n"
        "- Phrases like 'Leave a message', 'Not available', 'Please leave your message'\n"
        "- A 'beep' tone\n"
        "- The other party is silent with only music or hold tone\n"
        "If you detect an answering machine, IMMEDIATELY call the `end_call` tool. "
        "Do NOT attempt to leave a message, just hang up."
    ),
    "de": (
        "Dies ist ein ausgehender Anruf. Sie MÜSSEN innerhalb der ERSTEN 5 SEKUNDEN erkennen, "
        "ob die andere Seite ein Anrufbeantworter, Voicemail oder automatische Begrüßung ist.\n"
        "ANRUFBEANTWORTER-ZEICHEN:\n"
        "- Eine lange aufgezeichnete Nachricht wird abgespielt\n"
        "- Phrasen wie 'Hinterlassen Sie eine Nachricht', 'Nicht erreichbar'\n"
        "- Ein 'Piep'-Ton\n"
        "- Die andere Seite schweigt mit nur Musik oder Warteton\n"
        "Wenn Sie einen Anrufbeantworter erkennen, rufen Sie SOFORT das `end_call`-Tool auf. "
        "Versuchen Sie NICHT, eine Nachricht zu hinterlassen, legen Sie einfach auf."
    ),
}

# Abbreviated AMD backup text (for Asterisk bridge where AMD() is primary)
AMD_BACKUP_TEXT: str = (
    "If you detect an answering machine, voicemail, or automated greeting system "
    "(pre-recorded message playing, 'leave a message' phrases, beep tones), "
    "IMMEDIATELY call the `end_call` tool. Do NOT leave a message."
)


# ============================================================================
# VOICE INTERACTION RULES
# ============================================================================
VOICE_RULES_BASE: str = (
    "You are interacting with the user over voice, so speak casually and naturally.\n"
    "Keep your responses short and to the point, much like someone would in dialogue.\n"
    "Since this is a voice conversation, do not use lists, bullets, emojis, markdown, "
    "or other things that do not translate to voice.\n"
    "Do not use stage directions or action-based roleplay such as pauses or laughs.\n\n"
    "Always wait for the customer to speak after you ask a question.\n"
    "Never answer your own questions. Never assume what the customer will say.\n"
    "If there is silence, wait at least three to four seconds before prompting again.\n"
    "You are on a phone call. There is natural latency. Be patient.\n\n"
    "Ask only one question per turn, then wait for the answer.\n"
    "Do not chain multiple questions together.\n"
    "Do not combine greetings with questions.\n\n"
    "After receiving important information like a phone number, email, or name, "
    "repeat it back for confirmation and wait for explicit confirmation before proceeding.\n"
    "Do not assume confirmation from silence.\n\n"
    "Match the customer's speaking pace and energy.\n\n"
    "Output phone numbers as individual digits separated by hyphens. "
    "For example, 0-5-3-2-1-2-3-4-5-6-7.\n"
    "Output account numbers and codes as individual digits separated by hyphens.\n"
)

VOICE_RULES_BY_LANGUAGE: dict[str, str] = {
    "tr": (
        "Tarihleri dogal sekilde soyleyin. Ornegin, on iki Subat iki bin yirmi alti.\n"
        "Saatleri dogal soyleyin. Ornegin, on dort otuz.\n"
        "Para tutarlarini dogal soyleyin. Ornegin, iki yuz elli lira.\n"
    ),
    "default": (
        "Output dates as individual components. "
        "For example, December twenty-fifth twenty twenty-two.\n"
        "For times, ten AM instead of 10:00 AM.\n"
        "Read years naturally. For example, twenty twenty-four.\n"
        "For decimals, say point and then each digit. For example, three point one four.\n"
    ),
}
