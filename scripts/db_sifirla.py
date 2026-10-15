"""
Veritabanı sıfırlama aracı (sunum öncesi temiz başlangıç).

1. backend/kampus.db'nin yedeğini alır: backend/yedekler/kampus_YYYYMMDD_HHMM.db
   (SQLite yedekleme API'si; backend açıkken de tutarlı bir kopya üretir)
2. Tablo başına kayıt sayılarını gösterir, "EVET" yazılmasını ister
3. olaylar, olay_adimlari, sensor_gecmis ve giris_kayitlari tablolarını boşaltır, id
   sayaçlarını sıfırlar, VACUUM yapar. Tablo yapısına (sütunlar, indeksler) dokunmaz.
   kullanicilar ve ayarlar tabloları KORUNUR (hesaplar ve güvenlik modu silinmez).

Backend açıkken de çalıştırılabilir: veritabanı o an kilitliyse birkaç kez
bekleyip tekrar dener, olmazsa anlaşılır bir hata verir. Backend'in bellekteki
histerezis durumu (kurallar.py) sıfırlanmaz; temiz bir başlangıç için backend'i
yeniden başlatmak en iyisidir.

Çalıştırma (backend venv aktifken, proje kökünden):
    python scripts/db_sifirla.py          # onay sorar
    python scripts/db_sifirla.py --evet   # sorusuz
"""
import argparse
import os
import sqlite3
import sys
import time
from datetime import datetime

BACKEND_DIZINI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend")
sys.path.insert(0, BACKEND_DIZINI)
from app import config  # noqa: E402

# olay_adimlari / giris_kayitlari eski veritabanında henüz olmayabilir (backend açılışta oluşturur)
TABLOLAR = ("olaylar", "olay_adimlari", "sensor_gecmis", "giris_kayitlari")
KORUNAN = "kullanicilar"  # hiçbir zaman silinmez
DENEME = 5          # kilitliyse kaç kez denensin
BEKLEME_SN = 2      # denemeler arası bekleme
KILIT_SURESI = 5    # her bağlantının kilidi bekleme süresi (sqlite3 timeout)


class Kilitli(Exception):
    pass


def db_yolu():
    """Backend backend/ dizininden çalıştığı için göreli yol oraya göre çözülür."""
    yol = config.VERITABANI_YOLU
    return os.path.normpath(yol if os.path.isabs(yol) else os.path.join(BACKEND_DIZINI, yol))


def baglan(yol):
    # isolation_level=None: işlemleri (BEGIN/COMMIT) kendimiz yönetiriz; VACUUM işlem dışında çalışmalı
    return sqlite3.connect(yol, timeout=KILIT_SURESI, isolation_level=None)


def tekrar_dene(ad, islem):
    """'database is locked' hatasında bekleyip tekrar dener."""
    for deneme in range(1, DENEME + 1):
        try:
            return islem()
        except sqlite3.OperationalError as e:
            if "locked" not in str(e) and "busy" not in str(e):
                raise
            if deneme == DENEME:
                raise Kilitli(ad) from e
            print(f"  Veritabanı kilitli ({ad}), {BEKLEME_SN} sn sonra tekrar denenecek "
                  f"({deneme}/{DENEME - 1})...")
            time.sleep(BEKLEME_SN)


def mevcut_tablolar(conn):
    return [t for t in TABLOLAR
            if conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
                            (t,)).fetchone()]


def sayilar(conn):
    return {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            for t in mevcut_tablolar(conn)}


def korunan_sayisi(conn):
    """kullanicilar tablosundaki kayıt sayısı (tablo yoksa 0)."""
    if not conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
                        (KORUNAN,)).fetchone():
        return 0
    return conn.execute(f"SELECT COUNT(*) FROM {KORUNAN}").fetchone()[0]


