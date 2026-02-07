-- Fix Turkish characters for survey agent
UPDATE agents SET 
    name = 'Müşteri Memnuniyeti Anketi',
    description = 'Koşullu dallanma özellikli örnek anket agent. Müşteri memnuniyetini ölçer ve sorunları kategorize eder.',
    greeting_message = 'Merhaba! Ben müşteri memnuniyeti asistanıyım. Sizinle kısa bir anket yapmak istiyorum, sadece birkaç dakikanızı alacak. Başlayabilir miyiz?',
    prompt_role = 'Sen profesyonel ve samimi bir anket asistanısın. Müşterilerden geri bildirim topluyorsun.',
    prompt_personality = 'Bir şirketin müşteri hizmetleri departmanı için çalışıyorsun.',
    prompt_context = 'Nazik, sabırlı ve profesyonel bir tonda konuş.',
    prompt_pronunciations = '1. Müşteriyi selamla
2. Onay al, anketi başlat
3. Her soruyu sor ve cevabı kaydet
4. Teşekkür et ve bitir',
    prompt_sample_phrases = 'Müşteriyi zorla ankete dahil etme. Cevapları yönlendirme.',
    survey_config = '{
        "enabled": true,
        "questions": [
            {
                "id": "q1",
                "type": "multiple_choice",
                "text": "Hizmetimizden genel olarak memnun musunuz?",
                "required": true,
                "options": ["Çok memnunum", "Memnunum", "Memnun değilim"],
                "next_by_option": {
                    "Çok memnunum": "q2_puan",
                    "Memnunum": "q2_puan",
                    "Memnun değilim": "q2_sorun"
                }
            },
            {
                "id": "q2_puan",
                "type": "rating",
                "text": "1-10 arası puan verir misiniz?",
                "required": true,
                "min_value": 1,
                "max_value": 10,
                "next": "q3_tavsiye"
            },
            {
                "id": "q2_sorun",
                "type": "multiple_choice",
                "text": "Hangi konuda sorun yaşadınız?",
                "required": true,
                "options": ["Ürün kalitesi", "Teslimat", "Müşteri hizmetleri", "Fiyat", "Diğer"],
                "next": "q2b_detay"
            },
            {
                "id": "q2b_detay",
                "type": "open_ended",
                "text": "Sorunu kısaca anlatır mısınız?",
                "required": false,
                "next": "q3_tavsiye"
            },
            {
                "id": "q3_tavsiye",
                "type": "yes_no",
                "text": "Bizi arkadaşlarınıza tavsiye eder misiniz?",
                "required": true
            }
        ],
        "start_question": "q1",
        "completion_message": "Anketimize katıldığınız için teşekkür ederiz!",
        "abort_message": "Anket iptal edildi. İyi günler dileriz.",
        "show_progress": true
    }'
WHERE id = 13;
