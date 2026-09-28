"""
MQTT dinleyici.
Broker'a bağlanır, sensör konularına abone olur, gelen JSON mesajları
kural motoruyla değerlendirir ve veritabanına kaydeder.
paho-mqtt 2.x callback API'si kullanılır.
"""
import json
import time
import threading
import paho.mqtt.client as mqtt

from app import config, kurallar, veritabani

# Yeni bir olay oluştuğunda haber verilecek dış fonksiyon (main.py bağlayacak).
# WebSocket ile React'e canlı iletim için kullanılacak. Şimdilik None.
olay_geri_cagirma = None


def _dugum_cikar(topic):
    """kampus/guvenlik/<dugum>/<sensor> -> (dugum, sensor)"""
    parcalar = topic.split("/")
    if len(parcalar) >= 4:
        return parcalar[2], parcalar[3]
    return "bilinmeyen", "bilinmeyen"


def _on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print("[MQTT] Broker'a bağlanıldı.")
        for konu, qos in config.MQTT_KONULAR:
            client.subscribe(konu, qos)
            print(f"[MQTT] Abone olundu: {konu} (QoS {qos})")
    else:
        print(f"[MQTT] Bağlantı hatası, kod: {reason_code}")


def _on_message(client, userdata, msg):
    """Her gelen mesajda çalışır."""
    try:
        veri = json.loads(msg.payload.decode("utf-8"))
    except Exception as e:
        print(f"[MQTT] JSON çözülemedi: {msg.payload!r} ({e})")
        return

    dugum, sensor = _dugum_cikar(msg.topic)
    # durum mesajlarında alan adı 'durum', diğerlerinde 'deger'
    if sensor == "durum":
        durum_metin = veri.get("durum", "online")
        deger = 1 if durum_metin == "online" else 0
    else:
        deger = veri.get("deger", 0)
    zaman = veri.get("zaman") or int(time.time())

    # Ham okumayı geçmişe yaz (trend için)
    try:
        veritabani.gecmis_ekle(dugum, sensor, deger, zaman)
    except Exception as e:
        print(f"[DB] gecmis_ekle hatası: {e}")

    # Kural motoruyla değerlendir
    alarm_var, seviye, mesaj = kurallar.degerlendir(sensor, deger)

    print(f"[OLAY] {dugum}/{sensor} deger={deger} -> {seviye}: {mesaj}")

    if alarm_var:
        try:
            olay = veritabani.olay_ekle(dugum, sensor, deger, seviye, mesaj, zaman)
        except Exception as e:
            print(f"[DB] olay_ekle hatası: {e}")
            return

        # Alarm konusuna yayınla (backend -> .../alarm)
        try:
            alarm_konu = config.MQTT_ALARM_KONU_SABLON.format(dugum=dugum)
            client.publish(alarm_konu, json.dumps({
                "seviye": seviye, "mesaj": mesaj, "zaman": zaman
            }), qos=1)
        except Exception as e:
            print(f"[MQTT] alarm yayın hatası: {e}")

        # main.py bağladıysa canlı iletim (WebSocket)
        if olay_geri_cagirma:
            try:
                olay_geri_cagirma(olay)
            except Exception as e:
                print(f"[WS] geri çağırma hatası: {e}")


def istemci_olustur():
    """Yapılandırılmış bir MQTT istemcisi döndürür (bağlanmadan)."""
    client = mqtt.Client(
        client_id="kampus-backend",
        protocol=mqtt.MQTTv5,
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    )
    client.username_pw_set(config.MQTT_KULLANICI, config.MQTT_PAROLA)
    client.on_connect = _on_connect
    client.on_message = _on_message
    return client


def baslat_arka_planda():
    """
    MQTT döngüsünü ayrı bir thread'de başlatır ki FastAPI ana thread'i
    bloke olmasın. İstemciyi döndürür.
    """
    client = istemci_olustur()
    client.connect(config.MQTT_HOST, config.MQTT_PORT, keepalive=60)
    t = threading.Thread(target=client.loop_forever, daemon=True)
    t.start()
    return client


# Doğrudan çalıştırılırsa (test amaçlı) sadece dinle
if __name__ == "__main__":
    veritabani.kur()
    client = istemci_olustur()
    client.connect(config.MQTT_HOST, config.MQTT_PORT, keepalive=60)
    print("[MQTT] Dinleniyor... (Ctrl+C ile çık)")
    client.loop_forever()
