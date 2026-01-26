import os
import re
import tempfile
import yt_dlp


def is_instagram_url(url: str) -> bool:
    """Instagram URL'si olup olmadığını kontrol eder."""
    patterns = [
        r'https?://(www\.)?instagram\.com/p/[\w-]+',
        r'https?://(www\.)?instagram\.com/reel/[\w-]+',
        r'https?://(www\.)?instagram\.com/reels/[\w-]+',
        r'https?://(www\.)?instagram\.com/tv/[\w-]+',
    ]
    return any(re.match(pattern, url) for pattern in patterns)


def extract_instagram_url(text: str) -> str | None:
    """Metin içinden Instagram URL'sini çıkarır."""
    patterns = [
        r'https?://(www\.)?instagram\.com/p/[\w-]+/?(\?[^\s]*)?',
        r'https?://(www\.)?instagram\.com/reel/[\w-]+/?(\?[^\s]*)?',
        r'https?://(www\.)?instagram\.com/reels/[\w-]+/?(\?[^\s]*)?',
        r'https?://(www\.)?instagram\.com/tv/[\w-]+/?(\?[^\s]*)?',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)
    return None


async def download_video(url: str) -> tuple[str, str]:
    """
    Instagram videosunu indirir.

    Returns:
        tuple: (video_path, audio_path) - Video ve ses dosyası yolları

    Raises:
        Exception: İndirme başarısız olursa
    """
    temp_dir = tempfile.mkdtemp()
    output_template = os.path.join(temp_dir, 'video.%(ext)s')

    ydl_opts = {
        'format': 'best',
        'outtmpl': output_template,
        'quiet': True,
        'no_warnings': True,
        'extract_audio': False,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_ext = info.get('ext', 'mp4')
            video_path = os.path.join(temp_dir, f'video.{video_ext}')

            if not os.path.exists(video_path):
                # Bazen farklı extension ile kaydedilebilir
                for f in os.listdir(temp_dir):
                    if f.startswith('video.'):
                        video_path = os.path.join(temp_dir, f)
                        break

            return video_path, temp_dir

    except Exception as e:
        # Temizlik
        if os.path.exists(temp_dir):
            for f in os.listdir(temp_dir):
                os.remove(os.path.join(temp_dir, f))
            os.rmdir(temp_dir)
        raise Exception(f"Video indirilemedi: {str(e)}")


def cleanup(temp_dir: str):
    """Geçici dosyaları temizler."""
    if os.path.exists(temp_dir):
        for f in os.listdir(temp_dir):
            try:
                os.remove(os.path.join(temp_dir, f))
            except:
                pass
        try:
            os.rmdir(temp_dir)
        except:
            pass
