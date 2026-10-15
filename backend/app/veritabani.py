"""
Veritabanı modülü (SQLite).
Sözleşmedeki tabloları yönetir: olaylar, olay_adimlari ve sensor_gecmis.
"""
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
]

_AKIS_YER = ",".join("?" * len(AKIS_SEVIYELERI))  # SQL IN (...) yer tutucuları


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


def olay_ekle(dugum, sensor, deger, seviye, mesaj, zaman=None):
    """olaylar tablosuna bir kayıt ekler ve eklenen kaydı (dict) döndürür."""
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
            "durum, onaylayan, goruldu_zaman, mudahale_zaman, cozuldu_zaman) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (dugum, sensor, deger, seviye, mesaj, zaman,
             durum, onaylayan, kapanis, kapanis, kapanis),
        )
        yeni_id = cur.lastrowid
    return {
        "id": yeni_id, "dugum": dugum, "sensor": sensor, "deger": deger,
        "seviye": seviye, "mesaj": mesaj, "zaman": zaman,
        "durum": durum, "onaylayan": onaylayan, "goruldu_zaman": kapanis,
        "mudahale_zaman": kapanis, "cozuldu_zaman": kapanis, "not_metni": None,
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
    olay = dict(satir)
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
    return [dict(s) for s in satirlar]


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
