"""
E-posta bildirimi.
Kritik/yüksek olaylarda SMTP (SSL, 465) ile HTML + düz metin mail gönderir.

- gonder(olay) MQTT dinleyiciden çağrılır; hiçbir zaman beklemez, gönderim
  ayrı bir thread'de yapılır.
- Spam önleme: aynı (düğüm, sensör, seviye) için BILDIRIM_BEKLEME_SN içinde
  ikinci mail gitmez. Bu sürede bastırılan olaylar sayılır ve bir sonraki
  mailde "+N benzer olay" olarak yazılır.
- Hata (yanlış parola, internet yok) loglanır, tekrar denenmez.
"""
import html
import smtplib
import ssl
import threading
import time
from datetime import datetime
from email.message import EmailMessage
from email.utils import formataddr

from app import config

# Panelle aynı seviye renkleri (frontend/src/sabitler.js SEVIYE_RENK)
SEVIYE_RENK = {
    "bilgi": "#60a5fa",
    "uyari": "#2dd4bf",
    "orta": "#facc15",
    "yuksek": "#fb923c",
    "kritik": "#fb7185",
}
SEVIYE_ETIKET = {
    "bilgi": "BİLGİ",
    "uyari": "UYARI",
    "orta": "ORTA",
    "yuksek": "YÜKSEK",
    "kritik": "KRİTİK",
}
SENSOR_AD = {
    "hareket": "PIR hareket sensörü",
    "duman": "MQ-2 duman/gaz sensörü",
    "alev": "KY-026 alev sensörü",
    "durum": "Cihaz durumu",
}
# Konu satırındaki kısa olay başlığı
OLAY_BASLIK = {
    "hareket": "Hareket algılandı",
    "duman": "Duman/gaz eşiği aşıldı",
    "alev": "Alev algılandı",
    "durum": "Cihaz çevrimdışı",
}

# (dugum, sensor, seviye) -> {"son": son gönderim (monotonic), "bastirilan": int}
_bekleme = {}
_kilit = threading.Lock()
# Testlerde zamanı ileri sarmak için değiştirilebilir.
_saat = time.monotonic

if not config.BILDIRIM_AKTIF:
    if not (config.SMTP_KULLANICI and config.SMTP_PAROLA):
        print("[BILDIRIM] SMTP_KULLANICI/SMTP_PAROLA boş, e-posta bildirimi devre dışı.")
    else:
        print("[BILDIRIM] BILDIRIM_AKTIF=false, e-posta bildirimi kapalı.")


# ---------------- Mail içeriği ----------------

def _konum(dugum):
    return config.DUGUM_KONUMLARI.get(dugum, "")


def _deger_metni(sensor, deger):
    if sensor == "duman":
        return f"{deger} / 4095 (eşik {config.ESIK_DUMAN})"
    if sensor in ("alev", "hareket"):
        return f"{deger} ({'algılandı' if deger == 1 else 'yok'})"
    if sensor == "durum":
        return "çevrimdışı" if deger == 0 else "çevrimiçi"
    return str(deger)


def _sure_metni(saniye):
    """300 -> "5 dk'da", 30 -> "30 sn'de" (bulunma eki dahil)."""
    return f"{saniye // 60} dk'da" if saniye >= 60 else f"{saniye} sn'de"


