import os
import base64

def generate_string():
    session_file = os.path.join(os.path.dirname(__file__), '..', 'instagram_session')
    
    if not os.path.exists(session_file):
        print("❌ Hata: 'instagram_session' dosyası bulunamadı.")
        print("Lütfen önce 'python modules/login_helper.py' çalıştırarak giriş yapın.")
        return

    try:
        with open(session_file, 'rb') as f:
            data = f.read()
            encoded = base64.b64encode(data).decode('utf-8')
            
        print("\n✅ Session string oluşturuldu!")
        print("Aşağıdaki uzun metni kopyalayıp Railway'de 'INSTAGRAM_SESSION_DATA' değişkenine yapıştırın:\n")
        print("-" * 50)
        print(encoded)
        print("-" * 50)
        print("\n⚠️ Not: Bu string çok uzun olabilir, hepsini kopyaladığınızdan emin olun.")
        
    except Exception as e:
        print(f"Hata: {e}")

if __name__ == "__main__":
    generate_string()
