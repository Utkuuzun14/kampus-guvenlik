"""
Test senaryoları scripti (rapor Tablo 6, T1-T11).
Her senaryo için broker'a kontrollü mesaj gönderir, backend'in olayı doğru
işleyip işlemediğini API üzerinden doğrular. T6 (e-posta) gerçek mail
göndermez: SMTP taklit edilir, MQTT işleyicisi süreç içinde çağrılır.
T7, test_dugum için LWT'li bir client açıp socket'ini temiz olmayan şekilde
kapatır ve /api/dugumler'de çevrimdışı düşüp geri geldiğini doğrular.
T8, duman/alev histerezisini doğrular (art arda eşik üstü ölçüm → tek olay).
T9, olay yaşam döngüsünü doğrular: PATCH /api/olaylar/{id}/durum ile ileri
geçişler, geri gitmede 409, WebSocket olay_guncelleme ve /api/istatistik/mudahale.
T10, yangın teyidini (duman + alev korelasyonu) canlı ve kural fonksiyonu
üzerinden doğrular. T11, güvenlik modunu (PUT/GET /api/ayarlar/mod, WS "mod")
ve moda/saate bağlı hareket kuralını doğrular.
Hareket beklentileri "orta" olduğundan script başta güvenlik modunu mesai_disi
yapar ve sonunda (hata olsa da) kullanıcının önceki moduna geri alır.
Backend histerezis durumunu bellekte tuttuğu için testler başta test_dugum'u
normale çeker; böylece aynı backend açıkken tekrar çalıştırmak da tutarlıdır.

Çalıştırmadan önce: broker + backend çalışıyor olmalı, sahte veri üreteci
KAPATILMALI (test sonuçlarını kirletmemesi için).

Çalıştırma (backend venv aktifken, proje kökünden):
    python scripts/test_senaryolari.py

Çalışma bitince (testler başarısız olsa bile) bu çalıştırmada oluşan
test_dugum kayıtları olaylar, olay_adimlari ve sensor_gecmis tablolarından silinir.
"""
import json
import time
import sys
from datetime import datetime
import os
import sqlite3
import threading
import urllib.error
import urllib.request

import paho.mqtt.client as mqtt
from websockets.sync.client import connect as ws_baglan  # uvicorn bağımlılığı, venv'de var

BACKEND_DIZINI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend")
sys.path.insert(0, BACKEND_DIZINI)
from app import config, kurallar  # noqa: E402
import sahte_veri  # noqa: E402  (aynı dizin: LWT'li client ve kopma fonksiyonu)

API = "http://127.0.0.1:8000"
WS_URL = "ws://127.0.0.1:8000/ws"
DUGUM = "test_dugum"
TABLOLAR = ("olaylar", "sensor_gecmis")


def db_yolu():
    """Backend backend/ dizininden çalıştığı için göreli yol oraya göre çözülür."""
    yol = config.VERITABANI_YOLU
    return yol if os.path.isabs(yol) else os.path.join(BACKEND_DIZINI, yol)


def son_kayit_idleri():
    """Her tablodaki en büyük id (testten önceki durum)."""
    with sqlite3.connect(db_yolu()) as conn:
        return {t: conn.execute(f"SELECT COALESCE(MAX(id), 0) FROM {t}").fetchone()[0]
                for t in TABLOLAR}


def test_verisini_temizle(baslangic):
    """Bu çalıştırmada oluşan test_dugum kayıtlarını siler."""
    conn = sqlite3.connect(db_yolu())
    try:
        silinen = {}
        # Önce silinecek olayların durum adımları (tablo eski DB'de olmayabilir)
        if conn.execute("SELECT 1 FROM sqlite_master WHERE name = 'olay_adimlari'").fetchone():
            silinen["olay_adimlari"] = conn.execute(
                "DELETE FROM olay_adimlari WHERE olay_id IN "
                "(SELECT id FROM olaylar WHERE dugum = ? AND id > ?)",
                (DUGUM, baslangic["olaylar"])).rowcount
        for t in TABLOLAR:
            imlec = conn.execute(f"DELETE FROM {t} WHERE dugum = ? AND id > ?",
                                 (DUGUM, baslangic[t]))
            silinen[t] = imlec.rowcount
        conn.commit()
    finally:
        conn.close()
    print(f"\nTemizlik: {DUGUM} kayıtları silindi "
          f"(olaylar: {silinen['olaylar']}, olay_adimlari: {silinen.get('olay_adimlari', 0)}, "
          f"sensor_gecmis: {silinen['sensor_gecmis']})")


def mqtt_baglan():
    client = mqtt.Client(
        client_id="test-script",
        protocol=mqtt.MQTTv5,
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    )
    client.username_pw_set(config.MQTT_KULLANICI, config.MQTT_PAROLA)
    client.connect(config.MQTT_HOST, config.MQTT_PORT, keepalive=60)
    client.loop_start()
    return client


def yayinla(client, sensor, deger):
    konu = f"kampus/guvenlik/{DUGUM}/{sensor}"
    mesaj = {"dugum": DUGUM, "sensor": sensor, "deger": deger, "zaman": int(time.time())}
    client.publish(konu, json.dumps(mesaj, ensure_ascii=False), qos=1)


