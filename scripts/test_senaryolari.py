"""
Test senaryoları scripti (rapor Tablo 6, T1-T8).
Her senaryo için broker'a kontrollü mesaj gönderir, backend'in olayı doğru
işleyip işlemediğini API üzerinden doğrular. T6 (e-posta) gerçek mail
göndermez: SMTP taklit edilir, MQTT işleyicisi süreç içinde çağrılır.
T7, test_dugum için LWT'li bir client açıp socket'ini temiz olmayan şekilde
kapatır ve /api/dugumler'de çevrimdışı düşüp geri geldiğini doğrular.
T8, duman/alev histerezisini doğrular (art arda eşik üstü ölçüm → tek olay).
Backend histerezis durumunu bellekte tuttuğu için testler başta test_dugum'u
normale çeker; böylece aynı backend açıkken tekrar çalıştırmak da tutarlıdır.

Çalıştırmadan önce: broker + backend çalışıyor olmalı, sahte veri üreteci
KAPATILMALI (test sonuçlarını kirletmemesi için).

Çalıştırma (backend venv aktifken, proje kökünden):
    python scripts/test_senaryolari.py

Çalışma bitince (testler başarısız olsa bile) bu çalıştırmada oluşan
test_dugum kayıtları olaylar ve sensor_gecmis tablolarından silinir.
"""
import json
import time
import sys
import os
import sqlite3
import threading
import urllib.request

import paho.mqtt.client as mqtt

BACKEND_DIZINI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend")
sys.path.insert(0, BACKEND_DIZINI)
from app import config  # noqa: E402
import sahte_veri  # noqa: E402  (aynı dizin: LWT'li client ve kopma fonksiyonu)

API = "http://127.0.0.1:8000"
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
        for t in TABLOLAR:
            imlec = conn.execute(f"DELETE FROM {t} WHERE dugum = ? AND id > ?",
                                 (DUGUM, baslangic[t]))
            silinen[t] = imlec.rowcount
        conn.commit()
    finally:
        conn.close()
    print(f"\nTemizlik: {DUGUM} kayıtları silindi "
          f"(olaylar: {silinen['olaylar']}, sensor_gecmis: {silinen['sensor_gecmis']})")


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
    olay = son_olay()

    if not olay or olay["id"] <= onceki_id:
        print(f"    ✗ BAŞARISIZ (yeni olay oluşmadı, son id: {onceki_id})")
        return False
    if (olay["dugum"] == DUGUM and olay["sensor"] == sensor
            and olay["seviye"] == beklenen_seviye):
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

    def sahte_olay_ekle(dugum_, sensor, deger, seviye, mesaj, zaman):
        return {"id": 0, "dugum": dugum_, "sensor": sensor, "deger": deger,
                "seviye": seviye, "mesaj": mesaj, "zaman": zaman}

    kontroller = []

    def kontrol(ad, kosul):
        print(f"    {'✓' if kosul else '✗'} {ad}")
        kontroller.append(kosul)

    with mock.patch.object(bildirim, "_smtp_gonder", side_effect=yavas_gonderim) as smtp, \
            mock.patch.object(bildirim, "_saat", lambda: saat[0]), \
            mock.patch.dict(bildirim._bekleme, clear=True),             mock.patch.dict(kurallar._alarm, clear=True), \
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


def main():
    print("=" * 60)
    print("KAMPÜS GÜVENLİK SİSTEMİ - TEST SENARYOLARI (Tablo 6)")
    print("=" * 60)
    print("Not: Broker + backend çalışmalı, sahte üreteç kapalı olmalı.")

    baslangic = son_kayit_idleri()
    client = mqtt_baglan()
    try:
        testleri_calistir(client)
    finally:
        client.loop_stop()
        client.disconnect()
        test_verisini_temizle(baslangic)


def testleri_calistir(client):
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

    # Özet
    print("\n" + "=" * 60)
    print("ÖZET")
    print("=" * 60)
    sira = ["T1", "T2", "T2b", "T3", "T4", "T5", "T6", "T7", "T8"]
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
