"""
Yapılandırma modülü.
Tüm ayarlar tek yerde toplanır. Gizli değerler (.env) ortam değişkeninden,
sabit değerler doğrudan buradan okunur.
"""
import os
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
# MQ-2 duman/gaz analog eşiği (0-4095). Bu değeri aşınca "yüksek" alarm.
ESIK_DUMAN = int(os.getenv("ESIK_DUMAN", "1800"))
# Bir düğümden kaç saniye haber gelmezse "çevrimdışı" sayılsın.
CEVRIMDISI_SANIYE = int(os.getenv("CEVRIMDISI_SANIYE", "30"))

# ---------------- Veritabanı ----------------
# SQLite dosyasının yolu (backend klasöründe kampus.db)
VERITABANI_YOLU = os.getenv("VERITABANI_YOLU", "kampus.db")

# ---------------- E-posta (SMTP) ----------------
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_KULLANICI = os.getenv("SMTP_KULLANICI", "")
SMTP_PAROLA = os.getenv("SMTP_PAROLA", "")
ALARM_ALICI = os.getenv("ALARM_ALICI", "")
# E-posta gönderimi ayarlar boşsa otomatik devre dışı kalır.
EPOSTA_AKTIF = bool(SMTP_KULLANICI and SMTP_PAROLA and ALARM_ALICI)