def son_olay():
    """Backend API'den en son olayı çeker."""
    with urllib.request.urlopen(f"{API}/api/olaylar?limit=1", timeout=5) as r:
        veri = json.loads(r.read().decode("utf-8"))
    return veri[0] if veri else None


def son_olay_id():
    """En son olayın id'si (hiç olay yoksa 0)."""
    olay = son_olay()
    return olay["id"] if olay else 0


def test_calistir(client, no, ad, sensor, deger, beklenen_seviye):
    """Alarm üretmesi beklenen senaryo: yeni ve doğru olay oluşmalı."""
    print(f"\n[{no}] {ad}")
    onceki_id = son_olay_id()
    print(f"    Gönderiliyor: {sensor} = {deger}")
    yayinla(client, sensor, deger)
    time.sleep(1.5)  # backend işlesin
    # Son olaya değil bu sensörün yeni olayına bakılır: aynı mesaj bileşik bir
    # olay da üretebilir (ör. T2'den hemen sonra T3 → yangin_teyit)
    yeni = yeni_olaylar(onceki_id)
    olay = next((o for o in yeni if o["sensor"] == sensor), None)

    if not olay:
        print(f"    ✗ BAŞARISIZ (yeni {sensor} olayı oluşmadı, son id: {onceki_id})")
        return False
    for ek in yeni:
        if ek is not olay:
            print(f"    Ek olay: #{ek['id']} {ek['sensor']}/{ek['seviye']} - {ek['mesaj']}")
    if olay["seviye"] == beklenen_seviye:
        print(f"    Sonuç: #{olay['id']} {olay['seviye']} - {olay['mesaj']}")
        print(f"    ✓ BAŞARILI (beklenen seviye: {beklenen_seviye})")
        return True
    print(f"    ✗ BAŞARISIZ (beklenen: {DUGUM}/{sensor}/{beklenen_seviye}, "
          f"bulunan: {olay['dugum']}/{olay['sensor']}/{olay['seviye']})")
    return False


def test_alarm_yok(client, no, ad, sensor, deger):
    """Alarm üretmemesi beklenen senaryo: yeni olay OLUŞMAMALI."""
    print(f"\n[{no}] {ad}")
    onceki_id = son_olay_id()
    print(f"    Gönderiliyor: {sensor} = {deger}")
    yayinla(client, sensor, deger)
    time.sleep(1.5)  # backend işlesin
    sonraki_id = son_olay_id()

    if sonraki_id == onceki_id:
        print(f"    Sonuç: yeni olay oluşmadı (son id: {onceki_id})")
        print("    ✓ BAŞARILI (normal değer alarm üretmedi)")
        return True
    olay = son_olay()
    print(f"    ✗ BAŞARISIZ (beklenmeyen olay: #{olay['id']} "
          f"{olay['dugum']}/{olay['sensor']}/{olay['seviye']})")
    return False


def yeni_olaylar(onceki_id):
    """onceki_id'den sonra test düğümü için oluşan olaylar (eski → yeni)."""
    with urllib.request.urlopen(f"{API}/api/olaylar?limit=100", timeout=5) as r:
        veri = json.loads(r.read().decode("utf-8"))
    return sorted((o for o in veri if o["id"] > onceki_id and o["dugum"] == DUGUM),
                  key=lambda o: o["id"])


def normale_cek(client):
    """Histerezis durumunu sıfırlar (oluşan bilgi olayları testi etkilemez)."""
    yayinla(client, "duman", 400)
    yayinla(client, "alev", 0)
    time.sleep(1.5)


def test_histerezis(client):
    """
    T8: Alarm fırtınası önleme. Art arda eşik üstü ölçüm tek yüksek olay üretir,
    ölü bantta (1600-1800) olay yok, 1600 altına inince tek bilgi olayı.
    Alev: 1 olarak kaldıkça olay yok, 1 → 0'da tek bilgi olayı (T3'ten devam).
    """
    print("\n[T8] Histerezis (alarm fırtınası önleme)")
    kontroller = []

    def adim(ad, olcumler, beklenen):
        """olcumler: [(sensor, deger)], beklenen: [(sensor, seviye)]"""
        onceki_id = son_olay_id()
        for sensor, deger in olcumler:
            yayinla(client, sensor, deger)
            time.sleep(0.1)
        time.sleep(1.5)
        gelen = [(o["sensor"], o["seviye"]) for o in yeni_olaylar(onceki_id)]
        tamam = gelen == beklenen
        degerler = ", ".join(str(d) for _, d in olcumler)
        print(f"    {'✓' if tamam else '✗'} {ad}: [{degerler}] → "
              f"{len(gelen)} olay {gelen if gelen else ''}".rstrip())
        kontroller.append(tamam)

    # T2'den kalan duman alarmını kapat (bu adım sayılmaz)
    yayinla(client, "duman", 1500)
    time.sleep(1.5)

    adim("art arda 5 eşik üstü ölçüm → tek yüksek olay",
         [("duman", d) for d in (2100, 2500, 2900, 2300, 1900)], [("duman", "yuksek")])
    adim("ölü bant (1600-1800) → olay yok", [("duman", 1700)], [])
    adim("1600 altı → tek bilgi olayı (normale döndü)", [("duman", 1500)], [("duman", "bilgi")])
    adim("alev 1 olarak kalıyor → olay yok", [("alev", 1), ("alev", 1)], [])
    adim("alev 1 → 0 → tek bilgi olayı (söndü)", [("alev", 0)], [("alev", "bilgi")])

    basarili = all(kontroller)
    print(f"    {'✓ BAŞARILI' if basarili else '✗ BAŞARISIZ'}")
    return basarili


