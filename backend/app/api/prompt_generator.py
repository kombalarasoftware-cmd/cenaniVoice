"""
Prompt Generator API
Uses GPT-4o to generate professional prompts from user descriptions
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import httpx
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/prompt-generator", tags=["Prompt Generator"])


class PromptGenerateRequest(BaseModel):
    """Request model for prompt generation"""
    description: str = Field(..., min_length=5, max_length=2000, description="User's description of what they want")
    language: str = Field(default="tr", description="Output language: tr, en, de, etc.")
    agent_type: Optional[str] = Field(default=None, description="Type of agent: sales, support, collection, appointment, survey")
    tone: Optional[str] = Field(default="professional", description="Tone: professional, friendly, formal, casual")
    existing_prompt: Optional[str] = Field(default=None, description="Existing prompt to improve")


class PromptGenerateResponse(BaseModel):
    """Response model for prompt generation"""
    prompt: str
    suggestions: list[str] = []


# System prompt for the prompt generator
PROMPT_GENERATOR_SYSTEM = """Sen bir AI asistan prompt mühendisisin. Kullanıcının verdiği kısa açıklamayı profesyonel, etkili ve yapılandırılmış bir sistem prompt'una dönüştürüyorsun.

## Kurallar:

1. **Rol Tanımı**: Prompt'un başında net bir rol tanımı yap (örn: "Sen bir güneş enerjisi satış temsilcisisin")

2. **Davranış Kuralları**: Agent'ın nasıl davranması gerektiğini belirt:
   - Ses tonu (samimi, profesyonel, resmi)
   - Konuşma hızı (kısa-öz, detaylı)
   - Yaklaşım (empati, çözüm odaklı)

3. **Görev Tanımı**: Ana hedefi ve alt hedefleri belirt

4. **Kısıtlamalar**: Yapılmaması gerekenleri belirt:
   - Konuşulmaması gereken konular
   - Verilmemesi gereken bilgiler
   - Kaçınılması gereken davranışlar

5. **Senaryo Yönetimi**: Olası durumları ve nasıl yaklaşılacağını belirt:
   - Müşteri ilgilenmiyorsa
   - Müşteri soru sorarsa
   - Müşteri şikayet ederse

6. **Çıktı Formatı**: Konuşma stilini belirt

## Format:
Markdown formatında, okunabilir ve düzenli bir prompt oluştur.

## Dil:
Prompt'u kullanıcının belirttiği dilde yaz. Varsayılan Türkçe.

## Önemli:
- Prompt kısa ve öz olsun, gereksiz detaylardan kaçın
- Pratik ve uygulanabilir olsun
- Telefon görüşmesi için optimize edilmiş olsun (kısa cevaplar, net yönergeler)
"""


PROMPT_IMPROVER_SYSTEM = """Sen bir AI asistan prompt mühendisisin. Mevcut prompt'u analiz edip iyileştiriyorsun.

## Görevin:
1. Mevcut prompt'u analiz et
2. Eksik veya zayıf noktaları belirle
3. Kullanıcının isteğine göre iyileştir
4. Yapılandırılmış ve profesyonel bir prompt oluştur

## İyileştirme Alanları:
- Rol tanımının netliği
- Davranış kurallarının belirginliği
- Senaryo yönetimi
- Kısıtlamalar ve sınırlar
- Çıktı formatı

## Önemli:
- Orijinal prompt'un amacını koru
- Sadece gerekli iyileştirmeleri yap
- Fazla uzatma, özlü tut
"""


@router.post("/generate", response_model=PromptGenerateResponse)
async def generate_prompt(request: PromptGenerateRequest):
    """
    Generate a professional prompt from user description using GPT-4o
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured")
    
    # Build the user message
    user_message_parts = [f"Kullanıcı açıklaması: {request.description}"]
    
    if request.language != "tr":
        user_message_parts.append(f"Dil: {request.language}")
    
    if request.agent_type:
        agent_types = {
            "sales": "Satış temsilcisi",
            "support": "Müşteri destek temsilcisi", 
            "collection": "Tahsilat temsilcisi",
            "appointment": "Randevu planlama asistanı",
            "survey": "Anket yapan temsilci"
        }
        user_message_parts.append(f"Agent tipi: {agent_types.get(request.agent_type, request.agent_type)}")
    
    if request.tone:
        tones = {
            "professional": "Profesyonel",
            "friendly": "Samimi ve arkadaşça",
            "formal": "Resmi",
            "casual": "Günlük/rahat"
        }
        user_message_parts.append(f"Ton: {tones.get(request.tone, request.tone)}")
    
    user_message = "\n".join(user_message_parts)
    
    # Choose system prompt based on whether we're improving or generating
    if request.existing_prompt:
        system_prompt = PROMPT_IMPROVER_SYSTEM
        user_message = f"Mevcut Prompt:\n{request.existing_prompt}\n\nKullanıcının isteği:\n{request.description}"
    else:
        system_prompt = PROMPT_GENERATOR_SYSTEM
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-4o",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 2000
                }
            )
            
            if response.status_code != 200:
                logger.error(f"OpenAI API error: {response.text}")
                raise HTTPException(status_code=response.status_code, detail="OpenAI API error")
            
            data = response.json()
            generated_prompt = data["choices"][0]["message"]["content"]
            
            # Generate suggestions
            suggestions = []
            if not request.existing_prompt:
                suggestions = [
                    "İsterseniz bu prompt'u daha da iyileştirebilirim",
                    "Spesifik senaryolar ekleyebilirim",
                    "Farklı bir ton ile yeniden yazabilirim"
                ]
            
            return PromptGenerateResponse(
                prompt=generated_prompt,
                suggestions=suggestions
            )
            
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="OpenAI API timeout")
    except Exception as e:
        logger.error(f"Prompt generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/improve", response_model=PromptGenerateResponse)
