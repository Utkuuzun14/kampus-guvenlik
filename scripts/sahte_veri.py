"""
Sahte sensör veri üreteci.
Donanım (ESP32-S2) gelene kadar, kartların yerine broker'a gerçekçi sensör
verisi basar. Böylece backend ve arayüz uçtan uca test edilebilir.
Gerçek kart geldiğinde bu script kapatılır; firmware aynı konulara
aynı formatta yayın yapacağı için sistemin geri kalanı değişmez.

Her düğüm ayrı bir thread'de, kendi MQTT client'ı ve kendi LWT'si ile çalışır:
  - dugum1 (Mühendislik Fakültesi): arada duman eşik aşımı ve alev
  - dugum2 (Kütüphane): sakin; sık hareket, düşük duman, nadiren eşik aşımı
  - dugum3 (Yurtlar): 3-5 dk'da bir bağlantısı kopar (LWT tetiklenir),
    30-60 sn sonra geri bağlanıp "online" yayınlar

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

# Düğüm profilleri: olasılıklar her yayın turu için
PROFILLER = {
    "dugum1": {"duman_normal": (200, 800), "duman_alarm": (1900, 3500), "p_duman_alarm": 0.15,
               "p_hareket": 0.25, "p_alev": 0.05, "kopma": None},
    "dugum2": {"duman_normal": (150, 500), "duman_alarm": (1850, 2400), "p_duman_alarm": 0.02,
               "p_hareket": 0.60, "p_alev": 0.0, "kopma": None},
    # kopma: (bağlı kalma sn aralığı, kopuk kalma sn aralığı)
    "dugum3": {"duman_normal": (200, 700), "duman_alarm": (1900, 2800), "p_duman_alarm": 0.05,
               "p_hareket": 0.30, "p_alev": 0.0, "kopma": ((180, 300), (30, 60))},
}

_yazdir_kilit = threading.Lock()


def log(dugum, metin):
    with _yazdir_kilit:
        print(f"[{dugum}] {metin}", flush=True)


def _konu(dugum, sensor):
    return f"kampus/guvenlik/{dugum}/{sensor}"


def istemci_olustur(dugum, client_id=None):
    """
    LWT'si kurulmuş, bağlı ve döngüsü çalışan bir client döndürür.
    LWT yükü bağlanırken sabitlendiği için zaman=0 gönderilir; backend
    mesaj geldiği anın zamanını yazar (docs/SOZLESMELER.md §3).
    """
    client = mqtt.Client(
        client_id=client_id or f"sahte-{dugum}",
        protocol=mqtt.MQTTv5,
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    )
    client.username_pw_set(config.MQTT_KULLANICI, config.MQTT_PAROLA)
    client.will_set(_konu(dugum, "durum"),
                    json.dumps({"dugum": dugum, "durum": "offline", "zaman": 0}), qos=1)
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


class SahteDugum(threading.Thread):
    def __init__(self, dugum, profil, dur):
        super().__init__(name=dugum, daemon=True)
        self.dugum = dugum
        self.p = profil
        self.dur = dur  # threading.Event: Ctrl+C
        self.client = None

    def yayinla(self, sensor, deger):
        mesaj = {"dugum": self.dugum, "sensor": sensor, "deger": deger, "zaman": int(time.time())}
        self.client.publish(_konu(self.dugum, sensor), json.dumps(mesaj, ensure_ascii=False), qos=1)
        log(self.dugum, f"-> {sensor}={deger}")

    def baglan(self):
        self.client = istemci_olustur(self.dugum)
        durum_yayinla(self.client, self.dugum, online=True)
        log(self.dugum, "bağlandı, online yayınlandı")

    def tur(self):
        p = self.p
        if random.random() < p["p_duman_alarm"]:
            duman = random.randint(*p["duman_alarm"])
        else:
            duman = random.randint(*p["duman_normal"])
        self.yayinla("duman", duman)
        if random.random() < p["p_hareket"]:
            self.yayinla("hareket", 1)
        if random.random() < p["p_alev"]:
            self.yayinla("alev", 1)

    def run(self):
        self.baglan()
        kopma_zamani = None
        if self.p["kopma"]:
            kopma_zamani = time.monotonic() + random.uniform(*self.p["kopma"][0])

        while not self.dur.is_set():
            self.tur()
            if kopma_zamani and time.monotonic() >= kopma_zamani:
                bekle = random.uniform(*self.p["kopma"][1])
                baglantiyi_kopar(self.client)
                log(self.dugum, f"bağlantı koptu (LWT bekleniyor), {bekle:.0f} sn sonra geri bağlanacak")
                if self.dur.wait(bekle):
                    return  # kopukken durduruldu; LWT zaten offline bildirdi
                self.baglan()
                kopma_zamani = time.monotonic() + random.uniform(*self.p["kopma"][0])
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
