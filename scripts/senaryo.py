"""
Demo senaryoları. Çalışan sahte üretecin yanında ayrı bir komutla tetiklenir;
sensör verisini düğüm adına, sözleşmedeki formatta MQTT'ye yayınlar.

Senaryo süresince üreteç o düğüm için ölçüm yayınlamayı duraklatır (demo
kontrol konusu kampus/demo/<dugum>/senaryo), böylece paneldeki değerler
karışmaz. Üreteç çalışmıyorsa yangın ve hareket senaryoları yine çalışır.

Çalıştırma (backend venv aktifken, proje kökünden):
    python scripts/senaryo.py yangin dugum1    # duman yükselir → alev (kritik) → normale döner
    python scripts/senaryo.py hareket dugum2   # gece izinsiz giriş: art arda hareket
    python scripts/senaryo.py kopma dugum3     # LWT ile düşer, 30 sn sonra geri gelir
"""
import argparse
import json
import os
import random
import sys
import threading
import time

import paho.mqtt.client as mqtt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
from app import config  # noqa: E402
import sahte_veri as sv  # noqa: E402

ADIM = sv.YAYIN_ARALIGI  # 3 sn, üreteçle aynı ölçüm aralığı


def baglan():
    client = mqtt.Client(
        client_id=f"senaryo-{random.randint(1000, 9999)}",
        protocol=mqtt.MQTTv5,
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    )
    client.username_pw_set(config.MQTT_KULLANICI, config.MQTT_PAROLA)
    client.connect(config.MQTT_HOST, config.MQTT_PORT, keepalive=60)
    client.loop_start()
    return client


def kontrol(client, dugum, komut, **alanlar):
    yuk = json.dumps({"komut": komut, **alanlar})
    client.publish(sv.KONTROL_KONU.format(dugum=dugum), yuk, qos=1).wait_for_publish(3)


def olcum(client, dugum, duman, hareket=0, alev=0):
    """
    Üreteçle aynı biçimde tek turluk ölçüm (duman, hareket, alev).
    alev=None: alev ölçümü yayınlanmaz (son ölçüm olduğu gibi kalır).
    """
    for sensor, deger in (("duman", duman), ("hareket", hareket), ("alev", alev)):
        if deger is not None:
            sv.olcum_yayinla(client, dugum, sensor, deger)
    isaret = " (eşik üstü)" if duman > config.ESIK_DUMAN else ""
    alev_metin = "" if alev is None else f"  alev={alev}"
    print(f"  {time.strftime('%H:%M:%S')}  duman={duman}{isaret}  hareket={hareket}{alev_metin}",
          flush=True)
    time.sleep(ADIM)


def yangin(client, dugum):
    print(f"[yangın] {dugum}: duman 30 sn'de yükselip eşiği ({config.ESIK_DUMAN}) aşacak, "
          f"ardından alev; 60 sn sonra normale dönecek.")
    kontrol(client, dugum, "duraklat", sure=150)
    try:
        # 1) 30 sn kademeli yükseliş: 10 ölçüm, ~450 → ~2600
        for i in range(10):
            olcum(client, dugum, int(450 + i * 240 + random.randint(-40, 40)))
        # 2) Alev (kritik) + 60 sn yüksek duman. alev=1 bir kez yayınlanır
        #    (tek kritik olay); panelde son ölçüm söndürülene kadar "VAR" kalır.
        print("  ALEV ALGILANDI (kritik)", flush=True)
        for i in range(60 // ADIM):
            olcum(client, dugum, random.randint(2700, 3200), alev=1 if i == 0 else None)
        # 3) Normale dönüş
        print("  söndürüldü, normale dönülüyor", flush=True)
        for duman in (1500, 900, 520):
            olcum(client, dugum, duman)
    finally:
        kontrol(client, dugum, "devam")


def hareket(client, dugum):
    print(f"[izinsiz giriş] {dugum}: gece saatlerinde art arda hareket algılanacak.")
    kontrol(client, dugum, "duraklat", sure=60)
    try:
        for _ in range(8):
            olcum(client, dugum, random.randint(150, 400), hareket=1)
        olcum(client, dugum, random.randint(150, 400), hareket=0)
    finally:
        kontrol(client, dugum, "devam")


def kopma(client, dugum, sure=30):
    """Üreteçteki düğümü LWT ile düşürür; düşüşü ve geri gelişi broker'dan izler."""
    print(f"[kopma] {dugum}: bağlantı LWT ile düşürülecek, {sure} sn sonra geri gelecek.")
    gelen = {"offline": threading.Event(), "online": threading.Event()}

    def on_message(c, userdata, msg):
        durum = json.loads(msg.payload.decode("utf-8")).get("durum")
        if durum in gelen:
            gelen[durum].set()

    client.on_message = on_message
    client.subscribe(f"kampus/guvenlik/{dugum}/durum", 1)
    time.sleep(0.5)
    kontrol(client, dugum, "kopma", sure=sure)

    if not gelen["offline"].wait(10):
        print(f"  ✗ 10 sn içinde LWT gelmedi. Üreteç çalışıyor ve {dugum} içeriyor mu?")
        return 1
    print(f"  {time.strftime('%H:%M:%S')}  broker LWT yayınladı: {dugum} çevrimdışı", flush=True)
    if not gelen["online"].wait(sure + 15):
        print(f"  ✗ {sure + 15} sn içinde geri bağlanmadı.")
        return 1
    print(f"  {time.strftime('%H:%M:%S')}  {dugum} geri bağlandı (online)", flush=True)
    return 0


def main():
    ap = argparse.ArgumentParser(description="Demo senaryoları")
    ap.add_argument("senaryo", choices=["yangin", "hareket", "kopma"])
    ap.add_argument("dugum", help="ör. dugum1")
    ap.add_argument("--sure", type=int, default=30, help="kopma süresi (sn, varsayılan 30)")
    arg = ap.parse_args()

    client = baglan()
    try:
        if arg.senaryo == "yangin":
            yangin(client, arg.dugum)
            sonuc = 0
        elif arg.senaryo == "hareket":
            hareket(client, arg.dugum)
            sonuc = 0
        else:
            sonuc = kopma(client, arg.dugum, arg.sure)
    except KeyboardInterrupt:
        print("\n[senaryo] durduruldu, üreteç yayına döndü.")
        sonuc = 1
    finally:
        client.disconnect()
        client.loop_stop()
    if sonuc == 0:
        print("[senaryo] tamamlandı.")
    return sonuc


if __name__ == "__main__":
    sys.exit(main())
