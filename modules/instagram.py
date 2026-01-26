import os
import re
import tempfile
import instaloader

from config import INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD


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


def extract_shortcode(url: str) -> str:
    """URL'den Instagram shortcode'u çıkarır."""
    # https://www.instagram.com/reel/ABC123/ -> ABC123
    # https://www.instagram.com/p/XYZ789/ -> XYZ789
    match = re.search(r'/(p|reel|reels|tv)/([\w-]+)', url)
    if match:
        return match.group(2)
    return None


async def download_video(url: str) -> tuple[str, str]:
    """
    Instagram videosunu indirir.

    Returns:
        tuple: (video_path, temp_dir) - Video dosyası yolu ve geçici klasör

    Raises:
        Exception: İndirme başarısız olursa
    """
    temp_dir = tempfile.mkdtemp()

    try:
        # Instaloader instance oluştur
        L = instaloader.Instaloader(
            download_videos=True,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            compress_json=False,
            dirname_pattern=temp_dir,
            filename_pattern='{shortcode}'
        )

        # Login yap
        if INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD:
            try:
                # Önce session dosyasını dene
                session_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instagram_session')
                if os.path.exists(session_file):
                    L.load_session_from_file(INSTAGRAM_USERNAME, session_file)
                else:
                    L.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
            except Exception as login_error:
                # Login başarısız olursa anonim devam et
                pass

        # Shortcode'u çıkar
        shortcode = extract_shortcode(url)
        if not shortcode:
            raise Exception("Geçersiz Instagram URL'si")

        # Post'u indir
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        L.download_post(post, target=temp_dir)

        # Video dosyasını bul
        video_path = None
        for f in os.listdir(temp_dir):
            if f.endswith('.mp4'):
                video_path = os.path.join(temp_dir, f)
                break

        if not video_path:
            raise Exception("Video dosyası bulunamadı")

        return video_path, temp_dir

    except instaloader.exceptions.LoginRequiredException:
        cleanup(temp_dir)
        raise Exception("Bu video için login gerekiyor")
    except instaloader.exceptions.PrivateProfileNotFollowedException:
        cleanup(temp_dir)
        raise Exception("Bu profil gizli")
    except Exception as e:
        cleanup(temp_dir)
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
