"""
Sahte sensör veri üreteci.
Donanım (ESP32-S2) gelene kadar, kartların yerine broker'a gerçekçi sensör
verisi basar. Böylece backend ve arayüz uçtan uca test edilebilir.
Gerçek kart geldiğinde bu script kapatılır; firmware aynı konulara
aynı formatta yayın yapacağı için sistemin geri kalanı değişmez.

Her düğüm ayrı bir thread'de, kendi MQTT client'ı ve kendi LWT'si ile çalışır.
Varsayılan davranış sakindir; dikkat çekici olaylar scripts/senaryo.py ile
tetiklenir:
  - Her 3 sn'de duman, hareket (0/1) ve alev (0) ölçümü yayınlanır; böylece
    paneldeki "son ölçüm" gerçekten son durumu gösterir.
  - Alev kendiliğinden üretilmez (yalnızca senaryo ile).
  - Duman eşik aşımı düğüm başına ~10-15 dk'da bir, 2-3 ölçümlük kısa bir tepe.
  - dugum1 (Mühendislik Fakültesi): orta yoğunlukta hareket
  - dugum2 (Kütüphane): sık hareket, düşük duman
  - dugum3 (Yurtlar): 3-5 dk'da bir bağlantısı kopar (LWT tetiklenir),
    30-60 sn sonra geri bağlanıp "online" yayınlar

Demo kontrolü: her düğüm kampus/demo/<dugum>/senaryo konusunu dinler
(backend bu konuyu dinlemez):
  {"komut": "duraklat", "sure": 120}  → düğüm o süre ölçüm yayınlamaz
  {"komut": "devam"}                 → yayına hemen döner
  {"komut": "kopma", "sure": 30}      → LWT ile düşer, süre sonunda geri bağlanır

Çalıştırma (backend venv aktifken, proje kökünden):
    python scripts/sahte_veri.py                      # üç düğüm
    python scripts/sahte_veri.py --dugumler dugum1,dugum2
"""
import argparse
import json
import time
import random
import sys
import os
import threading

import paho.mqtt.client as mqtt

# backend/app/config.py'deki ayarları kullanmak için yol ekle
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from app import config  # noqa: E402

YAYIN_ARALIGI = 3  # saniye (kaç saniyede bir okuma yayınlanır)
# Duman eşik aşımı: iki tepe arası (sn) ve tepenin süresi (ölçüm sayısı)
DUMAN_TEPE_ARALIGI = (600, 900)
DUMAN_TEPE_OLCUM = (2, 3)
KONTROL_KONU = "kampus/demo/{dugum}/senaryo"

# Düğüm profilleri. p_hareket: her 3 sn'lik turda hareket=1 olasılığı.
PROFILLER = {
    "dugum1": {"duman_normal": (200, 800), "duman_alarm": (1900, 3000),
               "p_hareket": 0.25, "kopma": None},
    "dugum2": {"duman_normal": (150, 500), "duman_alarm": (1850, 2400),
               "p_hareket": 0.60, "kopma": None},
    # kopma: (bağlı kalma sn aralığı, kopuk kalma sn aralığı)
    "dugum3": {"duman_normal": (200, 700), "duman_alarm": (1900, 2800),
               "p_hareket": 0.30, "kopma": ((180, 300), (30, 60))},
}

_yazdir_kilit = threading.Lock()


def log(dugum, metin):
    with _yazdir_kilit:
        print(f"[{dugum}] {metin}", flush=True)


def _konu(dugum, sensor):
    return f"kampus/guvenlik/{dugum}/{sensor}"


def istemci_olustur(dugum, client_id=None, kontrol=None):
    """
    LWT'si kurulmuş, bağlı ve döngüsü çalışan bir client döndürür.
    LWT yükü bağlanırken sabitlendiği için zaman=0 gönderilir; backend
    mesaj geldiği anın zamanını yazar (docs/SOZLESMELER.md §3).
    kontrol verilirse demo kontrol konusu dinlenir: kontrol(komut_dict).
    """
    client = mqtt.Client(
        client_id=client_id or f"sahte-{dugum}",
        protocol=mqtt.MQTTv5,
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    )
    client.username_pw_set(config.MQTT_KULLANICI, config.MQTT_PAROLA)
    client.will_set(_konu(dugum, "durum"),
                    json.dumps({"dugum": dugum, "durum": "offline", "zaman": 0}), qos=1)
    if kontrol:
        konu = KONTROL_KONU.format(dugum=dugum)

        def on_connect(c, userdata, flags, reason_code, properties):
            if reason_code == 0:
                c.subscribe(konu, 1)

        def on_message(c, userdata, msg):
            try:
                kontrol(json.loads(msg.payload.decode("utf-8")))
            except Exception as e:
                log(dugum, f"kontrol mesajı işlenemedi: {e}")

        client.on_connect = on_connect
        client.on_message = on_message
    client.connect(config.MQTT_HOST, config.MQTT_PORT, keepalive=60)
    client.loop_start()
    return client


def baglantiyi_kopar(client):
    """
    Temiz olmayan kopma: DISCONNECT paketi göndermeden socket'i kapatır.
    Broker bunu beklenmedik kopma sayar ve düğümün LWT'sini yayınlar.
    """
    client.loop_stop()
    sock = client.socket()
    if sock is not None:
        sock.close()


def durum_yayinla(client, dugum, online=True):
    mesaj = {"dugum": dugum, "durum": "online" if online else "offline", "zaman": int(time.time())}
    return client.publish(_konu(dugum, "durum"), json.dumps(mesaj, ensure_ascii=False), qos=1)


