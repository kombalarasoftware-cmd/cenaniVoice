"""Fix Agent #1: Set proper Turkish characters, provider=ultravox, voice=Doga-Turkish"""
from app.core.database import SessionLocal
from app.models.models import Agent

db = SessionLocal()
a = db.query(Agent).filter(Agent.id == 1).first()

# Fix provider and voice
a.provider = "ultravox"
a.voice = "Doga-Turkish"

# Fix prompts with proper Turkish characters
a.prompt_role = (
    "Sen VoiceAI platformunun test ajansısın. Adın Doğa. Türkçe konuşuyorsun.\n"
    "Görev: Müşterileri aramak ve onlara yardımcı olmak.\n"
    "Kibarca selamlayarak kendini tanıt ve nasıl yardımcı olabileceğini sor."
)

a.prompt_personality = (
    "Profesyonel, sıcakkanlı ve yardımsever bir ses tonuyla konuş.\n"
    "Kısa ve net cevaplar ver. Gereksiz uzatma."
)

a.prompt_context = "Bu bir test aramasıdır. Müşteri ile konuşurken nazik ol."

a.greeting_message = "Merhaba, ben Doğa. VoiceAI platformundan arıyorum. Size nasıl yardımcı olabilirim?"

a.prompt_language = "Türkçe konuş. Tüm yanıtların Türkçe olmalı. Kesinlikle İngilizce kullanma."

a.first_speaker = "agent"

db.commit()
print(f"Updated agent #{a.id}:")
print(f"  provider={a.provider}")
print(f"  voice={a.voice}")
print(f"  greeting={a.greeting_message}")
print(f"  prompt_role={a.prompt_role[:80]}...")
db.close()
