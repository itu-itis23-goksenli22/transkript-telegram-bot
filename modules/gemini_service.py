import time
import google.generativeai as genai
from config import GEMINI_API_KEY

# Gemini API yapılandırması
genai.configure(api_key=GEMINI_API_KEY)


async def transcribe_video(video_path: str) -> str:
    """
    Video dosyasından transkript çıkarır.

    Args:
        video_path: Video dosyasının yolu

    Returns:
        Transkript metni
    """
    model = genai.GenerativeModel('gemini-1.5-flash')

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

    model = genai.GenerativeModel('gemini-1.5-flash')

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
