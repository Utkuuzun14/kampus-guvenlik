"""
Panel kullanıcısı ekleme (ilk admin dahil). Etkileşimlidir: kullanıcı adı,
ad soyad, rol ve iki kez parola sorar; parola ekranda görünmez (getpass).
Koda gömülü kullanıcı ya da parola yoktur. Kurallar backend'le aynıdır
(app/veritabani.py): kullanıcı adı 3-32 karakter [a-z0-9._-], parola 8-128 karakter.

Backend açıkken de çalıştırılabilir. Daha sonraki kullanıcılar panelden
(admin → Kullanıcılar) de eklenebilir.

Çalıştırma (backend venv aktifken, proje kökünden):
    python scripts/kullanici_ekle.py
"""
import getpass
import os
import sys

BACKEND_DIZINI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend")
sys.path.insert(0, BACKEND_DIZINI)
from app import config, veritabani  # noqa: E402

ROLLER = {"1": "admin", "2": "operator"}


def db_yolu():
    """Backend backend/ dizininden çalıştığı için göreli yol oraya göre çözülür."""
    yol = config.VERITABANI_YOLU
    return os.path.normpath(yol if os.path.isabs(yol) else os.path.join(BACKEND_DIZINI, yol))


def sor(soru, dogrula):
    """Geçerli bir cevap gelene kadar sorar; dogrula hata mesajlı KullaniciHatasi atar."""
    while True:
        try:
            return dogrula(input(soru))
        except veritabani.KullaniciHatasi as e:
            print(f"  ✗ {e}")


def parola_sor():
    while True:
        parola = getpass.getpass("Parola (en az 8 karakter, ekranda görünmez): ")
        try:
            veritabani.parola_kontrol(parola)
        except veritabani.KullaniciHatasi as e:
            print(f"  ✗ {e}")
            continue
        if getpass.getpass("Parola (tekrar): ") != parola:
            print("  ✗ Parolalar eşleşmedi, tekrar deneyin.")
            continue
        return parola


def kullanici_adi_dogrula(ad):
    ad = veritabani.kullanici_adi_duzelt(ad)
    if veritabani.kullanici_getir(ad):
        raise veritabani.KullaniciHatasi(f"'{ad}' zaten kayıtlı")
    return ad


def main():
    config.VERITABANI_YOLU = db_yolu()
    veritabani.kur()  # backend hiç açılmamışsa tablolar oluşsun
    ilk = veritabani.kullanici_sayisi() == 0
    print(f"Veritabanı: {config.VERITABANI_YOLU}")
    if ilk:
        print("Henüz kullanıcı yok: ilk kullanıcı varsayılan olarak admin olur.")

    try:
        ad = sor("Kullanıcı adı (küçük harf, rakam, . _ -): ", kullanici_adi_dogrula)
        ad_soyad = input("Ad soyad (zaman çizelgesinde görünür, boş bırakılabilir): ").strip()
        varsayilan = "1" if ilk else "2"

        def rol_dogrula(secim):
            rol = ROLLER.get(secim.strip() or varsayilan)
            if not rol:
                raise veritabani.KullaniciHatasi("1 ya da 2 girin")
            return rol

        rol = sor(f"Rol [1 admin / 2 operatör] (varsayılan {varsayilan}): ", rol_dogrula)
        parola = parola_sor()
    except (KeyboardInterrupt, EOFError):
        print("\nİptal edildi, kullanıcı eklenmedi.")
        return 1

    try:
        k = veritabani.kullanici_ekle(ad, ad_soyad, rol, parola)
    except veritabani.KullaniciHatasi as e:
        print(f"✗ {e}")
        return 1
    except veritabani.KullaniciVar:
        print(f"✗ '{ad}' zaten kayıtlı.")
        return 1
    print(f"✓ Eklendi: {k['kullanici_adi']} ({k['ad_soyad'] or '-'}, {k['rol']}). "
          "Panelde bu kullanıcıyla giriş yapabilirsiniz.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
