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
    session_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instagram_session')

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
            filename_pattern='{shortcode}',
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 15_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 Instagram 239.2.0.12.109 (iPhone12,1; iOS 15_5; en_US; en-US; scale=2.00; 828x1792; 376668393)"
        )

        def login_to_instagram():
            if INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD:
                try:
                    # Önce session dosyasını dene
                    if os.path.exists(session_file):
                        try:
                            L.load_session_from_file(INSTAGRAM_USERNAME, session_file)
                            print("Session yüklendi.")
                        except Exception as e:
                            print(f"Session yüklenirken hata: {e}")
                            L.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
                    else:
                        print("Session dosyası yok, yeni giriş yapılıyor...")
                        L.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
                    
                    # Başarılı giriş sonrası session kaydet
                    L.save_session_to_file(filename=session_file)
                    
                except Exception as login_error:
                    print(f"Login hatası: {login_error}")
                    # Login başarısız olsa da devam et (anonim deneme)
                    pass

        # İlk deneme
        login_to_instagram()

        # Shortcode'u çıkar
        shortcode = extract_shortcode(url)
        if not shortcode:
            raise Exception("Geçersiz Instagram URL'si")

        try:
            # Post'u indir
            post = instaloader.Post.from_shortcode(L.context, shortcode)
            L.download_post(post, target=temp_dir)
        except (instaloader.ConnectionException, instaloader.QueryReturnedNotFoundException, instaloader.LoginRequiredException) as e:
            # 401 veya benzeri hatalarda session'ı silip tekrar dene
            error_str = str(e)
            if "401" in error_str or "fail" in error_str or isinstance(e, instaloader.LoginRequiredException):
                print(f"Hata alındı ({error_str}), session silinip tekrar deneniyor...")
                if os.path.exists(session_file):
                    os.remove(session_file)
                
                # Yeni temiz instance
                L = instaloader.Instaloader(
                    download_videos=True,
                    download_video_thumbnails=False,
                    download_geotags=False,
                    download_comments=False,
                    save_metadata=False,
                    compress_json=False,
                    dirname_pattern=temp_dir,
                    filename_pattern='{shortcode}',
                    user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 15_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 Instagram 239.2.0.12.109 (iPhone12,1; iOS 15_5; en_US; en-US; scale=2.00; 828x1792; 376668393)"
                )
                # Tekrar login (session dosyası olmadığı için taze login yapacak)
                login_to_instagram()
                
                # Tekrar indir
                post = instaloader.Post.from_shortcode(L.context, shortcode)
                L.download_post(post, target=temp_dir)
            else:
                raise e

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
