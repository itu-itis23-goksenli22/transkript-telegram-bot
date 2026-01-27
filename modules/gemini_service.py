import time
import io
import os
import google.generativeai as genai
from google import genai as genai_new
from google.genai import types
from config import GEMINI_API_KEY

# Gemini API yapılandırması (eski SDK - transkript için)
genai.configure(api_key=GEMINI_API_KEY)

# Yeni Gemini client (Nano Banana Pro için)
genai_client = genai_new.Client(api_key=GEMINI_API_KEY)


async def transcribe_video(video_path: str) -> str:
    """
    Video dosyasından transkript çıkarır.

    Args:
        video_path: Video dosyasının yolu

    Returns:
        Transkript metni
    """
    model = genai.GenerativeModel('gemini-2.0-flash')

    # Video dosyasını yükle
    video_file = genai.upload_file(video_path)
    
    # Dosyanın işlenmesini bekle
    while video_file.state.name == "PROCESSING":
        time.sleep(2)
        video_file = genai.get_file(video_file.name)

    if video_file.state.name == "FAILED":
        raise ValueError("Video işlenirken hata oluştu.")

    # Transkript iste
    prompt = """Bu videodaki konuşmaları tam olarak transkript et.
    Sadece konuşulan metni yaz, başka hiçbir şey ekleme.
    Eğer videoda konuşma yoksa "Bu videoda konuşma bulunamadı." yaz."""

    response = model.generate_content([video_file, prompt])

    # Dosyayı sil
    try:
        video_file.delete()
    except:
        pass

    return response.text.strip()


async def translate_text(text: str, target_language: str) -> str:
    """
    Metni belirtilen dile çevirir.

    Args:
        text: Çevrilecek metin
        target_language: Hedef dil ("Turkish" veya "English")

    Returns:
        Çevrilmiş metin
    """
    if not text or text == "Bu videoda konuşma bulunamadı.":
        return text

    model = genai.GenerativeModel('gemini-2.0-flash')

    prompt = f"""Aşağıdaki metni {target_language} diline çevir.
Sadece çeviriyi yaz, başka hiçbir şey ekleme.
Eğer metin zaten {target_language} dilindeyse, aynen yaz.

Metin:
{text}"""

    response = model.generate_content(prompt)
    return response.text.strip()


async def process_video(video_path: str) -> dict:
    """
    Video dosyasını işler: transkript çıkarır ve çevirileri yapar.

    Args:
        video_path: Video dosyasının yolu

    Returns:
        dict: {
            'original': str,  # Orijinal transkript
            'turkish': str,   # Türkçe çeviri
            'english': str    # İngilizce çeviri
        }
    """
    # Transkript çıkar
    original = await transcribe_video(video_path)

    # Çevirileri yap
    turkish = await translate_text(original, "Turkish")
    english = await translate_text(original, "English")

    return {
        'original': original,
        'turkish': turkish,
        'english': english
    }


async def generate_hook_text(transcript: str) -> str:
    """
    Transkriptten kısa ve dikkat çekici hook text oluşturur.

    Args:
        transcript: Video transkripti

    Returns:
        2-5 kelimelik hook text
    """
    model = genai.GenerativeModel('gemini-2.0-flash')

    prompt = f"""Aşağıdaki video transkriptinden Instagram Reels thumbnail için kısa ve dikkat çekici bir başlık (hook text) oluştur.

Transkript:
{transcript[:500]}

Kurallar:
1. SADECE 2-5 kelime olmalı
2. Türkçe veya İngilizce olabilir (hangisi daha etkili olacaksa)
3. Büyük harfle yaz
4. Merak uyandırıcı olmalı
5. Sadece başlığı yaz, başka bir şey yazma

Örnek başlıklar:
- "BU SIR DEĞİŞTİRİR"
- "90% AI 10% HUMAN"
- "FREE TOOLS FOR EVERYTHING"
- "GOOGLE'S FREE TOOLS ARE INSANE" """

    response = model.generate_content(prompt)
    return response.text.strip()


