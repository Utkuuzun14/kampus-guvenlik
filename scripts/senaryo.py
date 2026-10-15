"""
Demo senaryoları. Çalışan sahte üretecin yanında ayrı bir komutla tetiklenir;
sensör verisini düğüm adına, sözleşmedeki formatta MQTT'ye yayınlar.

Senaryo süresince üreteç o düğüm için ölçüm yayınlamayı duraklatır (demo
kontrol konusu kampus/demo/<dugum>/senaryo), böylece paneldeki değerler
karışmaz. Üreteç çalışmıyorsa yangın ve hareket senaryoları yine çalışır.

Çalıştırma (backend venv aktifken, proje kökünden):
    python scripts/senaryo.py yangin dugum1    # duman eşiği aşar → 3 sn sonra alev → YANGIN TEYİTLİ
    python scripts/senaryo.py hareket dugum2   # izinsiz giriş: art arda hareket (seviye moda göre)
    python scripts/senaryo.py hareket dugum2 --mod gece   # modu gece yapar (yüksek), sonra geri alır
    python scripts/senaryo.py kopma dugum3     # LWT ile düşer, 30 sn sonra geri gelir

--mod API'ye giriş yapar: backend/.env'de SENARYO_KULLANICI ve SENARYO_PAROLA
(admin rolünde bir kullanıcı) tanımlı olmalı. MQTT senaryoları giriş istemez.
"""
import argparse
import json
import os
import random
import sys
import threading
import time
import urllib.error
import urllib.request

import paho.mqtt.client as mqtt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
from app import config  # noqa: E402
import sahte_veri as sv  # noqa: E402

ADIM = sv.YAYIN_ARALIGI  # 3 sn, üreteçle aynı ölçüm aralığı
API = "http://127.0.0.1:8000"
MODLAR = ("otomatik", "mesai", "mesai_disi", "gece")


class GirisHatasi(Exception):
    """--mod için API girişi yapılamadı; mesaj kullanıcıya gösterilir."""


def _json_istek(yol, yontem="GET", govde=None, token=None):
    basliklar = {"Content-Type": "application/json"}
    if token:
        basliklar["Authorization"] = f"Bearer {token}"
    veri = None if govde is None else json.dumps(govde).encode("utf-8")
    istek = urllib.request.Request(f"{API}{yol}", data=veri, method=yontem, headers=basliklar)
    with urllib.request.urlopen(istek, timeout=5) as r:
        return json.loads(r.read().decode("utf-8"))


def giris_tokeni():
    """backend/.env'deki SENARYO_KULLANICI / SENARYO_PAROLA ile giriş yapar."""
    kullanici = os.getenv("SENARYO_KULLANICI", "").strip()
    parola = os.getenv("SENARYO_PAROLA", "")
    if not kullanici or not parola:
        raise GirisHatasi("--mod için backend/.env'e şunları ekle (admin rolünde bir kullanıcı):\n"
                          "    SENARYO_KULLANICI=<kullanıcı adı>\n"
                          "    SENARYO_PAROLA=<parola>\n"
                          "Kullanıcı yoksa: python scripts/kullanici_ekle.py")
    try:
        return _json_istek("/api/giris", "POST",
                           {"kullanici_adi": kullanici, "parola": parola})["token"]
    except urllib.error.HTTPError as e:
        if e.code == 429:
            raise GirisHatasi("Çok fazla hatalı giriş denemesi; 1 dk sonra tekrar deneyin.") from None
        raise GirisHatasi(f"Giriş başarısız (HTTP {e.code}): SENARYO_KULLANICI / SENARYO_PAROLA "
                          "hatalı ya da kullanıcı pasif.") from None


def mod_istek(token, mod=None):
    """mod=None: GET, verilirse PUT /api/ayarlar/mod. Yanıt gövdesi (dict)."""
    try:
        if mod is None:
            return _json_istek("/api/ayarlar/mod", token=token)
        return _json_istek("/api/ayarlar/mod", "PUT", {"mod": mod}, token)
    except urllib.error.HTTPError as e:
        if e.code == 403:
            raise GirisHatasi("SENARYO_KULLANICI admin değil; modu yalnızca admin "
                              "değiştirebilir (HTTP 403).") from None
        raise


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
          f"{ADIM} sn sonra alev (korelasyon penceresi {config.KORELASYON_PENCERE_SN} sn → "
          f"YANGIN TEYİTLİ); 60 sn sonra normale dönecek.")
    kontrol(client, dugum, "duraklat", sure=150)
    try:
        # 1) 30 sn kademeli yükseliş: 10 ölçüm, ~450 → ~2600. İlk 9 ölçüm eşiğin
        #    altında kalır, eşik SON ölçümde aşılır; alev bir adım (3 sn) sonra
        #    geldiği için korelasyon penceresine rahatça girer.
        tavan = config.ESIK_DUMAN - 150
        for i in range(9):
            olcum(client, dugum, min(int(450 + i * 145 + random.randint(-40, 40)), tavan))
        olcum(client, dugum, config.ESIK_DUMAN + random.randint(600, 900))
        # 2) Alev (kritik) + 60 sn yüksek duman. alev=1 bir kez yayınlanır
        #    (tek kritik olay); panelde son ölçüm söndürülene kadar "VAR" kalır.
        print("  ALEV ALGILANDI (kritik) → yangın teyidi bekleniyor", flush=True)
        for i in range(60 // ADIM):
            olcum(client, dugum, random.randint(2700, 3200), alev=1 if i == 0 else None)
        # 3) Normale dönüş
        print("  söndürüldü, normale dönülüyor", flush=True)
        for duman in (1500, 900, 520):
            olcum(client, dugum, duman)
    finally:
        kontrol(client, dugum, "devam")


def hareket(client, dugum):
    print(f"[izinsiz giriş] {dugum}: art arda hareket algılanacak "
          f"(seviye güvenlik moduna göre: mesai bilgi, mesai dışı orta, gece yüksek).")
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
    ap.add_argument("--mod", choices=MODLAR,
                    help="hareket: senaryo süresince güvenlik modu (sonunda eski moda döner)")
    arg = ap.parse_args()
    if arg.mod and arg.senaryo != "hareket":
        ap.error("--mod yalnızca hareket senaryosunda kullanılır")

    onceki_mod = token = None
    if arg.mod:
        try:
            token = giris_tokeni()
            onceki_mod = mod_istek(token)["mod"]
            bilgi = mod_istek(token, arg.mod)
        except GirisHatasi as e:
            print(f"[senaryo] {e}")
            return 1
        except (urllib.error.URLError, OSError) as e:
            print(f"[senaryo] Güvenlik modu ayarlanamadı ({e}). Backend çalışıyor mu?")
            return 1
        print(f"[senaryo] Güvenlik modu: {onceki_mod} → {arg.mod} ({bilgi['aciklama']})")

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
        if onceki_mod:
            try:
                mod_istek(token, onceki_mod)
                print(f"[senaryo] Güvenlik modu geri alındı: {onceki_mod}")
            except (GirisHatasi, urllib.error.URLError, OSError) as e:
                print(f"[senaryo] Mod geri alınamadı ({e}); panelden {onceki_mod} seçin.")
    if sonuc == 0:
        print("[senaryo] tamamlandı.")
    return sonuc


if __name__ == "__main__":
    sys.exit(main())