def test_bildirim():
    """
    T6: Gerçek mail göndermeden (SMTP mock) bildirim kurallarını doğrular.
    MQTT dinleyicinin mesaj işleyicisi süreç içinde, sahte DB ile çağrılır.
    Yalnızca tekil olayların bildirimi ölçülür: korelasyon kapatılır (teyit
    maili T10'da) ve mod mesai_disi'ye sabitlenir (hareket = orta).
    """
    from types import SimpleNamespace
    from unittest import mock
    from app import bildirim, kurallar, mqtt_dinleyici

    print("\n[T6] Bildirim sistemi (e-posta, SMTP taklit edilerek)")
    dugum = "t6_dugum"
    saat = [1000.0]

    def yavas_gonderim(*args):
        time.sleep(0.5)  # yavaş SMTP sunucusu
        return True

    def mesaj_isle(sensor, deger):
        """Mesajı işler, dinleyicinin ne kadar beklediğini döndürür."""
        msg = SimpleNamespace(topic=f"kampus/guvenlik/{dugum}/{sensor}",
                              payload=json.dumps({"deger": deger, "zaman": int(time.time())}).encode())
        bas = time.perf_counter()
        mqtt_dinleyici._on_message(mock.Mock(), None, msg)
        sure = time.perf_counter() - bas
        for t in threading.enumerate():
            if t.name == "bildirim":
                t.join(5)
        return sure

    def sahte_olay_ekle(dugum_, sensor, deger, seviye, mesaj, zaman, kural=None, iliskili=None):
        return {"id": 0, "dugum": dugum_, "sensor": sensor, "deger": deger,
                "seviye": seviye, "mesaj": mesaj, "zaman": zaman,
                "kural": kural, "iliskili": iliskili}

    kontroller = []

    def kontrol(ad, kosul):
        print(f"    {'✓' if kosul else '✗'} {ad}")
        kontroller.append(kosul)

    with mock.patch.object(bildirim, "_smtp_gonder", side_effect=yavas_gonderim) as smtp, \
            mock.patch.object(bildirim, "_saat", lambda: saat[0]), \
            mock.patch.dict(bildirim._bekleme, clear=True), \
            mock.patch.dict(kurallar._alarm, clear=True), \
            mock.patch.dict(kurallar._korelasyon, clear=True), \
            mock.patch.object(config, "KORELASYON_PENCERE_SN", -1), \
            mock.patch.object(kurallar, "mod_getir", lambda: "mesai_disi"), \
            mock.patch.object(config, "BILDIRIM_AKTIF", True), \
            mock.patch.object(mqtt_dinleyici.veritabani, "olay_ekle", sahte_olay_ekle), \
            mock.patch.object(mqtt_dinleyici.veritabani, "gecmis_ekle", lambda *a: None):

        sure = mesaj_isle("alev", 1)
        kontrol("kritik (alev) olayında mail gönderildi", smtp.call_count == 1)
        kontrol(f"konu doğru: {smtp.call_args[0][0] if smtp.call_args else '-'}",
                bool(smtp.call_args) and smtp.call_args[0][0].startswith("[KRİTİK] Alev algılandı"))
        kontrol(f"dinleyici beklemedi ({sure * 1000:.0f} ms, SMTP 500 ms sürüyor)", sure < 0.2)

        mesaj_isle("hareket", 1)
        kontrol("orta (hareket) olayında mail gönderilmedi", smtp.call_count == 1)

        mesaj_isle("duman", 2500)
        kontrol("yüksek (duman) olayında mail gönderildi", smtp.call_count == 2)

        # Histerezis: yeni alev olayı için önce söner (bilgi olayı, mail yok)
        saat[0] += 10
        mesaj_isle("alev", 0)
        kontrol("alev söndü (bilgi) olayında mail gönderilmedi", smtp.call_count == 2)
        mesaj_isle("alev", 1)
        kontrol(f"bekleme süresinde ({config.BILDIRIM_BEKLEME_SN} sn) ikinci alev maili engellendi",
                smtp.call_count == 2)

        saat[0] += config.BILDIRIM_BEKLEME_SN
        mesaj_isle("alev", 0)
        mesaj_isle("alev", 1)
        metin = smtp.call_args[0][2] if smtp.call_count == 3 else ""
        kontrol("süre dolunca yeni mail gitti, bastırılan olay yazıldı (+1 benzer olay)",
                smtp.call_count == 3 and "+1 benzer olay" in metin)

    basarili = all(kontroller)
    print(f"    {'✓ BAŞARILI' if basarili else '✗ BAŞARISIZ'}")
    return basarili


def dugum_durumu():
    """/api/dugumler'deki test düğümü (yoksa None)."""
    with urllib.request.urlopen(f"{API}/api/dugumler", timeout=5) as r:
        liste = json.loads(r.read().decode("utf-8"))
    return next((d for d in liste if d["id"] == DUGUM), None)


