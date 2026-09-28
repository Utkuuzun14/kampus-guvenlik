"""
Sahte sensör veri üreteci.
Donanım (ESP32-S2) gelene kadar, kartın yerine broker'a gerçekçi sensör
verisi basar. Böylece backend ve arayüz uçtan uca test edilebilir.
Gerçek kart geldiğinde bu script kapatılır; firmware aynı konulara
aynı formatta yayın yapacağı için sistemin geri kalanı değişmez.

Çalıştırma (backend venv aktifken, proje kökünden):
    python scripts/sahte_veri.py
"""
import json
import time
import random
import sys
import os

import paho.mqtt.client as mqtt

# backend/app/config.py'deki ayarları kullanmak için yol ekle
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from app import config  # noqa: E402

DUGUM = "dugum1"
YAYIN_ARALIGI = 3  # saniye (kaç saniyede bir okuma yayınlanır)


def istemci_olustur():
    client = mqtt.Client(
        client_id="sahte-sensor",
        protocol=mqtt.MQTTv5,
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    )
    client.username_pw_set(config.MQTT_KULLANICI, config.MQTT_PAROLA)
    client.connect(config.MQTT_HOST, config.MQTT_PORT, keepalive=60)
    return client


def yayinla(client, sensor, deger):
    konu = f"kampus/guvenlik/{DUGUM}/{sensor}"
    mesaj = {
        "dugum": DUGUM,
        "sensor": sensor,
        "deger": deger,
        "zaman": int(time.time()),
    }
    client.publish(konu, json.dumps(mesaj, ensure_ascii=False), qos=1)
    print(f"-> {konu}: {mesaj}")


def durum_yayinla(client, online=True):
    konu = f"kampus/guvenlik/{DUGUM}/durum"
    mesaj = {
        "dugum": DUGUM,
        "durum": "online" if online else "offline",
        "zaman": int(time.time()),
    }
    client.publish(konu, json.dumps(mesaj, ensure_ascii=False), qos=1)
    print(f"-> {konu}: {mesaj}")


def main():
    client = istemci_olustur()
    client.loop_start()
    print("[SAHTE] Baglandi, veri uretiliyor... (Ctrl+C ile cik)")

    # Baslangicta cihaz online bildir
    durum_yayinla(client, online=True)

    try:
        while True:
            # --- Duman: cogunlukla normal, arada yuksek ---
            # %85 normal (200-800), %15 alarm (1900-3500)
            if random.random() < 0.15:
                duman = random.randint(1900, 3500)
            else:
                duman = random.randint(200, 800)
            yayinla(client, "duman", duman)

            # --- Hareket: %25 ihtimalle hareket var ---
            hareket = 1 if random.random() < 0.25 else 0
            if hareket == 1:
                yayinla(client, "hareket", 1)

            # --- Alev: nadiren (%5) ---
            if random.random() < 0.05:
                yayinla(client, "alev", 1)

            time.sleep(YAYIN_ARALIGI)

    except KeyboardInterrupt:
        print("\n[SAHTE] Durduruluyor, cihaz offline bildiriliyor...")
        durum_yayinla(client, online=False)
        time.sleep(0.5)
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