async def generate_thumbnail_prompt(transcript: str, hook_text: str) -> str:
    """
    Transkriptten thumbnail için prompt oluşturur.

    Args:
        transcript: Video transkripti
        hook_text: Görselin üzerine yazılacak hook text

    Returns:
        Thumbnail için optimize edilmiş prompt
    """
    model = genai.GenerativeModel('gemini-2.0-flash')

    prompt = f"""Create an Instagram Reels thumbnail image prompt based on this video transcript.

Transcript summary:
{transcript[:500]}

Hook text to display on image: "{hook_text}"

Requirements:
1. Pop-art or vibrant artistic style
2. Bold, saturated colors (like pink, yellow, cyan, orange)
3. Eye-catching and viral-worthy design
4. Include the hook text "{hook_text}" prominently displayed with bold typography
5. Modern, trendy Instagram aesthetic
6. 9:16 vertical format suitable for Reels
7. High contrast and attention-grabbing
8. Can include relevant visual elements related to the topic

Output ONLY the image generation prompt in English, nothing else.

Example style: "Vibrant pop-art style Instagram Reels thumbnail with bold text '{hook_text}' in large yellow typography, colorful artistic background with [relevant visual], saturated colors, modern social media aesthetic, eye-catching design, 9:16 vertical format" """

    response = model.generate_content(prompt)
    return response.text.strip()


# Sabit thumbnail input görseli
THUMBNAIL_BASE_IMAGE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'thumbnail_base.jpg')


async def generate_topic_summary(transcript: str) -> str:
    """
    Transkriptten konu özeti çıkarır.

    Args:
        transcript: Video transkripti

    Returns:
        Kısa konu özeti (1-2 cümle)
    """
    model = genai.GenerativeModel('gemini-2.0-flash')

    prompt = f"""Aşağıdaki video transkriptinin konusunu 1-2 cümleyle özetle.
Sadece konuyu yaz, başka bir şey ekleme.

Transkript:
{transcript[:800]}

Örnek çıktılar:
- "Python programlama eğitimi ve temel kodlama teknikleri"
- "Yapay zeka araçlarının iş hayatında kullanımı"
- "Instagram'da viral olmanın sırları"
- "Kişisel gelişim ve motivasyon tavsiyeleri" """

    response = model.generate_content(prompt)
    return response.text.strip()


async def generate_thumbnail(video_path: str) -> tuple[bytes, str]:
    """
    Sabit görsel üzerine transkripte göre thumbnail oluşturur (image-to-image).

    Args:
        video_path: Video dosyasının yolu (sadece transkript için)

    Returns:
        tuple: (PNG formatında görsel bytes, hook_text)
    """
    # Transkript çıkar (konuyu anlamak için)
    transcript = await transcribe_video(video_path)

    # Hook text ve konu özeti oluştur
    if transcript == "Bu videoda konuşma bulunamadı.":
        hook_text = "WATCH THIS"
        topic_summary = "General content"
    else:
        hook_text = await generate_hook_text(transcript)
        topic_summary = await generate_topic_summary(transcript)

    # Sabit görseli oku
    with open(THUMBNAIL_BASE_IMAGE, 'rb') as f:
        base_image_bytes = f.read()

    # Image-to-image prompt oluştur (transkript konusu dahil)
    edit_prompt = f"""Transform this image into a vibrant, eye-catching Instagram Reels thumbnail.

VIDEO TOPIC: {topic_summary}

Requirements:
1. Keep the main subject/person from the original image
2. Add bold, large text "{hook_text}" prominently displayed (preferably at top or bottom)
3. Apply pop-art or vibrant artistic style with saturated colors (pink, yellow, cyan, orange)
4. Add visual elements or icons related to the topic: {topic_summary}
5. Make it look professional and viral-worthy
6. Add visual effects like color splash, gradients, or artistic filters
7. The text should have a contrasting background/outline for readability
8. Keep the 9:16 vertical format

Style reference: Modern Instagram Reels thumbnails with bold typography, vibrant colors, and topic-relevant visual elements."""

    # Nano Banana Pro (Gemini 3 Pro Image) ile image-to-image düzenleme yap
    response = genai_client.models.generate_content(
        model="gemini-3-pro-image-preview",
        contents=[
            types.Part.from_bytes(data=base_image_bytes, mime_type="image/jpeg"),
            edit_prompt
        ],
        config=types.GenerateContentConfig(
            response_modalities=['TEXT', 'IMAGE'],
            image_config=types.ImageConfig(
                aspect_ratio="9:16",
                image_size="2K"
            )
        ),
    )

    # Görseli bytes olarak al
    for part in response.candidates[0].content.parts:
        if part.inline_data is not None:
            return (part.inline_data.data, hook_text)

    raise ValueError("Görsel oluşturulamadı.")