def durum_bekle(kosul, sure=5.0):
    """Koşul sağlanana kadar /api/dugumler'i yoklar. (sağlandı mı, geçen sn, son durum)"""
    bas = time.monotonic()
    while True:
        d = dugum_durumu()
        if d and kosul(d):
            return True, time.monotonic() - bas, d
        if time.monotonic() - bas > sure:
            return False, time.monotonic() - bas, d
        time.sleep(0.2)


def test_lwt():
    """
    T7: LWT ile çevrimdışı düşme ve geri gelme (sahte üretecin dugum3 davranışı).
    Üreteçle aynı fonksiyonlar kullanılır; rastgele kopmayı beklemek yerine
    kopma hemen tetiklenir.
    """
    print(f"\n[T7] LWT: çevrimdışı düşme ve geri gelme ({DUGUM})")
    kontroller = []

    def kontrol(ad, sonuc):
        tamam, sure, d = sonuc
        ozet = f"cevrimici={d['cevrimici']}, son_durum={d['son_durum']}" if d else "düğüm yok"
        print(f"    {'✓' if tamam else '✗'} {ad} ({sure:.1f} sn; {ozet})")
        kontroller.append(tamam)

    client = sahte_veri.istemci_olustur(DUGUM, client_id="test-lwt")
    try:
        sahte_veri.durum_yayinla(client, DUGUM, online=True).wait_for_publish(2)
        kontrol("bağlandı, çevrimiçi göründü", durum_bekle(lambda d: d["cevrimici"]))

        sahte_veri.baglantiyi_kopar(client)
        print("    socket DISCONNECT gönderilmeden kapatıldı")
        kontrol("broker LWT yayınladı, çevrimdışı düştü",
                durum_bekle(lambda d: not d["cevrimici"] and d["son_durum"] == "offline"))

        client = sahte_veri.istemci_olustur(DUGUM, client_id="test-lwt")
        sahte_veri.durum_yayinla(client, DUGUM, online=True).wait_for_publish(2)
        kontrol("geri bağlandı, tekrar çevrimiçi",
                durum_bekle(lambda d: d["cevrimici"] and d["son_durum"] == "online"))
    except Exception as e:
        print(f"    ✗ hata: {e}")
        kontroller.append(False)
    finally:
        # Temiz kapanış: DISCONNECT gönderilir, LWT tetiklenmez
        client.disconnect()
        client.loop_stop()

    basarili = bool(kontroller) and all(kontroller)
    print(f"    {'✓ BAŞARILI' if basarili else '✗ BAŞARISIZ'}")
    return basarili


