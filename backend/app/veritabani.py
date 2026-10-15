"""
Veritabanı modülü (SQLite).
Sözleşmedeki tabloları yönetir: olaylar, olay_adimlari, sensor_gecmis, ayarlar,
kullanicilar ve giris_kayitlari.
"""
import hashlib
import hmac
import json
import re
import secrets
import sqlite3
import time
from contextlib import contextmanager
from app import config

# Olay yaşam döngüsü (docs/SOZLESMELER.md §5, §6): yalnızca ileri gidilir
DURUMLAR = ["yeni", "goruldu", "mudahale", "cozuldu"]
# Bu seviyeler operatör akışına girer; diğerleri oluşurken otomatik çözülür
AKIS_SEVIYELERI = ("orta", "yuksek", "kritik")
ZAMAN_KOLONU = {"goruldu": "goruldu_zaman", "mudahale": "mudahale_zaman",
                "cozuldu": "cozuldu_zaman"}
GOC_ONAYLAYAN = "sistem (göç)"

# Eski veritabanlarında olaylar tablosuna eklenecek kolonlar
_YENI_KOLONLAR = [
    ("durum", "TEXT DEFAULT 'yeni'"),
    ("onaylayan", "TEXT"),
    ("goruldu_zaman", "REAL"),
    ("mudahale_zaman", "REAL"),
    ("cozuldu_zaman", "REAL"),
    ("not_metni", "TEXT"),
    ("kural", "TEXT"),      # olayı üreten kural: histerezis, gece_modu, korelasyon...
    ("iliskili", "TEXT"),   # bileşik olayın tetikleyen olay id'leri, JSON liste "[412, 413]"
]

_AKIS_YER = ",".join("?" * len(AKIS_SEVIYELERI))  # SQL IN (...) yer tutucuları

