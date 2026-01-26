import os
import instaloader
from config import INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD

def manual_login():
    print("Instagram Login Yardımcısı")
    print("--------------------------")
    
    if not INSTAGRAM_USERNAME or not INSTAGRAM_PASSWORD:
        print("Hata: .env dosyasında INSTAGRAM_USERNAME veya INSTAGRAM_PASSWORD eksik.")
        return

    print(f"Kullanıcı: {INSTAGRAM_USERNAME}")
    print("Giriş yapılıyor...")

    L = instaloader.Instaloader(
        user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 15_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 Instagram 239.2.0.12.109 (iPhone12,1; iOS 15_5; en_US; en-US; scale=2.00; 828x1792; 376668393)"
    )
    session_file = os.path.join(os.path.dirname(__file__), 'instagram_session')

    try:
        # Eski session varsa yüklemeyi dene (amaç sadece test etmek değil, tazelemek)
        # Ama checkpoint hatası aldığımız için direkt login denemek daha iyi olabilir.
        if os.path.exists(session_file):
            print(f"Mevcut session dosyası bulundu: {session_file}")
            print("Siliniyor ve yeniden giriş yapılıyor...")
            os.remove(session_file)

        L.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
        print("\n✅ Başarıyla giriş yapıldı!")
        
        L.save_session_to_file(filename=session_file)
        print(f"✅ Session dosyası kaydedildi: {session_file}")
        print("Şimdi botu tekrar çalıştırabilirsiniz.")

    except instaloader.TwoFactorAuthRequiredException:
        print("\n⚠️ İki faktörlü doğrulama (2FA) gerekiyor.")
        code = input("Lütfen SMS/Email ile gelen kodu girin: ")
        L.two_factor_login(code)
        
        L.save_session_to_file(filename=session_file)
        print(f"✅ Session dosyası kaydedildi: {session_file}")
        
    except instaloader.ConnectionException as e:
        print(f"\n❌ Bağlantı hatası: {e}")
        if "Checkpoint" in str(e):
            print("\n⚠️ Instagram güvenlik kontrolüne takıldı (Checkpoint).")
            print("Lütfen şu adımları deneyin:")
            print("1. Bu bilgisayarda/IP'de tarayıcıdan Instagram'a giriş yapın.")
            print("2. 'Bu bendim' (This was me) uyarısını onaylayın.")
            print("3. Bu scripti tekrar çalıştırın.")
            
    except Exception as e:
        print(f"\n❌ Bir hata oluştu: {e}")

if __name__ == "__main__":
    manual_login()