def olcum_yayinla(client, dugum, sensor, deger):
    mesaj = {"dugum": dugum, "sensor": sensor, "deger": deger, "zaman": int(time.time())}
    return client.publish(_konu(dugum, sensor), json.dumps(mesaj, ensure_ascii=False), qos=1)


class SahteDugum(threading.Thread):
    def __init__(self, dugum, profil, dur):
        super().__init__(name=dugum, daemon=True)
        self.dugum = dugum
        self.p = profil
        self.dur = dur  # threading.Event: Ctrl+C
        self.client = None
        # Demo kontrolü (MQTT thread'inden yazılır, düğüm thread'inden okunur)
        self.duraklat_bitis = 0.0
        self.kopma_istegi = None
        # Duman tepesi planı
        self.tepe_zamani = time.monotonic() + random.uniform(*DUMAN_TEPE_ARALIGI)
        self.tepe_kalan = 0

    def kontrol(self, komut):
        tur = komut.get("komut")
        if tur == "duraklat":
            sure = float(komut.get("sure", 60))
            self.duraklat_bitis = time.monotonic() + sure
            log(self.dugum, f"senaryo: {sure:.0f} sn duraklatıldı")
        elif tur == "devam":
            self.duraklat_bitis = 0.0
            log(self.dugum, "senaryo: yayına dönüldü")
        elif tur == "kopma":
            self.kopma_istegi = float(komut.get("sure", 30))
            log(self.dugum, f"senaryo: kopma istendi ({self.kopma_istegi:.0f} sn)")

    def baglan(self):
        self.client = istemci_olustur(self.dugum, kontrol=self.kontrol)
        durum_yayinla(self.client, self.dugum, online=True)
        log(self.dugum, "bağlandı, online yayınlandı")

    def duman_uret(self):
        if self.tepe_kalan == 0 and time.monotonic() >= self.tepe_zamani:
            self.tepe_kalan = random.randint(*DUMAN_TEPE_OLCUM)
            self.tepe_zamani = time.monotonic() + random.uniform(*DUMAN_TEPE_ARALIGI)
        if self.tepe_kalan:
            self.tepe_kalan -= 1
            return random.randint(*self.p["duman_alarm"])
        return random.randint(*self.p["duman_normal"])

    def tur(self):
        duman = self.duman_uret()
        hareket = 1 if random.random() < self.p["p_hareket"] else 0
        for sensor, deger in (("duman", duman), ("hareket", hareket), ("alev", 0)):
            olcum_yayinla(self.client, self.dugum, sensor, deger)
        isaret = " (eşik üstü)" if duman > config.ESIK_DUMAN else ""
        log(self.dugum, f"-> duman={duman}{isaret} hareket={hareket} alev=0")

    def kopma(self, bekle):
        baglantiyi_kopar(self.client)
        log(self.dugum, f"bağlantı koptu (LWT bekleniyor), {bekle:.0f} sn sonra geri bağlanacak")
        if self.dur.wait(bekle):
            return False  # kopukken durduruldu; LWT zaten offline bildirdi
        self.baglan()
        return True

    def run(self):
        self.baglan()
        kopma_zamani = None
        if self.p["kopma"]:
            kopma_zamani = time.monotonic() + random.uniform(*self.p["kopma"][0])

        while not self.dur.is_set():
            istek, self.kopma_istegi = self.kopma_istegi, None
            if istek is not None or (kopma_zamani and time.monotonic() >= kopma_zamani):
                bekle = istek if istek is not None else random.uniform(*self.p["kopma"][1])
                if not self.kopma(bekle):
                    return
                if kopma_zamani:
                    kopma_zamani = time.monotonic() + random.uniform(*self.p["kopma"][0])
            elif time.monotonic() >= self.duraklat_bitis:
                self.tur()
            self.dur.wait(YAYIN_ARALIGI)

        # Temiz kapanış: offline bildir, DISCONNECT gönder (LWT tetiklenmez)
        durum_yayinla(self.client, self.dugum, online=False).wait_for_publish(2)
        self.client.disconnect()
        self.client.loop_stop()
        log(self.dugum, "offline bildirildi, kapatıldı")


def main():
    ap = argparse.ArgumentParser(description="Sahte sensör düğümleri")
    ap.add_argument("--dugumler", default=",".join(PROFILLER),
                    help=f"virgülle ayrılmış düğümler (varsayılan: {','.join(PROFILLER)})")
    secilen = [d.strip() for d in ap.parse_args().dugumler.split(",") if d.strip()]
    bilinmeyen = [d for d in secilen if d not in PROFILLER]
    if bilinmeyen or not secilen:
        ap.error(f"bilinmeyen düğüm: {', '.join(bilinmeyen) or '(boş)'}; seçenekler: {', '.join(PROFILLER)}")

    dur = threading.Event()
    dugumler = [SahteDugum(d, PROFILLER[d], dur) for d in secilen]
    for d in dugumler:
        d.start()
    print(f"[SAHTE] {', '.join(secilen)} veri üretiyor... (Ctrl+C ile çık)", flush=True)

    try:
        while any(d.is_alive() for d in dugumler):
            time.sleep(0.5)  # Windows'ta Ctrl+C'nin ana thread'e ulaşması için
    except KeyboardInterrupt:
        print("\n[SAHTE] Durduruluyor...", flush=True)
        dur.set()
        for d in dugumler:
            d.join(5)


if __name__ == "__main__":
    main()