# Kullanıcılar (docs/SOZLESMELER.md §9)
ROLLER = ("admin", "operator")
KULLANICI_ADI_DESEN = re.compile(r"^[a-z0-9._-]{3,32}$")
PAROLA_EN_AZ = 8
PAROLA_EN_COK = 128  # scrypt pahalı: çok uzun parolayla hizmet engelleme olmasın
AD_SOYAD_EN_COK = 60
# scrypt parametreleri (n=2^14, r=8, p=1 → ~16 MB bellek, ~50 ms)
_SCRYPT = {"n": 2 ** 14, "r": 8, "p": 1, "dklen": 32}
# API'ye dönen kullanıcı alanları (parola_hash ve tuz asla dönmez)
_KULLANICI_ALANLARI = "id, kullanici_adi, ad_soyad, rol, aktif, olusturma, son_giris"


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
    """Tablolar yoksa oluşturur, eski şemayı kayıpsız göç ettirir. Açılışta bir kez çağrılır."""
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
        # Her durum geçişi bir satır: zaman çizelgesindeki kim + not + saat
        conn.execute("""
            CREATE TABLE IF NOT EXISTS olay_adimlari (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                olay_id INTEGER NOT NULL,
                durum TEXT NOT NULL,
                kim TEXT,
                not_metni TEXT,
                zaman REAL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS ix_adimlar_olay ON olay_adimlari (olay_id, id)")
        _olaylar_gocu(conn)
        # Kalıcı ayarlar (ör. guvenlik_modu); yeni tablo, mevcut veriye dokunmaz
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ayarlar (
                anahtar TEXT PRIMARY KEY,
                deger TEXT
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
        # /api/dugumler her düğüm+sensörün en son satırını arar
        conn.execute("""
            CREATE INDEX IF NOT EXISTS ix_gecmis_dugum_sensor
            ON sensor_gecmis (dugum, sensor, id)
        """)
        # Panel kullanıcıları; yeni tablolar, mevcut veriye dokunmaz
        conn.execute("""
            CREATE TABLE IF NOT EXISTS kullanicilar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kullanici_adi TEXT NOT NULL UNIQUE,
                ad_soyad TEXT,
                rol TEXT NOT NULL CHECK (rol IN ('admin', 'operator')),
                parola_hash TEXT NOT NULL,
                tuz TEXT NOT NULL,
                aktif INTEGER NOT NULL DEFAULT 1,
                olusturma REAL,
                son_giris REAL
            )
        """)
        # Giriş denetim kaydı (başarılı + başarısız)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS giris_kayitlari (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                zaman REAL NOT NULL,
                kullanici_adi TEXT,
                ip TEXT,
                basarili INTEGER NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS ix_giris_zaman ON giris_kayitlari (zaman)")


def _olaylar_gocu(conn):
    """
    Kayıpsız göç: olaylar tablosunda eksik durum kolonlarını ALTER TABLE ile ekler.
    durum kolonu bu çalıştırmada eklendiyse mevcut kayıtlar bir kez kapatılır:
    bilgi/uyari → cozuldu (sistem); orta+ → cozuldu (sistem (göç)) ve zaman
    çizelgesi boş kalmasın diye olay_adimlari'na tek bir 'cozuldu' adımı.
    İdempotent: kolonlar zaten varsa hiçbir şey yapmaz.
    """
    var_olan = {s["name"] for s in conn.execute("PRAGMA table_info(olaylar)")}
    eksik = [(ad, tip) for ad, tip in _YENI_KOLONLAR if ad not in var_olan]
    for ad, tip in eksik:
        conn.execute(f"ALTER TABLE olaylar ADD COLUMN {ad} {tip}")
    conn.execute("CREATE INDEX IF NOT EXISTS ix_olaylar_durum ON olaylar (durum, id)")
    if "durum" in var_olan:
        return

    simdi = time.time()
    orta_idler = [s[0] for s in conn.execute(
        f"SELECT id FROM olaylar WHERE seviye IN ({_AKIS_YER})", AKIS_SEVIYELERI)]
    conn.execute(
        "UPDATE olaylar SET durum = 'cozuldu', goruldu_zaman = ?, mudahale_zaman = ?, "
        f"cozuldu_zaman = ?, onaylayan = CASE WHEN seviye IN ({_AKIS_YER}) "
        "THEN ? ELSE 'sistem' END",
        (simdi, simdi, simdi, *AKIS_SEVIYELERI, GOC_ONAYLAYAN),
    )
    conn.executemany(
        "INSERT INTO olay_adimlari (olay_id, durum, kim, not_metni, zaman) "
        "VALUES (?, 'cozuldu', ?, ?, ?)",
        [(i, GOC_ONAYLAYAN, "Durum takibinden önceki kayıt, göçte kapatıldı", simdi)
         for i in orta_idler],
    )
    print(f"[DB] Göç: olaylar tablosuna {len(eksik)} kolon eklendi, "
          f"{len(orta_idler)} orta+ kayıt çözüldü olarak işaretlendi.")


def _olay_dict(satir):
    """DB satırı -> API sözlüğü. iliskili DB'de JSON metin, API'de liste."""
    olay = dict(satir)
    metin = olay.get("iliskili")
    try:
        olay["iliskili"] = json.loads(metin) if metin else None
    except ValueError:
        olay["iliskili"] = None
    return olay


def olay_ekle(dugum, sensor, deger, seviye, mesaj, zaman=None, kural=None, iliskili=None):
    """
    olaylar tablosuna bir kayıt ekler ve eklenen kaydı (dict) döndürür.
    kural: olayı üreten kural etiketi; iliskili: tetikleyen olay id'leri (liste).
    """
    if not zaman:
        zaman = int(time.time())
    # bilgi/uyari operatör akışına girmez: oluşurken çözülmüş sayılır
    if seviye in AKIS_SEVIYELERI:
        durum, onaylayan, kapanis = "yeni", None, None
    else:
        durum, onaylayan, kapanis = "cozuldu", "sistem", time.time()
    with baglanti() as conn:
        cur = conn.execute(
            "INSERT INTO olaylar (dugum, sensor, deger, seviye, mesaj, zaman, "
            "durum, onaylayan, goruldu_zaman, mudahale_zaman, cozuldu_zaman, kural, iliskili) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (dugum, sensor, deger, seviye, mesaj, zaman,
             durum, onaylayan, kapanis, kapanis, kapanis,
             kural, json.dumps(iliskili) if iliskili else None),
        )
        yeni_id = cur.lastrowid
    return {
        "id": yeni_id, "dugum": dugum, "sensor": sensor, "deger": deger,
        "seviye": seviye, "mesaj": mesaj, "zaman": zaman,
        "durum": durum, "onaylayan": onaylayan, "goruldu_zaman": kapanis,
        "mudahale_zaman": kapanis, "cozuldu_zaman": kapanis, "not_metni": None,
        "kural": kural, "iliskili": list(iliskili) if iliskili else None,
    }


def olay_getir(olay_id):
    """Tek olay ve durum adımları (eski → yeni); yoksa None."""
    with baglanti() as conn:
        satir = conn.execute("SELECT * FROM olaylar WHERE id = ?", (olay_id,)).fetchone()
        if satir is None:
            return None
        adimlar = conn.execute(
            "SELECT durum, kim, not_metni, zaman FROM olay_adimlari "
            "WHERE olay_id = ? ORDER BY id", (olay_id,)
        ).fetchall()
    olay = _olay_dict(satir)
    olay["adimlar"] = [dict(a) for a in adimlar]
    return olay


def olay_durum_guncelle(olay_id, durum, onaylayan, not_=None, simdi=None):
    """
    Olayı `durum`a ilerletir. Dönen değer (sonuç, veri):
      ("yok", None)       olay bulunamadı
      ("geri", mevcut)    hedef mevcut durumdan ileri değil (aynı durum dahil)
      ("tamam", olay)     güncellendi; olay adımlarıyla birlikte
    Atlanan ara adımların zamanı da aynı anla doldurulur. UPDATE mevcut duruma
    koşullu olduğundan aynı anda iki istek gelirse yalnızca biri kazanır.
    """
    if simdi is None:
        simdi = time.time()
    hedef = DURUMLAR.index(durum)
    with baglanti() as conn:
        satir = conn.execute("SELECT durum FROM olaylar WHERE id = ?", (olay_id,)).fetchone()
        if satir is None:
            return "yok", None
        mevcut = satir["durum"] or "yeni"
        if hedef <= DURUMLAR.index(mevcut):
            return "geri", mevcut
        kolonlar = [ZAMAN_KOLONU[d] for d in DURUMLAR[DURUMLAR.index(mevcut) + 1:hedef + 1]]
        atamalar = ", ".join(f"{k} = COALESCE({k}, ?)" for k in kolonlar)
        cur = conn.execute(
            f"UPDATE olaylar SET durum = ?, onaylayan = ?, not_metni = ?, {atamalar} "
            "WHERE id = ? AND COALESCE(durum, 'yeni') = ?",
            (durum, onaylayan, not_, *[simdi] * len(kolonlar), olay_id, mevcut),
        )
        if cur.rowcount == 0:  # arada başka bir istek ilerletti
            yeni = conn.execute("SELECT durum FROM olaylar WHERE id = ?", (olay_id,)).fetchone()
            return "geri", yeni["durum"] if yeni else mevcut
        conn.execute(
            "INSERT INTO olay_adimlari (olay_id, durum, kim, not_metni, zaman) "
            "VALUES (?, ?, ?, ?, ?)",
            (olay_id, durum, onaylayan, not_, simdi),
        )
    return "tamam", olay_getir(olay_id)


def mudahale_istatistigi(simdi=None):
    """
    acik_sayisi: zamandan bağımsız tüm çözülmemiş orta+ olaylar.
    Ortalamalar ve cozulen_sayisi: son 24 saatte oluşan orta+ olaylar.
    Süre = sunucu saatiyle *_zaman − cihaz saatiyle zaman. Negatif süre
    (cihaz saati ileride) ortalamaya katılmaz; göçte kapatılan kayıtlar da.
    """
    if simdi is None:
        simdi = time.time()
    with baglanti() as conn:
        acik = conn.execute(
            f"SELECT COUNT(*) FROM olaylar WHERE seviye IN ({_AKIS_YER}) "
            "AND COALESCE(durum, 'yeni') != 'cozuldu'", AKIS_SEVIYELERI
        ).fetchone()[0]
        s = conn.execute(
            "SELECT "
            "  AVG(CASE WHEN goruldu_zaman - zaman >= 0 THEN goruldu_zaman - zaman END), "
            "  AVG(CASE WHEN cozuldu_zaman - zaman >= 0 THEN cozuldu_zaman - zaman END), "
            "  SUM(CASE WHEN durum = 'cozuldu' THEN 1 ELSE 0 END) "
            f"FROM olaylar WHERE seviye IN ({_AKIS_YER}) AND zaman >= ? "
            "AND COALESCE(onaylayan, '') != ?",
            (*AKIS_SEVIYELERI, simdi - 86400, GOC_ONAYLAYAN),
        ).fetchone()

    def yuvarla(v):
        return None if v is None else round(v, 1)

    return {
        "acik_sayisi": acik,
        "ort_gorulme_sn": yuvarla(s[0]),
        "ort_cozum_sn": yuvarla(s[1]),
        "cozulen_sayisi": s[2] or 0,
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


def son_olaylar(limit=50, sadece_acik=False):
    """En son olayları döndürür (yeni -> eski). sadece_acik: durum != cozuldu."""
    kosul = "WHERE COALESCE(durum, 'yeni') != 'cozuldu' " if sadece_acik else ""
    with baglanti() as conn:
        satirlar = conn.execute(
            f"SELECT * FROM olaylar {kosul}ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [_olay_dict(s) for s in satirlar]


def sensor_gecmis_getir(sensor, dugum="dugum1", limit=50):
    """Belirli bir sensörün son ham okumalarını döndürür (eski -> yeni)."""
    with baglanti() as conn:
        satirlar = conn.execute(
            "SELECT * FROM sensor_gecmis WHERE sensor = ? AND dugum = ? "
            "ORDER BY id DESC LIMIT ?",
            (sensor, dugum, limit),
        ).fetchall()
    # En son 'limit' kaydı aldık; grafik için eski->yeni sırala
    return [dict(s) for s in reversed(satirlar)]


def son_okumalar():
    """Her (düğüm, sensör) çiftinin en son ham okumasını döndürür."""
    with baglanti() as conn:
        satirlar = conn.execute(
            "SELECT g.* FROM sensor_gecmis g JOIN ("
            "  SELECT MAX(id) AS id FROM sensor_gecmis GROUP BY dugum, sensor"
            ") s ON g.id = s.id"
        ).fetchall()
    return [dict(s) for s in satirlar]


def ayar_getir(anahtar, varsayilan=None):
    """ayarlar tablosundan bir değer; yoksa varsayilan."""
    with baglanti() as conn:
        satir = conn.execute("SELECT deger FROM ayarlar WHERE anahtar = ?", (anahtar,)).fetchone()
    return satir["deger"] if satir else varsayilan


def ayar_yaz(anahtar, deger):
    """Ayarı ekler ya da günceller."""
    with baglanti() as conn:
        conn.execute(
            "INSERT INTO ayarlar (anahtar, deger) VALUES (?, ?) "
            "ON CONFLICT(anahtar) DO UPDATE SET deger = excluded.deger",
            (anahtar, deger),
        )


# ---------------- Kullanıcılar ve giriş kayıtları ----------------

class KullaniciHatasi(ValueError):
    """Geçersiz kullanıcı adı / parola / rol; mesaj kullanıcıya gösterilebilir."""


class KullaniciVar(Exception):
    """Aynı kullanıcı adı zaten kayıtlı."""


def kullanici_adi_duzelt(ad):
    """Boşluklar atılır, küçük harfe çevrilir; desene uymazsa KullaniciHatasi."""
    ad = (ad or "").strip().lower()
    if not KULLANICI_ADI_DESEN.match(ad):
        raise KullaniciHatasi("Kullanıcı adı 3-32 karakter olmalı: küçük harf, rakam, . _ -")
    return ad


def parola_kontrol(parola):
    if not isinstance(parola, str) or not PAROLA_EN_AZ <= len(parola) <= PAROLA_EN_COK:
        raise KullaniciHatasi(f"Parola {PAROLA_EN_AZ}-{PAROLA_EN_COK} karakter olmalı")
    return parola


def _ad_soyad_duzelt(ad_soyad):
    ad_soyad = (ad_soyad or "").strip()
    if len(ad_soyad) > AD_SOYAD_EN_COK:
        raise KullaniciHatasi(f"Ad soyad en fazla {AD_SOYAD_EN_COK} karakter olmalı")
    return ad_soyad or None


def _rol_kontrol(rol):
    if rol not in ROLLER:
        raise KullaniciHatasi("Rol admin ya da operator olmalı")
    return rol


def parola_ozeti(parola, tuz=None):
    """scrypt ile (ozet_hex, tuz_hex). Tuz verilmezse kullanıcıya özel 16 bayt üretilir."""
    tuz_b = bytes.fromhex(tuz) if tuz else secrets.token_bytes(16)
    ozet = hashlib.scrypt(parola.encode("utf-8"), salt=tuz_b, **_SCRYPT)
    return ozet.hex(), tuz_b.hex()


def parola_dogru(parola, ozet_hex, tuz_hex):
    """Sabit zamanlı karşılaştırma (hmac.compare_digest)."""
    hesap, _ = parola_ozeti(parola, tuz_hex)
    return hmac.compare_digest(hesap, ozet_hex)


def kullanici_ekle(kullanici_adi, ad_soyad, rol, parola):
    """Yeni kullanıcı; dönen sözlükte hash/tuz yok. KullaniciHatasi / KullaniciVar atar."""
    kullanici_adi = kullanici_adi_duzelt(kullanici_adi)
    ad_soyad = _ad_soyad_duzelt(ad_soyad)
    _rol_kontrol(rol)
    ozet, tuz = parola_ozeti(parola_kontrol(parola))
    try:
        with baglanti() as conn:
            conn.execute(
                "INSERT INTO kullanicilar (kullanici_adi, ad_soyad, rol, parola_hash, tuz, "
                "aktif, olusturma) VALUES (?, ?, ?, ?, ?, 1, ?)",
                (kullanici_adi, ad_soyad, rol, ozet, tuz, time.time()),
            )
    except sqlite3.IntegrityError:
        raise KullaniciVar(kullanici_adi) from None
    return kullanici_getir(kullanici_adi)


def kullanici_getir(kullanici_adi, hassas=False):
    """Kullanıcı sözlüğü ya da None. hassas=True yalnızca parola doğrulaması için."""
    alanlar = "*" if hassas else _KULLANICI_ALANLARI
    with baglanti() as conn:
        satir = conn.execute(f"SELECT {alanlar} FROM kullanicilar WHERE kullanici_adi = ?",
                             ((kullanici_adi or "").strip().lower(),)).fetchone()
    return dict(satir) if satir else None


def kullanicilari_listele():
    with baglanti() as conn:
        satirlar = conn.execute(
            f"SELECT {_KULLANICI_ALANLARI} FROM kullanicilar ORDER BY kullanici_adi").fetchall()
    return [dict(s) for s in satirlar]


def kullanici_sayisi():
    with baglanti() as conn:
        return conn.execute("SELECT COUNT(*) FROM kullanicilar").fetchone()[0]


def kullanici_guncelle(kullanici_adi, rol=None, ad_soyad=None, aktif=None, yeni_parola=None):
    """
    Verilen alanları günceller. Dönen değer (sonuç, veri):
      ("yok", None)        kullanıcı bulunamadı
      ("son_admin", None)  son aktif admin pasif yapılamaz / operatöre düşürülemez
      ("tamam", kullanici) güncellendi (hash/tuz yok)
    Son admin kontrolü ve güncelleme aynı yazma işleminde yapılır.
    """
    atamalar, degerler = [], []
    if rol is not None:
        atamalar.append("rol = ?")
        degerler.append(_rol_kontrol(rol))
    if ad_soyad is not None:
        atamalar.append("ad_soyad = ?")
        degerler.append(_ad_soyad_duzelt(ad_soyad))
    if aktif is not None:
        atamalar.append("aktif = ?")
        degerler.append(1 if aktif else 0)
    if yeni_parola is not None:
        ozet, tuz = parola_ozeti(parola_kontrol(yeni_parola))
        atamalar += ["parola_hash = ?", "tuz = ?"]
        degerler += [ozet, tuz]
    kullanici_adi = (kullanici_adi or "").strip().lower()

    with baglanti() as conn:
        conn.execute("BEGIN IMMEDIATE")
        satir = conn.execute("SELECT rol, aktif FROM kullanicilar WHERE kullanici_adi = ?",
                             (kullanici_adi,)).fetchone()
        if satir is None:
            return "yok", None
        admin_kalmiyor = (satir["rol"] == "admin" and satir["aktif"]
                          and (rol == "operator" or aktif is False))
        if admin_kalmiyor and conn.execute(
                "SELECT COUNT(*) FROM kullanicilar WHERE rol = 'admin' AND aktif = 1"
        ).fetchone()[0] <= 1:
            return "son_admin", None
        if atamalar:
            conn.execute(f"UPDATE kullanicilar SET {', '.join(atamalar)} WHERE kullanici_adi = ?",
                         (*degerler, kullanici_adi))
    return "tamam", kullanici_getir(kullanici_adi)


def kullanici_sil(kullanici_adi):
    """Kullanıcıyı ve giriş kayıtlarını siler (yalnızca scriptler; API'de silme yok)."""
    kullanici_adi = (kullanici_adi or "").strip().lower()
    with baglanti() as conn:
        k = conn.execute("DELETE FROM kullanicilar WHERE kullanici_adi = ?",
                         (kullanici_adi,)).rowcount
        g = conn.execute("DELETE FROM giris_kayitlari WHERE kullanici_adi = ?",
                         (kullanici_adi,)).rowcount
    return k, g


def son_giris_yaz(kullanici_adi, zaman=None):
    with baglanti() as conn:
        conn.execute("UPDATE kullanicilar SET son_giris = ? WHERE kullanici_adi = ?",
                     (zaman or time.time(), kullanici_adi))


def giris_kaydet(kullanici_adi, ip, basarili):
    """Denetim kaydı. Kullanıcı adı denemede yazılan biçimiyle (kısaltılmış) saklanır."""
    with baglanti() as conn:
        conn.execute(
            "INSERT INTO giris_kayitlari (zaman, kullanici_adi, ip, basarili) VALUES (?, ?, ?, ?)",
            (time.time(), (kullanici_adi or "").strip().lower()[:64], ip, 1 if basarili else 0),
        )