def mail_olustur(olay, bastirilan=0):
    """Olaydan (konu, html, düz metin) üretir."""
    dugum, sensor, seviye = olay["dugum"], olay["sensor"], olay["seviye"]
    konum = _konum(dugum)
    etiket = SEVIYE_ETIKET.get(seviye, seviye.upper())
    renk = SEVIYE_RENK.get(seviye, "#94a3b8")
    baslik = OLAY_BASLIK.get(sensor, olay.get("mesaj", "Olay"))
    yer = f"{dugum} ({konum})" if konum else dugum
    zaman = datetime.fromtimestamp(olay.get("zaman") or time.time()).strftime("%d.%m.%Y %H:%M:%S")
    deger = _deger_metni(sensor, olay.get("deger"))
    sensor_ad = SENSOR_AD.get(sensor, sensor)
    ek = (f"Son {_sure_metni(config.BILDIRIM_BEKLEME_SN)} +{bastirilan} benzer olay"
          if bastirilan else "")

    konu = f"[{etiket}] {baslik} — {yer}"

    satirlar = [
        ("Düğüm", dugum),
        ("Konum", konum or "Tanımsız"),
        ("Sensör", sensor_ad),
        ("Değer", deger),
        ("Zaman", zaman),
    ]

    metin = "\n".join(
        [f"[{etiket}] {baslik}", ""]
        + [f"{ad:8}: {deger_}" for ad, deger_ in satirlar]
        + ([f"\n{ek}."] if ek else [])
        + ["", f"Panel: {config.PANEL_URL}", "",
           "Bu mail Kampüs Güvenlik Sistemi tarafından otomatik gönderildi."]
    )

    e = html.escape
    tablo = "".join(
        f'<tr><td style="padding:8px 0;color:#64748b;font-size:13px;width:90px;'
        f'border-bottom:1px solid #e2e8f0;">{e(ad)}</td>'
        f'<td style="padding:8px 0;color:#0f172a;font-size:14px;font-weight:600;'
        f'border-bottom:1px solid #e2e8f0;">{e(str(deger_))}</td></tr>'
        for ad, deger_ in satirlar
    )
    ek_html = (
        f'<p style="margin:16px 0 0;padding:10px 12px;background-color:#f1f5f9;'
        f'border-left:3px solid {renk};color:#334155;font-size:13px;">{e(ek)}.</p>'
        if ek else ""
    )
    govde = f"""\
<!doctype html>
<html lang="tr"><head><meta charset="utf-8">
<meta name="color-scheme" content="light dark"><meta name="supported-color-schemes" content="light dark">
</head>
<body style="margin:0;padding:0;background-color:#e2e8f0;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" bgcolor="#e2e8f0" style="background-color:#e2e8f0;">
<tr><td align="center" style="padding:24px 12px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;border-collapse:collapse;font-family:Segoe UI,Arial,Helvetica,sans-serif;">
  <tr><td bgcolor="#0b1220" style="background-color:#0b1220;padding:18px 24px;border-radius:8px 8px 0 0;border-bottom:3px solid {renk};">
    <div style="color:#94a3b8;font-size:11px;letter-spacing:1.5px;font-weight:600;">KAMPÜS GÜVENLİK SİSTEMİ</div>
    <div style="color:#f8fafc;font-size:20px;font-weight:700;margin-top:6px;">{e(baslik)}</div>
  </td></tr>
  <tr><td bgcolor="#ffffff" style="background-color:#ffffff;padding:20px 24px;border-radius:0 0 8px 8px;">
    <span style="display:inline-block;background-color:{renk};color:#1a0b0f;font-size:12px;font-weight:700;letter-spacing:1px;padding:4px 10px;border-radius:4px;">{e(etiket)}</span>
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-top:14px;border-collapse:collapse;">{tablo}</table>
    {ek_html}
    <table role="presentation" cellpadding="0" cellspacing="0" style="margin-top:20px;"><tr>
      <td bgcolor="#0b1220" style="background-color:#0b1220;border-radius:6px;">
        <a href="{e(config.PANEL_URL)}" style="display:inline-block;padding:10px 18px;color:#f8fafc;font-size:14px;font-weight:600;text-decoration:none;">Paneli aç</a>
      </td></tr></table>
    <p style="margin:20px 0 0;color:#64748b;font-size:12px;">Bu mail otomatik gönderildi. Panel: {e(config.PANEL_URL)}</p>
  </td></tr>
</table>
</td></tr></table>
</body></html>"""
    return konu, govde, metin


# ---------------- Gönderim ----------------

def _smtp_gonder(konu, html_govde, metin):
    """Maili SMTP SSL ile gönderir. Başarılıysa True, hata olursa loglar ve False döner."""
    msg = EmailMessage()
    msg["Subject"] = konu
    msg["From"] = formataddr(("Kampüs Güvenlik", config.SMTP_KULLANICI))
    msg["To"] = config.BILDIRIM_ALICI
    msg.set_content(metin, charset="utf-8", cte="quoted-printable")
    msg.add_alternative(html_govde, subtype="html", charset="utf-8", cte="quoted-printable")
    try:
        with smtplib.SMTP_SSL(config.SMTP_SUNUCU, config.SMTP_PORT,
                              context=ssl.create_default_context(), timeout=15) as smtp:
            try:
                smtp.login(config.SMTP_KULLANICI, config.SMTP_PAROLA)
            except smtplib.SMTPServerDisconnected:
                # Gmail, AUTH PLAIN'de kimliği reddedince 535 yerine bağlantıyı kesebiliyor.
                raise smtplib.SMTPAuthenticationError(535, b"baglanti giriste kesildi")
            smtp.send_message(msg)
    except smtplib.SMTPAuthenticationError:
        print("[BILDIRIM] Gönderilemedi: kullanıcı adı/parola reddedildi "
              "(Gmail için 2 adımlı doğrulama + uygulama şifresi gerekir).")
        return False
    except (smtplib.SMTPException, OSError) as e:
        print(f"[BILDIRIM] Gönderilemedi ({type(e).__name__}): {e}")
        return False
    print(f"[BILDIRIM] Gönderildi -> {config.BILDIRIM_ALICI}: {konu}")
    return True


def hemen_gonder(olay, bastirilan=0):
    """Bekleme kontrolü olmadan, bu thread'de gönderir (eposta_test.py için)."""
    return _smtp_gonder(*mail_olustur(olay, bastirilan))


def gonder(olay):
    """
    Olay için gerekiyorsa mail gönderimini arka planda başlatır, beklemeden döner.
    Gönderim başladıysa Thread'i, başlamadıysa (kapalı / bekleme süresi) None döndürür.
    """
    if not config.BILDIRIM_AKTIF:
        return None
    if olay["seviye"] not in config.BILDIRIM_SEVIYELER:
        return None
    if olay["dugum"] in config.BILDIRIM_HARIC_DUGUMLER:
        return None

    anahtar = (olay["dugum"], olay["sensor"], olay["seviye"])
    simdi = _saat()
    with _kilit:
        kayit = _bekleme.get(anahtar)
        if kayit and simdi - kayit["son"] < config.BILDIRIM_BEKLEME_SN:
            kayit["bastirilan"] += 1
            return None
        bastirilan = kayit["bastirilan"] if kayit else 0
        # Süre deneme anında başlar: hata olsa da her olayda yeniden denenmez.
        _bekleme[anahtar] = {"son": simdi, "bastirilan": 0}

    t = threading.Thread(target=hemen_gonder, args=(olay, bastirilan),
                         name="bildirim", daemon=True)
    t.start()
    return t
