"""
Veritabanı modülü (SQLite).
Sözleşmedeki iki tabloyu yönetir: olaylar ve sensor_gecmis.
"""
import sqlite3
import time
from contextlib import contextmanager
from app import config


@contextmanager
def baglanti():
    """SQLite bağlantısı açar, iş bitince otomatik kapatır."""
    conn = sqlite3.connect(config.VERITABANI_YOLU)
    conn.row_factory = sqlite3.Row  # sonuçlara sütun adıyla erişim
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def kur():
    """Tablolar yoksa oluşturur. Uygulama açılışında bir kez çağrılır."""
    with baglanti() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS olaylar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dugum TEXT NOT NULL,
                sensor TEXT NOT NULL,
                deger INTEGER,
                seviye TEXT NOT NULL,
                mesaj TEXT,
                zaman INTEGER,
                olusturma DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sensor_gecmis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dugum TEXT NOT NULL,
                sensor TEXT NOT NULL,
                deger INTEGER,
                zaman INTEGER
            )
        """)


def olay_ekle(dugum, sensor, deger, seviye, mesaj, zaman=None):
    """olaylar tablosuna bir kayıt ekler ve eklenen kaydı (dict) döndürür."""
    if not zaman:
        zaman = int(time.time())
    with baglanti() as conn:
        cur = conn.execute(
            "INSERT INTO olaylar (dugum, sensor, deger, seviye, mesaj, zaman) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (dugum, sensor, deger, seviye, mesaj, zaman),
        )
        yeni_id = cur.lastrowid
    return {
        "id": yeni_id, "dugum": dugum, "sensor": sensor, "deger": deger,
        "seviye": seviye, "mesaj": mesaj, "zaman": zaman,
    }


def gecmis_ekle(dugum, sensor, deger, zaman=None):
    """sensor_gecmis tablosuna ham okuma ekler (trend/grafik için)."""
    if not zaman:
        zaman = int(time.time())
    with baglanti() as conn:
        conn.execute(
            "INSERT INTO sensor_gecmis (dugum, sensor, deger, zaman) "
            "VALUES (?, ?, ?, ?)",
            (dugum, sensor, deger, zaman),
        )


def son_olaylar(limit=50):
    """En son olayları döndürür (yeni -> eski)."""
    with baglanti() as conn:
        satirlar = conn.execute(
            "SELECT * FROM olaylar ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(s) for s in satirlar]
