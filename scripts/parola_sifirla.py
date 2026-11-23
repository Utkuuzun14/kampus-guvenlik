"""
Panel kullanıcısının parolasını sıfırlama (unutulan admin parolası dahil).
Etkileşimlidir: kullanıcı adı ve iki kez yeni parola sorar; parola ekranda
görünmez (getpass). Kurallar backend'le aynıdır (app/veritabani.py): parola
8-128 karakter. Rol ve aktiflik değişmez.

Backend açıkken de çalıştırılabilir.

Çalıştırma (backend venv aktifken, proje kökünden):
    python scripts/parola_sifirla.py
    python scripts/parola_sifirla.py utku     # kullanıcı adını sormadan
"""
import getpass
import os
import sys

BACKEND_DIZINI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend")
sys.path.insert(0, BACKEND_DIZINI)
from app import config, veritabani  # noqa: E402


def db_yolu():
    """Backend backend/ dizininden çalıştığı için göreli yol oraya göre çözülür."""
    yol = config.VERITABANI_YOLU
    return os.path.normpath(yol if os.path.isabs(yol) else os.path.join(BACKEND_DIZINI, yol))


def parola_sor():
    while True:
        parola = getpass.getpass("Yeni parola (en az 8 karakter, ekranda görünmez): ")
        try:
            veritabani.parola_kontrol(parola)
        except veritabani.KullaniciHatasi as e:
            print(f"  ✗ {e}")
            continue
        if getpass.getpass("Yeni parola (tekrar): ") != parola:
            print("  ✗ Parolalar eşleşmedi, tekrar deneyin.")
            continue
        return parola


def main():
    sys.stdout.reconfigure(errors="replace")  # ✓/✗ cp1254 konsolda çökmesin
    config.VERITABANI_YOLU = db_yolu()
    veritabani.kur()
    kullanicilar = veritabani.kullanicilari_listele()
    print(f"Veritabanı: {config.VERITABANI_YOLU}")
    if not kullanicilar:
        print("Henüz kullanıcı yok: önce python scripts/kullanici_ekle.py")
        return 1
    print("Kullanıcılar:")
    for k in kullanicilar:
        print(f"  - {k['kullanici_adi']} ({k['rol']}{'' if k['aktif'] else ', pasif'})")

    try:
        while True:
            ad = (sys.argv[1] if len(sys.argv) > 1 else input("Kullanıcı adı: ")).strip().lower()
            if veritabani.kullanici_getir(ad):
                break
            print(f"  ✗ '{ad}' bulunamadı.")
            if len(sys.argv) > 1:
                return 1
        parola = parola_sor()
    except (KeyboardInterrupt, EOFError):
        print("\nİptal edildi, parola değişmedi.")
        return 1

    sonuc, k = veritabani.kullanici_guncelle(ad, yeni_parola=parola)
    if sonuc != "tamam":
        print(f"✗ Güncellenemedi ({sonuc}).")
        return 1
    print(f"✓ '{k['kullanici_adi']}' ({k['rol']}) parolası güncellendi. "
          "Panelde yeni parolayla giriş yapabilirsiniz.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
