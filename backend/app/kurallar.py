"""
Kural motoru.
Gelen bir sensör mesajını değerlendirir, alarm seviyesini ve
insan-okur mesajı belirler. Sözleşmedeki eşik/alarm kurallarını uygular.

Alarm fırtınasını önlemek için duman ve alev histerezisli çalışır: olay
yalnızca durum DEĞİŞİMİNDE üretilir (normal → alarm, alarm → normal).
Durum düğüm bazında bellekte tutulur; backend yeniden başlarsa tüm düğümler
"normal" kabul edilerek sıfırdan başlanır.

Akıllı kurallar:
- Güvenlik modu (otomatik | mesai | mesai_disi | gece): hareket=1'in seviyesini
  belirler. Mod ayarlar tablosunda kalıcıdır; "otomatik"te SUNUCU saatine göre
  seçilir (cihaz saati kayabilir). Saf fonksiyonlar: etkin_mod, hareket_seviyesi.
- Yangın teyidi (korelasyon): aynı düğümde duman alarma girişi ve alev=1,
  sıra fark etmeksizin KORELASYON_PENCERE_SN içinde gelirse bileşik
  "yangin_teyit" olayı. Saf fonksiyon: korelasyon. Durum bellekte tutulur.
"""
import threading
import time
from datetime import datetime

from app import config, veritabani

# Alarm seviyeleri (düşükten yükseğe)
SEVIYELER = ["bilgi", "uyari", "orta", "yuksek", "kritik"]

# (dugum, sensor) -> alarmda mı (yalnızca duman ve alev için)
_alarm = {}
_kilit = threading.Lock()


def _gecis(dugum, sensor, alarm_kosulu, normal_kosulu):
    """
    Histerezis: alarm_kosulu sağlanınca alarma girer, normal_kosulu
    sağlanana kadar alarmda kalır. Dönüş: "alarm" | "normal" | None (değişim yok)
    """
    anahtar = (dugum, sensor)
    with _kilit:
        alarmda = _alarm.get(anahtar, False)
        if not alarmda and alarm_kosulu:
            _alarm[anahtar] = True
            return "alarm"
        if alarmda and normal_kosulu:
            _alarm[anahtar] = False
            return "normal"
    return None


def alarmda_mi(dugum, sensor):
    with _kilit:
        return _alarm.get((dugum, sensor), False)


# ---------------- Güvenlik modu ----------------

MODLAR = ("otomatik", "mesai", "mesai_disi", "gece")
MOD_ANAHTAR = "guvenlik_modu"  # ayarlar tablosundaki anahtar
VARSAYILAN_MOD = "otomatik"
MOD_AD = {"otomatik": "Otomatik", "mesai": "Mesai", "mesai_disi": "Mesai dışı", "gece": "Gece"}

# etkin mod -> (hareket seviyesi, kural etiketi, mesaj eki)
HAREKET_KURALI = {
    "mesai": ("bilgi", "mesai", "mesai saati"),
    "mesai_disi": ("orta", "mesai_disi", "mesai dışı"),
    "gece": ("yuksek", "gece_modu", "gece modu"),
}


def _aralikta(saat, baslangic, bitis):
    """[baslangic, bitis) aralığında mı; bitis < baslangic ise gece yarısını aşar."""
    if baslangic <= bitis:
        return baslangic <= saat < bitis
    return saat >= baslangic or saat < bitis


def etkin_mod(mod, simdi):
    """
    O an geçerli mod. otomatik dışındakiler olduğu gibi döner. otomatik:
    gece aralığı (her gün) → gece; hafta içi mesai saatleri → mesai; kalanı mesai_disi.
    simdi: sunucu saat dilimindeki datetime.
    """
    if mod != "otomatik":
        return mod
    saat = simdi.time()
    if _aralikta(saat, config.GECE_BASLANGIC, config.GECE_BITIS):
        return "gece"
    if simdi.weekday() < 5 and _aralikta(saat, config.MESAI_BASLANGIC, config.MESAI_BITIS):
        return "mesai"
    return "mesai_disi"


def hareket_seviyesi(mod, simdi):
    """hareket=1 için (seviye, kural, mesaj). Saf: saat parametreyle verilir."""
    seviye, kural, ek = HAREKET_KURALI[etkin_mod(mod, simdi)]
    if mod == "otomatik":
        ek += " (otomatik)"
    return seviye, kural, f"Hareket algılandı · {ek}"


def mod_aciklama(mod, simdi):
    """Panel ve API için kısa açıklama."""
    etkin = etkin_mod(mod, simdi)
    seviye = HAREKET_KURALI[etkin][0]
    if mod != "otomatik":
        return f"{MOD_AD[mod]} modu (elle seçildi) · hareket = {seviye}"
    if etkin == "gece":
        aralik = f" ({config.GECE_BASLANGIC:%H:%M}–{config.GECE_BITIS:%H:%M})"
    elif etkin == "mesai":
        aralik = f" (hafta içi {config.MESAI_BASLANGIC:%H:%M}–{config.MESAI_BITIS:%H:%M})"
    else:
        aralik = ""
    return f"Otomatik · şu an {MOD_AD[etkin].lower()}{aralik} · hareket = {seviye}"


def simdi_yerel():
    """Sunucu saati, Europe/Istanbul."""
    return datetime.now(config.SAAT_DILIMI)