async def improve_prompt(request: PromptGenerateRequest):
    """
    Improve an existing prompt based on user feedback
    """
    if not request.existing_prompt:
        raise HTTPException(status_code=400, detail="existing_prompt is required for improvement")
    
    return await generate_prompt(request)


@router.get("/suggestions")
async def get_prompt_suggestions():
    """
    Get prompt improvement suggestions
    """
    return {
        "suggestions": [
            {
                "id": "clarity",
                "label": "How can my prompt be better?",
                "description": "Analyze the prompt and suggest improvements"
            },
            {
                "id": "rewrite",
                "label": "Rewrite this prompt clearly",
                "description": "Rewrite the prompt in a clearer, more structured way"
            },
            {
                "id": "debug",
                "label": "Debug an issue",
                "description": "Help identify and fix issues with the prompt"
            },
            {
                "id": "scenarios",
                "label": "Add edge case scenarios",
                "description": "Add handling for edge cases and difficult situations"
            },
            {
                "id": "shorter",
                "label": "Make it more concise",
                "description": "Shorten the prompt while keeping the essential parts"
            }
        ]
    }


@router.get("/templates")
async def get_prompt_templates():
    """
    Get pre-built prompt templates for common use cases
    """
    return {
        "templates": [
            {
                "id": "sales",
                "name": "Satış Temsilcisi",
                "description": "Ürün veya hizmet satışı için",
                "template": """Sen {company_name} firmasının satış temsilcisisin. 

## Görevin:
Müşterilerle telefonda görüşerek {product_name} hakkında bilgi vermek ve satış yapmak.

## Davranış Kuralları:
- Samimi ve profesyonel ol
- Kısa ve öz cevaplar ver
- Müşterinin ihtiyaçlarını dinle
- Baskıcı olma

## Senaryo Yönetimi:
- İlgilenmiyorsa: Nazikçe teşekkür et ve görüşmeyi sonlandır
- Fiyat sorarsa: Detaylı bilgi ver ve fırsat varsa belirt
- Düşüneceğim derse: Bir sonraki adımı planla (geri arama, e-posta)

## Kısıtlamalar:
- Rakip firmalar hakkında olumsuz konuşma
- Olmayan özellikleri söyleme
- Agresif satış taktikleri kullanma"""
            },
            {
                "id": "appointment",
                "name": "Randevu Asistanı",
                "description": "Randevu planlama ve yönetimi için",
                "template": """Sen {company_name} firmasının randevu asistanısın.

## Görevin:
Müşterilerle telefonda görüşerek randevu almak veya mevcut randevuları yönetmek.

## Davranış Kuralları:
- Profesyonel ve yardımsever ol
- Net ve anlaşılır konuş
- Uygun tarih ve saatleri öner

## Süreç:
1. Müşteriyi selamla
2. Randevu isteğini al
3. Uygun tarih/saat öner
4. Randevuyu onayla
5. Özet bilgi ver

## Kısıtlamalar:
- Mesai saatleri dışında randevu verme
- Tıbbi veya hukuki tavsiye verme"""
            },
            {
                "id": "collection",
                "name": "Tahsilat Temsilcisi",
                "description": "Ödeme hatırlatma ve tahsilat için",
                "template": """Sen {company_name} firmasının tahsilat temsilcisisin.

## Görevin:
Vadesi geçmiş ödemeler hakkında müşterileri bilgilendirmek ve ödeme planı oluşturmak.

## Davranış Kuralları:
- Profesyonel ve saygılı ol
- Anlayışlı ama kararlı ol
- Çözüm odaklı yaklaş
- Tehditkâr veya kaba olma

## Süreç:
1. Kendinizi tanıtın
2. Borç durumunu açıklayın
3. Ödeme seçenekleri sunun
4. Anlaşmayı kaydedin

## Kısıtlamalar:
- Yasal işlem tehdidinde bulunma (yetkiniz yoksa)
- Kişisel hakaretler
- Gece yarısı veya uygunsuz saatlerde arama"""
            },
            {
                "id": "support",
                "name": "Müşteri Destek",
                "description": "Müşteri sorunlarını çözmek için",
                "template": """Sen {company_name} firmasının müşteri destek temsilcisisin.

## Görevin:
Müşterilerin sorunlarını dinlemek, anlamak ve çözmek.

## Davranış Kuralları:
- Empati göster
- Sabırlı ve anlayışlı ol
- Çözüm odaklı düşün
- Net ve anlaşılır açıklamalar yap

## Süreç:
1. Sorunu dinle ve anla
2. Gerekirse sorular sor
3. Çözüm öner veya yönlendir
4. Memnuniyeti kontrol et

## Kısıtlamalar:
- Müşteriyi suçlama
- "Yapamayız" yerine alternatif sun
- Teknik jargon kullanma"""
            },
            {
                "id": "survey",
                "name": "Anket Yapan",
                "description": "Müşteri memnuniyeti veya pazar araştırması için",
                "template": """Sen {company_name} firması adına anket yapan bir temsilcisin.

## Görevin:
Müşterilerden geri bildirim toplamak için kısa anket uygulamak.

## Davranış Kuralları:
- Nazik ve kısa ol
- Zamanlarına saygı göster
- Tarafsız sorular sor

## Süreç:
1. Kendinizi tanıtın
2. Anketin amacını ve süresini belirtin
3. Soruları sırayla sorun
4. Teşekkür edin

## Kısıtlamalar:
- Yönlendirici sorular sorma
- 5 dakikadan uzun tutma
- Satış yapmaya çalışma"""
            }
        ]
    }
