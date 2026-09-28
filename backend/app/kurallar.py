"""
Kural motoru.
Gelen bir sensör mesajını değerlendirir, alarm seviyesini ve
insan-okur mesajı belirler. Sözleşmedeki eşik/alarm kurallarını uygular.
"""
from app import config

# Alarm seviyeleri (düşükten yükseğe)
SEVIYELER = ["bilgi", "uyari", "orta", "yuksek", "kritik"]


def degerlendir(sensor, deger):
    """
    Bir sensör okumasını değerlendirir.
    Dönüş: (alarm_var_mi, seviye, mesaj)
      - alarm_var_mi: True ise olaylar tablosuna yazılır + gerekirse bildirim
      - seviye: SEVIYELER'den biri
      - mesaj: panelde/logda gösterilecek açıklama
    """
    if sensor == "hareket":
        if deger == 1:
            return True, "orta", "Hareket algılandı"
        return False, "bilgi", "Hareket yok"

    if sensor == "duman":
        if deger > config.ESIK_DUMAN:
            return True, "yuksek", f"Duman/gaz eşiği aşıldı (deger={deger})"
        return False, "bilgi", f"Duman/gaz normal (deger={deger})"

    if sensor == "alev":
        if deger == 1:
            return True, "kritik", "ALEV ALGILANDI"
        return False, "bilgi", "Alev yok"

    if sensor == "durum":
        # deger burada 1=online, 0=offline gibi kullanılabilir
        if deger == 0:
            return True, "uyari", "Cihaz çevrimdışı"
        return False, "bilgi", "Cihaz çevrimiçi"

    # Bilinmeyen sensör tipi
    return False, "bilgi", f"Bilinmeyen sensör: {sensor}"


def bildirim_gerekli_mi(seviye):
    """E-posta bildirimi bu seviyeler için gönderilir."""
    return seviye in ("yuksek", "kritik")