def mod_getir():
    """Kalıcı mod (ayarlar tablosu); boş/geçersizse varsayılan."""
    mod = veritabani.ayar_getir(MOD_ANAHTAR, VARSAYILAN_MOD)
    return mod if mod in MODLAR else VARSAYILAN_MOD


def mod_bilgisi(mod=None, simdi=None):
    """GET /api/ayarlar/mod yanıtı ve WS "mod" mesajının verisi."""
    mod = mod or mod_getir()
    simdi = simdi or simdi_yerel()
    return {"mod": mod, "etkin_mod": etkin_mod(mod, simdi),
            "aciklama": mod_aciklama(mod, simdi)}


# ---------------- Yangın teyidi (korelasyon) ----------------

# dugum -> {"duman": (zaman, olay_id) | None, "alev": ..., "duman_alarm": bool,
#           "alev_alarm": bool, "kilitli": bool}
_korelasyon = {}
# Mesajın sunucuya varış zamanı. Testlerde değiştirilebilir.
_saat = time.time


def korelasyon(durum, sensor, gecis, olay_id, simdi, pencere):
    """
    Saf korelasyon adımı; düğümün `durum` sözlüğünü yerinde günceller.
    sensor: "duman" | "alev"; gecis: "alarm" (alarma giriş) | "normal".
    Teyit oluştuysa tetikleyen olay id'leri [önceki, bu] döner, yoksa None.
    Teyitten sonra düğüm kilitlenir; duman ve alev ikisi de normale dönünce açılır.
    """
    diger = "alev" if sensor == "duman" else "duman"
    if gecis == "normal":
        durum[f"{sensor}_alarm"] = False
        durum[sensor] = None
        if not durum.get("duman_alarm") and not durum.get("alev_alarm"):
            durum["kilitli"] = False
        return None

    durum[f"{sensor}_alarm"] = True
    durum[sensor] = (simdi, olay_id)
    if durum.get("kilitli"):
        return None
    onceki = durum.get(diger)
    if onceki and durum.get(f"{diger}_alarm") and abs(simdi - onceki[0]) <= pencere:
        durum["kilitli"] = True
        return [onceki[1], olay_id]
    return None


def korelasyona_bildir(dugum, sensor, gecis, olay_id):
    """Dinleyiciden çağrılır: düğümün korelasyon durumunu ilerletir."""
    with _kilit:
        durum = _korelasyon.setdefault(dugum, {})
        return korelasyon(durum, sensor, gecis, olay_id, _saat(), config.KORELASYON_PENCERE_SN)


def teyit_mesaji(dugum):
    konum = config.DUGUM_KONUMLARI.get(dugum) or dugum
    return f"Yangın teyitli: duman + alev ({konum})"


# ---------------- Değerlendirme ----------------

def degerlendir(dugum, sensor, deger, mod=None, simdi=None):
    """
    Bir sensör okumasını değerlendirir.
    Dönüş: (olay_var_mi, seviye, mesaj, kural)
      - olay_var_mi: True ise olaylar tablosuna yazılır + gerekirse bildirim
      - seviye: SEVIYELER'den biri
      - mesaj: panelde/logda gösterilecek açıklama
      - kural: uygulanan kuralın etiketi (olaylar.kural), olay yoksa None olabilir
    Hareket için mod/simdi verilmezse kalıcı mod ve sunucu saati kullanılır.
    """
    if sensor == "hareket":
        if deger == 1:
            seviye, kural, mesaj = hareket_seviyesi(mod or mod_getir(), simdi or simdi_yerel())
            return True, seviye, mesaj, kural
        return False, "bilgi", "Hareket yok", None

    if sensor == "duman":
        # > ESIK_DUMAN: alarma gir; < ESIK_DUMAN_NORMAL olana kadar alarmda kal
        gecis = _gecis(dugum, "duman", deger > config.ESIK_DUMAN,
                       deger < config.ESIK_DUMAN_NORMAL)
        if gecis == "alarm":
            return True, "yuksek", f"Duman/gaz eşiği aşıldı (deger={deger})", "histerezis"
        if gecis == "normal":
            return True, "bilgi", f"Duman/gaz normale döndü (deger={deger})", "histerezis"
        if alarmda_mi(dugum, "duman"):
            return False, "yuksek", f"Duman/gaz hâlâ yüksek (deger={deger})", "histerezis"
        return False, "bilgi", f"Duman/gaz normal (deger={deger})", None

    if sensor == "alev":
        gecis = _gecis(dugum, "alev", deger == 1, deger == 0)
        if gecis == "alarm":
            return True, "kritik", "ALEV ALGILANDI", "histerezis"
        if gecis == "normal":
            return True, "bilgi", "Alev söndü", "histerezis"
        if alarmda_mi(dugum, "alev"):
            return False, "kritik", "Alev sürüyor", "histerezis"
        return False, "bilgi", "Alev yok", None

    if sensor == "durum":
        # deger burada 1=online, 0=offline gibi kullanılabilir
        if deger == 0:
            return True, "uyari", "Cihaz çevrimdışı", "baglanti"
        return False, "bilgi", "Cihaz çevrimiçi", None

    # Bilinmeyen sensör tipi
    return False, "bilgi", f"Bilinmeyen sensör: {sensor}", None


def bildirim_gerekli_mi(seviye):
    """E-posta bildirimi BILDIRIM_SEVIYELER'deki seviyeler için gönderilir."""
    return seviye in config.BILDIRIM_SEVIYELER
