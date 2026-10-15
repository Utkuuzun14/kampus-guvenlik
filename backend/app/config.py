"""
Yapılandırma modülü.
Tüm ayarlar tek yerde toplanır. Gizli değerler (.env) ortam değişkeninden,
sabit değerler doğrudan buradan okunur.
"""
import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dotenv import load_dotenv

# .env dosyasını yükle (backend/.env)
load_dotenv()

# ---------------- MQTT ayarları ----------------
MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_KULLANICI = os.getenv("MQTT_KULLANICI", "kampus")
MQTT_PAROLA = os.getenv("MQTT_PAROLA", "")

# Backend'in abone olacağı konular (sözleşmedeki + jokerli yapı)
MQTT_KONULAR = [
    ("kampus/guvenlik/+/hareket", 1),
    ("kampus/guvenlik/+/duman", 1),
    ("kampus/guvenlik/+/alev", 1),
    ("kampus/guvenlik/+/durum", 1),
]
# Alarm yayınlama kök konusu (backend -> ... /alarm)
MQTT_ALARM_KONU_SABLON = "kampus/guvenlik/{dugum}/alarm"

# ---------------- Eşik / kural ayarları ----------------
# MQ-2 duman/gaz analog eşiği (0-4095). Bu değeri aşınca "yuksek" alarm.
ESIK_DUMAN = int(os.getenv("ESIK_DUMAN", "1800"))
# Histerezis: alarmdaki düğüm bu değerin altına inince "normale döndü" sayılır.
ESIK_DUMAN_NORMAL = int(os.getenv("ESIK_DUMAN_NORMAL", "1600"))
# Bir düğümden kaç saniye haber gelmezse "çevrimdışı" sayılsın.
CEVRIMDISI_SANIYE = int(os.getenv("CEVRIMDISI_SANIYE", "30"))

# ---------------- Akıllı kurallar ----------------
# Yangın teyidi: aynı düğümde duman alarmı ve alev bu kadar saniye içinde
# (sıra fark etmeksizin) gelirse bileşik "yangin_teyit" olayı üretilir.
KORELASYON_PENCERE_SN = int(os.getenv("KORELASYON_PENCERE_SN", "10"))


def _saat_oku(ad, varsayilan):
    """"HH:MM" -> datetime.time; hatalı biçim açılışta hata verir."""
    metin = os.getenv(ad, varsayilan).strip()
    try:
        return datetime.strptime(metin, "%H:%M").time()
    except ValueError:
        raise ValueError(f"{ad} 'HH:MM' biçiminde olmalı, gelen: {metin!r}") from None


# Güvenlik modu "otomatik"ken hareket kuralı sunucu saatine göre seçilir:
# hafta içi mesai saatleri "mesai", gece aralığı (her gün) "gece", kalanı "mesai_disi".
MESAI_BASLANGIC = _saat_oku("MESAI_BASLANGIC", "08:00")
MESAI_BITIS = _saat_oku("MESAI_BITIS", "18:00")
GECE_BASLANGIC = _saat_oku("GECE_BASLANGIC", "23:00")
GECE_BITIS = _saat_oku("GECE_BITIS", "06:00")

# Sunucu saat dilimi. Windows'ta IANA veritabanı (tzdata) yoksa sabit UTC+3
# kullanılır: Türkiye 2016'dan beri yaz saati uygulamıyor, sonuç aynıdır.
try:
    SAAT_DILIMI = ZoneInfo("Europe/Istanbul")
except ZoneInfoNotFoundError:
    SAAT_DILIMI = timezone(timedelta(hours=3), "Europe/Istanbul")
    print("[CONFIG] tzdata yok, Europe/Istanbul için sabit UTC+03:00 kullanılıyor.")

# ---------------- Veritabanı ----------------
# SQLite dosyasının yolu (backend klasöründe kampus.db)
VERITABANI_YOLU = os.getenv("VERITABANI_YOLU", "kampus.db")

# ---------------- E-posta bildirimi (SMTP, SSL 465) ----------------
SMTP_SUNUCU = os.getenv("SMTP_SUNUCU", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_KULLANICI = os.getenv("SMTP_KULLANICI", "").strip()
# Gmail'de normal parola değil, 16 haneli "uygulama şifresi" kullanılır.
# Gmail onu boşluklu gösterir; boşluklar burada atılır.
SMTP_PAROLA = os.getenv("SMTP_PAROLA", "").replace(" ", "")
# Alıcı boşsa mail gönderen adrese (kendine) gider.
BILDIRIM_ALICI = os.getenv("BILDIRIM_ALICI", "").strip() or SMTP_KULLANICI
# Hangi seviyeler mail üretir (virgülle ayrılmış).
BILDIRIM_SEVIYELER = [s.strip() for s in os.getenv("BILDIRIM_SEVIYELER", "kritik,yuksek").split(",")
                      if s.strip()]
# Aynı düğüm + sensör + seviye için iki mail arasındaki en kısa süre (sn).
BILDIRIM_BEKLEME_SN = int(os.getenv("BILDIRIM_BEKLEME_SN", "300"))
# Bu düğümlerin olayları mail üretmez (test_senaryolari.py canlı testleri).
BILDIRIM_HARIC_DUGUMLER = {"test_dugum"}
# Kullanıcı/parola boşsa bildirim sessizce devre dışı kalır.
BILDIRIM_AKTIF = (os.getenv("BILDIRIM_AKTIF", "true").strip().lower() in ("1", "true", "evet")
                  and bool(SMTP_KULLANICI and SMTP_PAROLA))

# Maildeki panel bağlantısı
PANEL_URL = os.getenv("PANEL_URL", "http://localhost:5173")

# Düğüm -> kampüs konum adı. Tek kaynak burası (/api/dugumler); frontend/src/sabitler.js
# yalnızca harita koordinatlarını tutar.
DUGUM_KONUMLARI = {
    "dugum1": "Ana Bina · A Kanadı",
    "dugum2": "Spor Kompleksi",
    "dugum3": "Yurt Binası",
}
