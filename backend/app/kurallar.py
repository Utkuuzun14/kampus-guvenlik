"""
Kural motoru.
Gelen bir sensör mesajını değerlendirir, alarm seviyesini ve
insan-okur mesajı belirler. Sözleşmedeki eşik/alarm kurallarını uygular.

Alarm fırtınasını önlemek için duman ve alev histerezisli çalışır: olay
yalnızca durum DEĞİŞİMİNDE üretilir (normal → alarm, alarm → normal).
Durum düğüm bazında bellekte tutulur; backend yeniden başlarsa tüm düğümler
"normal" kabul edilerek sıfırdan başlanır.
"""
import threading

from app import config

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


def degerlendir(dugum, sensor, deger):
    """
    Bir sensör okumasını değerlendirir.
    Dönüş: (olay_var_mi, seviye, mesaj)
      - olay_var_mi: True ise olaylar tablosuna yazılır + gerekirse bildirim
      - seviye: SEVIYELER'den biri
      - mesaj: panelde/logda gösterilecek açıklama
    """
    if sensor == "hareket":
        if deger == 1:
            return True, "orta", "Hareket algılandı"
        return False, "bilgi", "Hareket yok"

    if sensor == "duman":
        # > ESIK_DUMAN: alarma gir; < ESIK_DUMAN_NORMAL olana kadar alarmda kal
        gecis = _gecis(dugum, "duman", deger > config.ESIK_DUMAN,
                       deger < config.ESIK_DUMAN_NORMAL)
        if gecis == "alarm":
            return True, "yuksek", f"Duman/gaz eşiği aşıldı (deger={deger})"
        if gecis == "normal":
            return True, "bilgi", f"Duman/gaz normale döndü (deger={deger})"
        if alarmda_mi(dugum, "duman"):
            return False, "yuksek", f"Duman/gaz hâlâ yüksek (deger={deger})"
        return False, "bilgi", f"Duman/gaz normal (deger={deger})"

    if sensor == "alev":
        gecis = _gecis(dugum, "alev", deger == 1, deger == 0)
        if gecis == "alarm":
            return True, "kritik", "ALEV ALGILANDI"
        if gecis == "normal":
            return True, "bilgi", "Alev söndü"
        if alarmda_mi(dugum, "alev"):
            return False, "kritik", "Alev sürüyor"
        return False, "bilgi", "Alev yok"

    if sensor == "durum":
        # deger burada 1=online, 0=offline gibi kullanılabilir
        if deger == 0:
            return True, "uyari", "Cihaz çevrimdışı"
        return False, "bilgi", "Cihaz çevrimiçi"

    # Bilinmeyen sensör tipi
    return False, "bilgi", f"Bilinmeyen sensör: {sensor}"


def bildirim_gerekli_mi(seviye):
    """E-posta bildirimi BILDIRIM_SEVIYELER'deki seviyeler için gönderilir."""
    return seviye in config.BILDIRIM_SEVIYELER