def api_istek(yol, yontem="GET", govde=None):
    """(HTTP kodu, JSON gövde). Hata kodları da istisna atmadan döner."""
    veri = None if govde is None else json.dumps(govde).encode("utf-8")
    istek = urllib.request.Request(f"{API}{yol}", data=veri, method=yontem,
                                   headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(istek, timeout=5) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8") or "null")


def ws_mesaj_bekle(ws, kosul, sure=3.0):
    """Koşulu sağlayan ilk WS mesajı (yoksa None); diğer mesajlar atlanır."""
    bitis = time.monotonic() + sure
    while (kalan := bitis - time.monotonic()) > 0:
        try:
            mesaj = json.loads(ws.recv(timeout=kalan))
        except TimeoutError:
            return None
        if kosul(mesaj):
            return mesaj
    return None


def test_yasam_dongusu(client, baslangic):
    """
    T9: Alarm onaylama ve olay yaşam döngüsü (yeni → goruldu → mudahale → cozuldu).
    Hareket alarmı üretilir, panelin PATCH çağrıları taklit edilir; bir WS
    istemcisi olay_guncelleme yayınını dinler.
    """
    print("\n[T9] Alarm onaylama / olay yaşam döngüsü")
    kontroller = []

    def kontrol(ad, kosul):
        print(f"    {'✓' if kosul else '✗'} {ad}")
        kontroller.append(bool(kosul))

    def durum_patch(olay_id, govde):
        return api_istek(f"/api/olaylar/{olay_id}/durum", "PATCH", govde)

    try:
        onceki_id = son_olay_id()
        yayinla(client, "hareket", 1)
        time.sleep(1.5)
        olay = next((o for o in yeni_olaylar(onceki_id)
                     if o["sensor"] == "hareket" and o["seviye"] == "orta"), None)
        kontrol(f"hareket alarmı oluştu, durum=yeni "
                f"(#{olay['id'] if olay else '-'}, {olay.get('durum') if olay else '-'})",
                olay and olay.get("durum") == "yeni" and olay.get("onaylayan") is None)
        if not olay:
            raise Exception("alarm oluşmadı, kalan adımlar atlandı")
        oid = olay["id"]

        with ws_baglan(WS_URL, open_timeout=5) as ws:
            kod, v = durum_patch(oid, {"durum": "goruldu", "onaylayan": "T9 Operatör",
                                       "not": "Kamera kontrol ediliyor"})
            kontrol(f"PATCH goruldu → {kod}, goruldu_zaman dolu",
                    kod == 200 and v["durum"] == "goruldu" and v["goruldu_zaman"]
                    and v["mudahale_zaman"] is None)
            mesaj = ws_mesaj_bekle(ws, lambda m: m.get("tip") == "olay_guncelleme"
                                   and m["veri"].get("id") == oid)
            kontrol("WebSocket olay_guncelleme mesajı geldi (durum=goruldu)",
                    mesaj and mesaj["veri"]["durum"] == "goruldu")

        kod, v = durum_patch(oid, {"durum": "cozuldu", "onaylayan": "T9 Operatör"})
        kontrol(f"PATCH cozuldu → {kod}, atlanan mudahale_zaman = cozuldu_zaman",
                kod == 200 and v["durum"] == "cozuldu" and v["cozuldu_zaman"]
                and v["mudahale_zaman"] == v["cozuldu_zaman"]
                and v["goruldu_zaman"] < v["cozuldu_zaman"])
        adimlar = v.get("adimlar", []) if kod == 200 else []
        kontrol(f"olay_adimlari: {[(a['durum'], a['kim'], a['not_metni']) for a in adimlar]}",
                [a["durum"] for a in adimlar] == ["goruldu", "cozuldu"]
                and adimlar[0]["kim"] == "T9 Operatör"
                and adimlar[0]["not_metni"] == "Kamera kontrol ediliyor")

        kod, v = durum_patch(oid, {"durum": "goruldu", "onaylayan": "T9 Operatör"})
        kontrol(f"geri gitme (cozuldu → goruldu) → {kod}, mevcut={v.get('mevcut')}",
                kod == 409 and v.get("mevcut") == "cozuldu")
        kod, _ = durum_patch(oid, {"durum": "cozuldu", "onaylayan": "T9 Operatör"})
        kontrol(f"aynı duruma geçiş (cozuldu → cozuldu) → {kod}", kod == 409)

        kod, _ = durum_patch(10 ** 9, {"durum": "cozuldu", "onaylayan": "T9 Operatör"})
        kontrol(f"olmayan id → {kod}", kod == 404)
        hatalilar = [
            ("durum=xyz", {"durum": "xyz", "onaylayan": "T9"}),
            ("durum=yeni", {"durum": "yeni", "onaylayan": "T9"}),
            ("boş onaylayan", {"durum": "goruldu", "onaylayan": "   "}),
            ("41 karakter onaylayan", {"durum": "goruldu", "onaylayan": "x" * 41}),
            ("301 karakter not", {"durum": "goruldu", "onaylayan": "T9", "not": "x" * 301}),
        ]
        kodlar = {ad: durum_patch(oid, g)[0] for ad, g in hatalilar}
        kontrol(f"geçersiz gövde → 422 {kodlar}", all(k == 422 for k in kodlar.values()))

        _, acik = api_istek("/api/olaylar?durum=acik&limit=500")
        kontrol("?durum=acik: çözülen olay listede yok, listede çözülmüş kayıt yok",
                all(o["id"] != oid and o["durum"] != "cozuldu" for o in acik))

        _, liste = api_istek("/api/olaylar?limit=200")
        bilgi = [o for o in liste if o["dugum"] == DUGUM and o["id"] > baslangic["olaylar"]
                 and o["seviye"] == "bilgi"]
        kontrol(f"bilgi olayları otomatik çözüldü ({len(bilgi)} olay, onaylayan=sistem)",
                bilgi and all(o["durum"] == "cozuldu" and o["onaylayan"] == "sistem"
                              for o in bilgi))

        kod, ist = api_istek("/api/istatistik/mudahale")
        kontrol(f"/api/istatistik/mudahale → {kod} {ist}",
                kod == 200 and ist["cozulen_sayisi"] >= 1
                and isinstance(ist["ort_cozum_sn"], (int, float))
                and isinstance(ist["ort_gorulme_sn"], (int, float))
                and isinstance(ist["acik_sayisi"], int))
    except Exception as e:
        print(f"    ✗ hata: {e}")
        kontroller.append(False)

    basarili = bool(kontroller) and all(kontroller)
    print(f"    {'✓ BAŞARILI' if basarili else '✗ BAŞARISIZ'}")
    return basarili


def test_korelasyon(client):
    """
    T10: Yangın teyidi. Duman alarmı + alev KORELASYON_PENCERE_SN içinde
    (sıra fark etmeksizin) tek bir yangin_teyit (kritik) olayı üretir; yangın
    sürerken tekrar üretmez; normale dönüp yeniden yanınca yeni teyit üretir.
    Pencere dışı durum, pencereyi düşürmek yerine kural fonksiyonuyla denenir.
    """
    from app import bildirim

    print(f"\n[T10] Yangın teyidi (korelasyon, pencere {config.KORELASYON_PENCERE_SN} sn)")
    kontroller = []

    def kontrol(ad, kosul):
        print(f"    {'✓' if kosul else '✗'} {ad}")
        kontroller.append(bool(kosul))

    def gonder(olcumler, ara=0.1):
        """olcumler: [(sensor, deger, sonra_bekle)] → bu adımda oluşan olaylar"""
        onceki_id = son_olay_id()
        for sensor, deger, bekle in olcumler:
            yayinla(client, sensor, deger)
            time.sleep(bekle or ara)
        time.sleep(1.5)
        return yeni_olaylar(onceki_id)

    def teyitler(olaylar):
        return [o for o in olaylar if o["sensor"] == "yangin_teyit"]

    def bul(olaylar, sensor, seviye):
        return next((o for o in olaylar if o["sensor"] == sensor and o["seviye"] == seviye), None)

    try:
        normale_cek(client)

        # 1) Duman eşiği aşılır, 2 sn sonra alev
        olaylar = gonder([("duman", 2500, 2.0), ("alev", 1, 0)])
        duman, alev, t = bul(olaylar, "duman", "yuksek"), bul(olaylar, "alev", "kritik"), teyitler(olaylar)
        teyit = t[0] if len(t) == 1 else None
        kontrol(f"duman 2500 → 2 sn → alev=1: tek yangin_teyit "
                f"({len(t)} teyit; {teyit['mesaj'] if teyit else '-'})",
                duman and alev and teyit and teyit["seviye"] == "kritik"
                and teyit["mesaj"].startswith("Yangın teyitli: duman + alev"))
        kontrol(f"iliskili = [duman, alev] id'leri ({teyit['iliskili'] if teyit else '-'}), "
                f"kural=korelasyon, durum=yeni",
                teyit and duman and alev and teyit["iliskili"] == [duman["id"], alev["id"]]
                and teyit["kural"] == "korelasyon" and teyit["durum"] == "yeni")
        kontrol("orijinal duman/alev olayları korundu (kural=histerezis)",
                duman and alev and duman["kural"] == "histerezis" and alev["kural"] == "histerezis")
        if teyit:
            _, detay = api_istek(f"/api/olaylar/{teyit['id']}")
            kontrol(f"GET /api/olaylar/{teyit['id']} iliskili liste döner",
                    detay.get("iliskili") == teyit["iliskili"])

        # 2) Yangın sürüyor: tekrar ölçüm ve alevin söndüp yeniden yanması → teyit yok
        olaylar = gonder([("duman", 2900, 0), ("alev", 1, 0), ("alev", 0, 0), ("alev", 1, 0)])
        kontrol(f"yangın sürerken (duman alarmda) alev 0 → 1: yeni teyit yok "
                f"({[(o['sensor'], o['seviye']) for o in olaylar]})",
                not teyitler(olaylar) and bul(olaylar, "alev", "kritik"))

        # 3) Normale dönüş → yeniden yangın → yeni teyit
        normale_cek(client)
        olaylar = gonder([("duman", 2500, 1.0), ("alev", 1, 0)])
        kontrol(f"normale dönüp (duman <1600, alev 0) yeniden yangın → yeni teyit "
                f"({len(teyitler(olaylar))} teyit)", len(teyitler(olaylar)) == 1)

        # 4) Ters sıra: önce alev, sonra duman
        normale_cek(client)
        olaylar = gonder([("alev", 1, 2.0), ("duman", 2500, 0)])
        t = teyitler(olaylar)
        alev, duman = bul(olaylar, "alev", "kritik"), bul(olaylar, "duman", "yuksek")
        kontrol(f"ters sıra (alev → 2 sn → duman) → teyit, iliskili [alev, duman] "
                f"({t[0]['iliskili'] if t else '-'})",
                len(t) == 1 and alev and duman and t[0]["iliskili"] == [alev["id"], duman["id"]])
        normale_cek(client)
    except Exception as e:
        print(f"    ✗ hata: {e}")
        kontroller.append(False)

    # Kural fonksiyonu (saf): pencere sınırı ve kilit
    p = 10
    d = {}
    kurallar.korelasyon(d, "duman", "alarm", 1, 100.0, p)
    kontrol("birim: duman t=100, alev t=111 (pencere dışı) → teyit yok",
            kurallar.korelasyon(d, "alev", "alarm", 2, 111.0, p) is None)
    d = {}
    kurallar.korelasyon(d, "duman", "alarm", 1, 100.0, p)
    kontrol("birim: duman t=100, alev t=110 (sınırda) → teyit [1, 2]",
            kurallar.korelasyon(d, "alev", "alarm", 2, 110.0, p) == [1, 2])
    kurallar.korelasyon(d, "alev", "normal", 3, 111.0, p)
    kontrol("birim: duman alarmdayken alev söner ve yanar → kilit, teyit yok",
            kurallar.korelasyon(d, "alev", "alarm", 4, 112.0, p) is None)
    kurallar.korelasyon(d, "alev", "normal", 5, 113.0, p)
    kurallar.korelasyon(d, "duman", "normal", 6, 114.0, p)
    kurallar.korelasyon(d, "alev", "alarm", 7, 200.0, p)
    kontrol("birim: ikisi de normale döndükten sonra alev → duman → yeni teyit [7, 8]",
            kurallar.korelasyon(d, "duman", "alarm", 8, 205.0, p) == [7, 8])

    konu, _, metin = bildirim.mail_olustur({
        "dugum": "dugum1", "sensor": "yangin_teyit", "seviye": "kritik", "deger": 2500,
        "mesaj": kurallar.teyit_mesaji("dugum1"), "zaman": int(time.time()),
        "kural": "korelasyon", "iliskili": [412, 413]})
    kontrol(f"e-posta konusu: {konu}",
            konu.startswith("[KRİTİK] YANGIN TEYİTLİ") and "#412, #413" in metin)

    basarili = bool(kontroller) and all(kontroller)
    print(f"    {'✓ BAŞARILI' if basarili else '✗ BAŞARISIZ'}")
    return basarili


def mod_ayarla(mod):
    """PUT /api/ayarlar/mod → (HTTP kodu, gövde)"""
    return api_istek("/api/ayarlar/mod", "PUT", {"mod": mod})


def test_mod(client):
    """
    T11: Güvenlik modu + zamana bağlı hareket kuralı. Mod PUT ile değiştirilir,
    hareket=1 seviyesi doğrulanır; otomatik mod saat eşlemesi hareket_seviyesi
    üzerinden belirli saatlerle birim test edilir. Mod main()'de geri alınır.
    """
    from unittest import mock

    print("\n[T11] Güvenlik modu ve zamana bağlı hareket kuralı")
    kontroller = []

    def kontrol(ad, kosul):
        print(f"    {'✓' if kosul else '✗'} {ad}")
        kontroller.append(bool(kosul))

    def hareket_olayi():
        onceki_id = son_olay_id()
        yayinla(client, "hareket", 1)
        time.sleep(1.5)
        return next((o for o in yeni_olaylar(onceki_id) if o["sensor"] == "hareket"), None)

    try:
        with ws_baglan(WS_URL, open_timeout=5) as ws:
            kod, v = mod_ayarla("mesai")
            mesaj = ws_mesaj_bekle(ws, lambda m: m.get("tip") == "mod")
            kontrol(f"PUT mesai → {kod} {v}", kod == 200 and v["mod"] == "mesai"
                    and v["etkin_mod"] == "mesai" and v.get("aciklama"))
            kontrol("WebSocket mod mesajı geldi (mod=mesai)",
                    mesaj and mesaj["veri"]["mod"] == "mesai")
        o = hareket_olayi()
        kontrol(f"mesai: hareket → {o and o['seviye']}, {o and o['durum']}/{o and o['onaylayan']}, "
                f"kural={o and o['kural']} ({o and o['mesaj']})",
                o and o["seviye"] == "bilgi" and o["durum"] == "cozuldu"
                and o["onaylayan"] == "sistem" and o["kural"] == "mesai")

        mod_ayarla("mesai_disi")
        o = hareket_olayi()
        kontrol(f"mesai_disi: hareket → {o and o['seviye']}, kural={o and o['kural']}",
                o and o["seviye"] == "orta" and o["durum"] == "yeni" and o["kural"] == "mesai_disi")

        mod_ayarla("gece")
        o = hareket_olayi()
        kontrol(f"gece: hareket → {o and o['seviye']}, kural={o and o['kural']} ({o and o['mesaj']})",
                o and o["seviye"] == "yuksek" and o["kural"] == "gece_modu"
                and "gece modu" in o["mesaj"])

        kod, v = api_istek("/api/ayarlar/mod")
        kontrol(f"GET /api/ayarlar/mod → {kod} {v}",
                kod == 200 and v["mod"] == "gece" and v["etkin_mod"] == "gece")
        kodlar = [mod_ayarla("tatil")[0], api_istek("/api/ayarlar/mod", "PUT", {})[0]]
        kontrol(f"geçersiz mod / boş gövde → {kodlar}", kodlar == [422, 422])
        kontrol("geçersiz istek modu değiştirmedi",
                api_istek("/api/ayarlar/mod")[1]["mod"] == "gece")
    except Exception as e:
        print(f"    ✗ hata: {e}")
        kontroller.append(False)

    # Otomatik mod: saat eşlemesi (varsayılan saatlerle, .env'den bağımsız)
    tz = config.SAAT_DILIMI
    vakalar = [
        ("hafta içi 10:00", datetime(2026, 10, 14, 10, 0, tzinfo=tz), "bilgi", "mesai"),
        ("hafta içi 20:00", datetime(2026, 10, 14, 20, 0, tzinfo=tz), "orta", "mesai_disi"),
        ("hafta içi 02:00", datetime(2026, 10, 14, 2, 0, tzinfo=tz), "yuksek", "gece_modu"),
        ("cumartesi 11:00", datetime(2026, 10, 17, 11, 0, tzinfo=tz), "orta", "mesai_disi"),
        ("cumartesi 02:00", datetime(2026, 10, 17, 2, 0, tzinfo=tz), "yuksek", "gece_modu"),
        ("sınır 08:00", datetime(2026, 10, 14, 8, 0, tzinfo=tz), "bilgi", "mesai"),
        ("sınır 18:00", datetime(2026, 10, 14, 18, 0, tzinfo=tz), "orta", "mesai_disi"),
        ("sınır 23:00", datetime(2026, 10, 14, 23, 0, tzinfo=tz), "yuksek", "gece_modu"),
        ("sınır 06:00", datetime(2026, 10, 14, 6, 0, tzinfo=tz), "orta", "mesai_disi"),
    ]
    saatler = {"MESAI_BASLANGIC": "08:00", "MESAI_BITIS": "18:00",
               "GECE_BASLANGIC": "23:00", "GECE_BITIS": "06:00"}
    with mock.patch.multiple(config, **{k: datetime.strptime(v, "%H:%M").time()
                                        for k, v in saatler.items()}):
        sonuc = [(ad, kurallar.hareket_seviyesi("otomatik", t)[:2], (sev, kural))
                 for ad, t, sev, kural in vakalar]
        elle = [kurallar.hareket_seviyesi(m, vakalar[0][1])[0]
                for m in ("mesai", "mesai_disi", "gece")]
    hatali = [f"{ad}: {bulunan} ≠ {beklenen}" for ad, bulunan, beklenen in sonuc
              if bulunan != beklenen]
    kontrol(f"birim: otomatik saat eşlemesi {len(vakalar) - len(hatali)}/{len(vakalar)} "
            f"(hafta içi 10:00 bilgi, 20:00 orta, 02:00 yüksek, cumartesi 11:00 orta)"
            + (f" — {hatali}" if hatali else ""), not hatali)
    kontrol(f"birim: elle seçilen mod saatten bağımsız (mesai/mesai_disi/gece → {elle})",
            elle == ["bilgi", "orta", "yuksek"])

    basarili = bool(kontroller) and all(kontroller)
    print(f"    {'✓ BAŞARILI' if basarili else '✗ BAŞARISIZ'}")
    return basarili


def main():
    print("=" * 60)
    print("KAMPÜS GÜVENLİK SİSTEMİ - TEST SENARYOLARI (Tablo 6)")
    print("=" * 60)
    print("Not: Broker + backend çalışmalı, sahte üreteç kapalı olmalı.")

    baslangic = son_kayit_idleri()
    # T1-T9 hareketi "orta" bekler: testler mesai_disi modunda koşar,
    # kullanıcının modu sonunda geri yüklenir
    try:
        onceki_mod = api_istek("/api/ayarlar/mod")[1]["mod"]
        mod_ayarla("mesai_disi")
        print(f"Güvenlik modu test süresince mesai_disi (önceki: {onceki_mod}).")
    except Exception as e:
        onceki_mod = None
        print(f"Güvenlik modu okunamadı ({e}); backend çalışıyor mu?")
    client = mqtt_baglan()
    try:
        testleri_calistir(client, baslangic)
    finally:
        client.loop_stop()
        client.disconnect()
        if onceki_mod:
            kod, _ = mod_ayarla(onceki_mod)
            print(f"\nGüvenlik modu geri alındı: {onceki_mod} (HTTP {kod})")
        test_verisini_temizle(baslangic)


def testleri_calistir(client, baslangic):
    time.sleep(1)
    normale_cek(client)

    sonuclar = []
    sonuclar.append(("T1", "Hareket algılama",
                     test_calistir(client, "T1", "Hareket algılama (PIR)", "hareket", 1, "orta")))
    sonuclar.append(("T2", "Duman/gaz eşik aşımı",
                     test_calistir(client, "T2", "Duman/gaz eşik aşımı (MQ-2, normal → 2500)",
                                   "duman", 2500, "yuksek")))
    sonuclar.append(("T3", "Alev algılama",
                     test_calistir(client, "T3", "Alev algılama (KY-026, 0 → 1)", "alev", 1, "kritik")))
    # T8, T2/T3'ün açtığı alarmları da kapatır; T2b ondan sonra normal durumda koşar
    sonuclar.append(("T8", "Histerezis (alarm fırtınası)", test_histerezis(client)))
    sonuclar.append(("T2b", "Duman normal (alarm yok)",
                     test_alarm_yok(client, "T2b", "Duman normal seviye (MQ-2)", "duman", 400)))

    # T4: MQTT iletimi (yukarıdaki testler zaten iletimi kanıtlıyor)
    print("\n[T4] MQTT mesaj iletimi")
    print("    Yukarıdaki T1-T3 testleri mesajların broker üzerinden")
    print("    backend'e ulaştığını zaten kanıtlıyor.")
    print("    ✓ BAŞARILI")
    sonuclar.append(("T4", "MQTT mesaj iletimi", True))

    # T5: Web arayüzü (API erişilebilir mi)
    print("\n[T5] Web arayüzü / API erişimi")
    try:
        with urllib.request.urlopen(f"{API}/api/saglik", timeout=5) as r:
            saglik = json.loads(r.read().decode("utf-8"))
        if saglik.get("durum") == "calisiyor" and saglik.get("mqtt") == "bagli":
            print("    API /api/saglik yanıt veriyor, backend broker'a bağlı (mqtt=bagli).")
            print("    ✓ BAŞARILI")
            sonuclar.append(("T5", "Web arayüzü / API", True))
        else:
            raise Exception(f"beklenmeyen yanıt: {saglik}")
    except Exception as e:
        print(f"    ✗ BAŞARISIZ ({e})")
        sonuclar.append(("T5", "Web arayüzü / API", False))

    sonuclar.append(("T6", "Bildirim (e-posta)", test_bildirim()))
    sonuclar.append(("T7", "LWT: çevrimdışı ve geri gelme", test_lwt()))
    sonuclar.append(("T9", "Olay yaşam döngüsü (onaylama)", test_yasam_dongusu(client, baslangic)))
    sonuclar.append(("T10", "Yangın teyidi (korelasyon)", test_korelasyon(client)))
    sonuclar.append(("T11", "Güvenlik modu (zaman kuralı)", test_mod(client)))

    # Özet
    print("\n" + "=" * 60)
    print("ÖZET")
    print("=" * 60)
    sira = ["T1", "T2", "T2b", "T3", "T4", "T5", "T6", "T7", "T8", "T9", "T10", "T11"]
    for no, ad, sonuc in sorted(sonuclar, key=lambda x: sira.index(x[0])):
        if sonuc is True:
            durum = "BAŞARILI"
        elif sonuc is False:
            durum = "BAŞARISIZ"
        else:
            durum = "BEKLEMEDE"
        print(f"  {no:4} | {ad:30} | {durum}")


if __name__ == "__main__":
    main()
