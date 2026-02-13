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
        "## ZORUNLU: Telesekreter Algılama (AMD)\n"
        "Bu bir dış arama. Arama cevaplandığı AN, karşı tarafın gerçek bir insan mı "
        "yoksa telesekreter/sesli yanıt sistemi mi olduğunu tespit et.\n\n"
        "Telesekreter İŞARETLERİ (HERHANGİ BİRİ yeterliyken HEMEN kapat):\n"
        "- Önceden kaydedilmiş bir mesaj çalıyorsa (doğal konuşma değil, tek taraflı konuşma)\n"
        "- 'Mesajınızı bırakın', 'Şu anda müsait değiliz', 'Lütfen mesaj bırakın', "
        "'Bip sesinden sonra', 'ulaşamıyoruz', 'meşgul' gibi ifadeler\n"
        "- 'Bip' veya 'biiiip' sesi\n"
        "- 'Mailbox', 'voicemail', 'Anrufbeantworter', 'Nachricht' kelimeleri\n"
        "- Karşı taraf hiç konuşmuyorsa ve sadece müzik, bekleme tonu veya sessizlik varsa\n"
        "- Uzun kesintisiz konuşma (3+ saniye) — gerçek insanlar kısa cevap verir\n"
        "- 'Hinterlassen Sie eine Nachricht', 'nicht erreichbar', 'nach dem Signalton'\n\n"
        "TELESEKRETERSİZ (insan): Karşı taraf 'Alo', 'Efendim', 'Ja', 'Hallo' gibi "
        "KISA bir yanıt veriyorsa bu gerçek insandır, aramaya devam et.\n\n"
        "Telesekreter tespit edersen HEMEN `hangUp` aracını çağır. "
        "Mesaj bırakma, açıklama yapma, sadece ANINDA kapat. Bu EN ÖNCELİKLİ görevindir."
    ),
    "en": (
        "## MANDATORY: Answering Machine Detection (AMD)\n"
        "This is an outbound call. The MOMENT the call is answered, determine whether "
        "the other side is a real human or an answering machine/voicemail.\n\n"
        "ANSWERING MACHINE SIGNS (ANY ONE of these means hang up IMMEDIATELY):\n"
        "- A pre-recorded message is playing (not natural conversation, one-sided speech)\n"
        "- Phrases: 'Leave a message', 'Not available', 'after the beep/tone', "
        "'currently unavailable', 'mailbox', 'voicemail'\n"
        "- A 'beep' or long tone\n"
        "- Only music, hold tone, or silence with no human response\n"
        "- Long uninterrupted speech (3+ seconds) — real humans give short answers\n\n"
        "NOT A MACHINE (human): Short responses like 'Hello', 'Yes', 'Hi' — "
        "this is a real person, continue the call.\n\n"
        "If you detect an answering machine, IMMEDIATELY call the `hangUp` tool. "
        "Do NOT leave a message, do NOT explain, just hang up INSTANTLY. "
        "This is your HIGHEST PRIORITY task."
    ),
    "de": (
        "## PFLICHT: Anrufbeantworter-Erkennung (AMD)\n"
        "Dies ist ein ausgehender Anruf. SOBALD der Anruf angenommen wird, bestimmen Sie, "
        "ob die andere Seite ein echter Mensch oder ein Anrufbeantworter/Voicemail ist.\n\n"
        "ANRUFBEANTWORTER-ZEICHEN (JEDES EINZELNE bedeutet SOFORT auflegen):\n"
        "- Eine aufgezeichnete Nachricht wird abgespielt (einseitiges Sprechen)\n"
        "- Phrasen: 'Hinterlassen Sie eine Nachricht', 'nicht erreichbar', "
        "'nach dem Signalton', 'Mailbox', 'Voicemail', 'zur Zeit nicht erreichbar'\n"
        "- Ein 'Piep'-Ton oder langer Signalton\n"
        "- Nur Musik, Warteton oder Stille ohne menschliche Antwort\n"
        "- Lange ununterbrochene Rede (3+ Sekunden) — echte Menschen antworten kurz\n\n"
        "KEIN ANRUFBEANTWORTER (Mensch): Kurze Antworten wie 'Hallo', 'Ja', 'Bitte' — "
        "dies ist eine echte Person, Gespräch fortsetzen.\n\n"
        "Wenn Sie einen Anrufbeantworter erkennen, rufen Sie SOFORT das `hangUp`-Tool auf. "
        "Hinterlassen Sie KEINE Nachricht, erklären Sie NICHTS, legen Sie einfach SOFORT auf. "
        "Dies ist Ihre HÖCHSTE PRIORITÄT."
    ),
}

# Abbreviated AMD backup text (for Asterisk bridge where AMD() is primary)
AMD_BACKUP_TEXT: str = (
    "If you detect an answering machine, voicemail, or automated greeting system "
    "(pre-recorded message playing, 'leave a message' phrases, beep tones, "
    "long uninterrupted one-sided speech), "
    "IMMEDIATELY call the `hangUp` tool. Do NOT leave a message. "
    "This is your highest priority task."
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
    "CRITICAL RULE — BARGE-IN: When the customer starts speaking, you MUST immediately "
    "stop talking and listen. Never talk over the customer. If the customer interrupts you, "
    "stop your current sentence mid-word and let them speak. After they finish, respond to "
    "what they said. This is the most important rule and must never be violated.\n\n"
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