def yedek_al(yol):
    klasor = os.path.join(BACKEND_DIZINI, "yedekler")
    os.makedirs(klasor, exist_ok=True)
    hedef = os.path.normpath(os.path.join(klasor, f"kampus_{datetime.now():%Y%m%d_%H%M}.db"))
    if os.path.exists(hedef):  # aynı dakika içinde ikinci çalıştırma
        hedef = hedef[:-3] + f"{datetime.now():%S}.db"

    def kopyala():
        kaynak, yedek = baglan(yol), sqlite3.connect(hedef)
        try:
            kaynak.backup(yedek)
        finally:
            yedek.close()
            kaynak.close()

    tekrar_dene("yedekleme", kopyala)
    return hedef


def bosalt(yol):
    def sil():
        conn = baglan(yol)
        try:
            conn.execute("BEGIN IMMEDIATE")  # yazma kilidini baştan al
            tablolar = mevcut_tablolar(conn)
            for t in tablolar:
                conn.execute(f"DELETE FROM {t}")
            # AUTOINCREMENT sayaçları: yeni kayıtlar 1'den başlasın
            conn.execute(f"DELETE FROM sqlite_sequence WHERE name IN ({','.join('?' * len(tablolar))})",
                         tablolar)
            conn.execute("COMMIT")
        except Exception:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        finally:
            conn.close()

    def vacuum():
        conn = baglan(yol)
        try:
            conn.execute("VACUUM")
        finally:
            conn.close()

    tekrar_dene("silme", sil)
    tekrar_dene("VACUUM", vacuum)


def main():
    ap = argparse.ArgumentParser(description="olaylar, olay_adimlari, sensor_gecmis ve giris_kayitlari "
                                             "tablolarını yedekleyip boşaltır (kullanicilar korunur)")
    ap.add_argument("--evet", action="store_true", help="onay sormadan çalış")
    arg = ap.parse_args()

    yol = db_yolu()
    if not os.path.exists(yol):
        print(f"Veritabanı bulunamadı: {yol}")
        return 1

    try:
        conn = baglan(yol)
        try:
            once = tekrar_dene("sayım", lambda: sayilar(conn))
            korunan = tekrar_dene("sayım", lambda: korunan_sayisi(conn))
        finally:
            conn.close()
        boyut = os.path.getsize(yol)
        print(f"Veritabanı: {yol} ({boyut / 1024 / 1024:.1f} MB)")
        for t, n in once.items():
            print(f"  {t:15} {n:>8} kayıt")
        print(f"{KORUNAN} tablosu KORUNUR ({korunan} kullanıcı) — silinmez.")

        yedek = yedek_al(yol)
        print(f"Yedek alındı: {yedek} ({os.path.getsize(yedek) / 1024 / 1024:.1f} MB)")

        if not arg.evet:
            cevap = input("Yukarıdaki tabloların tüm kayıtları silinecek (tablo yapısı ve kullanıcılar "
                          'korunur). Onaylıyorsanız "EVET" yazın: ')
            if cevap.strip() != "EVET":
                print("İptal edildi. Veritabanı değiştirilmedi (yedek duruyor).")
                return 1

        bosalt(yol)
        conn = baglan(yol)
        try:
            sonra = sayilar(conn)
        finally:
            conn.close()
    except Kilitli as e:
        print(f"\n✗ Veritabanı {DENEME} denemede de kilitliydi ({e}). Backend ya da üreteç yoğun yazıyor "
              f"olabilir; birkaç saniye sonra tekrar deneyin ya da önce backend'i durdurun.")
        return 2

    print("✓ Sıfırlandı: " + ", ".join(f"{t} {n}" for t, n in sonra.items())
          + f" kayıt; dosya {os.path.getsize(yol) / 1024 / 1024:.1f} MB")
    print(f"  {KORUNAN}: {korunan} kullanıcı korundu.")
    print("İpucu: backend açıksa yeniden başlatın (bellekteki alarm durumu da sıfırlansın).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
