"""
E-posta bildirim ayarlarını doğrulamak için örnek bir kritik mail gönderir.
Bekleme süresine takılmaz, gönderimi bekler ve sonucu yazar.

Çalıştırma (backend venv aktifken, proje kökünden):
    python scripts/eposta_test.py
"""
import os
import sys
import time

BACKEND_DIZINI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend")
sys.path.insert(0, BACKEND_DIZINI)
from app import bildirim, config  # noqa: E402


def main():
    if not (config.SMTP_KULLANICI and config.SMTP_PAROLA):
        print("backend/.env içinde SMTP_KULLANICI ve SMTP_PAROLA doldurulmalı.")
        return 1
    print(f"Sunucu : {config.SMTP_SUNUCU}:{config.SMTP_PORT} (SSL)")
    print(f"Gönderen: {config.SMTP_KULLANICI}")
    print(f"Alıcı  : {config.BILDIRIM_ALICI}")
    if not config.BILDIRIM_AKTIF:
        print("Not: BILDIRIM_AKTIF=false; backend mail atmaz ama bu test yine de gönderir.")

    olay = {"id": 0, "dugum": "dugum1", "sensor": "alev", "deger": 1,
            "seviye": "kritik", "mesaj": "ALEV ALGILANDI", "zaman": int(time.time())}
    print("Gönderiliyor...")
    if bildirim.hemen_gonder(olay, bastirilan=3):
        print("✓ Gönderildi. Gelen kutusunu (ve spam klasörünü) kontrol edin.")
        return 0
    print("✗ Gönderilemedi (ayrıntı yukarıda).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
