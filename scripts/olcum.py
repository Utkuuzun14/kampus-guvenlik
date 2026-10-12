"""
Performans ölçümleri (akademik rapor için). Yalnızca test_dugum kullanır;
bitince bu çalıştırmada oluşan test_dugum kayıtlarını siler.

Ölçümler:
  1. Uçtan uca gecikme: MQTT yayını → WebSocket'ten olayın alınması (100 tekrar)
  2. Olay üretim gecikmesi: yayın → olayın SQLite'a yazılması (duman eşik aşımı
     ve alev, 20'şer tekrar)
  3. LWT tespit süresi: temiz olmayan kopma → broker'ın LWT'yi yayınlaması ve
     /api/dugumler'de çevrimdışı görünmesi (5 tekrar)
  4. E-posta: SMTP gönderim süresi (scripts/eposta_test.py ile 1 gerçek gönderim)
  5. Mesaj kaybı: QoS 1 ile 500 ölçüm → kaçı sensor_gecmis'e yazıldı

Çalıştırmadan önce: broker + backend açık, sahte üreteç KAPALI.

Çalıştırma (backend venv aktifken, proje kökünden):
    python scripts/olcum.py                    # sonuçları markdown olarak yazar
    python scripts/olcum.py --json sonuc.json  # ham sonuçları da kaydeder
    python scripts/olcum.py --eposta-yok       # gerçek e-posta göndermeden
"""
import argparse
import asyncio
import importlib.metadata
import json
import os
import platform
import shutil
import sqlite3
import statistics
import subprocess
import sys
import threading
import time
import urllib.request
from datetime import datetime

import paho.mqtt.client as mqtt
import websockets

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_senaryolari as ts  # noqa: E402  (db yolu, MQTT bağlantısı, temizlik)
import sahte_veri as sv  # noqa: E402  (LWT'li client ve kopma fonksiyonu)
from app import config  # noqa: E402

DUGUM = ts.DUGUM  # "test_dugum"
API = ts.API
WS_URL = "ws://127.0.0.1:8000/ws"
DB_YOKLAMA_SN = 0.002   # olay tablosunu yoklama aralığı (ölçüm çözünürlüğü)
API_YOKLAMA_SN = 0.01


def ms(sn):
    return sn * 1000.0


def ozet(degerler_ms):
    """ortalama, medyan, p95 (en yakın sıra yöntemi), min, max — ms"""
    s = sorted(degerler_ms)
    if not s:
        return None
    p95 = s[max(0, -(-95 * len(s) // 100) - 1)]
    return {"n": len(s), "ort": statistics.fmean(s), "medyan": statistics.median(s),
            "p95": p95, "min": s[0], "max": s[-1]}


def yayinla(client, sensor, deger):
    ts.yayinla(client, sensor, deger)


# ---------------- 1. Uçtan uca (MQTT → WebSocket) ----------------

async def _uctan_uca(client, tekrar):
    sureler, kayip = [], 0
    async with websockets.connect(WS_URL) as ws:
        await asyncio.sleep(0.5)
        for _ in range(tekrar):
            t0 = time.perf_counter()
            yayinla(client, "hareket", 1)
            bitis = t0 + 5
            alindi = False
            while time.perf_counter() < bitis:
                try:
                    ham = await asyncio.wait_for(ws.recv(), timeout=bitis - time.perf_counter())
                except asyncio.TimeoutError:
                    break
                veri = json.loads(ham).get("veri", {})
                if veri.get("dugum") == DUGUM and veri.get("sensor") == "hareket":
                    sureler.append(ms(time.perf_counter() - t0))
                    alindi = True
                    break
            kayip += not alindi
            await asyncio.sleep(0.05)
    return sureler, kayip


def olc_uctan_uca(client, tekrar=100):
    print(f"[1] Uçtan uca gecikme: {tekrar} yayın (hareket=1) → WebSocket olayı")
    sureler, kayip = asyncio.run(_uctan_uca(client, tekrar))
    print(f"    {len(sureler)} alındı, {kayip} zaman aşımı")
    return {"sureler_ms": sureler, "zaman_asimi": kayip}


# ---------------- 2. Olay üretim (yayın → SQLite) ----------------

def olay_bekle(db, onceki_id, sensor, seviye, sure=5.0):
    bitis = time.perf_counter() + sure
    while time.perf_counter() < bitis:
        satir = db.execute(
            "SELECT id FROM olaylar WHERE id > ? AND dugum = ? AND sensor = ? AND seviye = ? LIMIT 1",
            (onceki_id, DUGUM, sensor, seviye)).fetchone()
        if satir:
            return True
        time.sleep(DB_YOKLAMA_SN)
    return False


def son_olay_id(db):
    return db.execute("SELECT COALESCE(MAX(id), 0) FROM olaylar").fetchone()[0]


def olc_olay_uretim(client, tekrar=20):
    print(f"[2] Olay üretim gecikmesi: duman eşik aşımı ve alev, {tekrar}'şer tekrar")
    db = sqlite3.connect(ts.db_yolu(), timeout=5)
    sonuc = {}
    try:
        for sensor, normal, alarm, seviye in (("duman", 400, 2500, "yuksek"), ("alev", 0, 1, "kritik")):
            sureler, kayip = [], 0
            for _ in range(tekrar):
                yayinla(client, sensor, normal)  # histerezisi normale çek
                time.sleep(0.3)
                onceki = son_olay_id(db)
                t0 = time.perf_counter()
                yayinla(client, sensor, alarm)
                if olay_bekle(db, onceki, sensor, seviye):
                    sureler.append(ms(time.perf_counter() - t0))
                else:
                    kayip += 1
            yayinla(client, sensor, normal)
            time.sleep(0.3)
            print(f"    {sensor}: {len(sureler)} olay, {kayip} zaman aşımı")
            sonuc[sensor] = {"sureler_ms": sureler, "zaman_asimi": kayip}
    finally:
        db.close()
    return sonuc


# ---------------- 3. LWT tespit ----------------

def api_dugum():
    with urllib.request.urlopen(f"{API}/api/dugumler", timeout=5) as r:
        return next((d for d in json.loads(r.read().decode("utf-8")) if d["id"] == DUGUM), None)


def api_bekle(kosul, sure=10.0):
    bitis = time.perf_counter() + sure
    while time.perf_counter() < bitis:
        d = api_dugum()
        if d and kosul(d):
            return True
        time.sleep(API_YOKLAMA_SN)
    return False


def olc_lwt(tekrar=5):
    print(f"[3] LWT tespit süresi: {tekrar} temiz olmayan kopma")
    lwt_geldi = threading.Event()

    izleyici = mqtt.Client(client_id="olcum-izleyici", protocol=mqtt.MQTTv5,
                           callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    izleyici.username_pw_set(config.MQTT_KULLANICI, config.MQTT_PAROLA)

    def on_message(c, u, msg):
        if json.loads(msg.payload.decode("utf-8")).get("durum") == "offline":
            lwt_geldi.set()

    izleyici.on_message = on_message
    izleyici.connect(config.MQTT_HOST, config.MQTT_PORT)
    izleyici.subscribe(f"kampus/guvenlik/{DUGUM}/durum", 1)
    izleyici.loop_start()
    time.sleep(0.5)

    broker_ms, api_ms, kayip = [], [], 0
    try:
        for _ in range(tekrar):
            c = sv.istemci_olustur(DUGUM, client_id="olcum-lwt")
            sv.durum_yayinla(c, DUGUM, online=True).wait_for_publish(2)
            if not api_bekle(lambda d: d["cevrimici"]):
                kayip += 1
                c.disconnect()
                c.loop_stop()
                continue
            lwt_geldi.clear()
            # sv.baglantiyi_kopar ile aynı adımlar; ama loop_stop() paho ağ thread'inin
            # ~1 sn'lik select beklemesini bitirmesini beklediği için süre, socket'in
            # gerçekten kapandığı andan başlatılır.
            c.loop_stop()
            sock = c.socket()
            t0 = time.perf_counter()
            sock.close()
            if lwt_geldi.wait(10):
                broker_ms.append(ms(time.perf_counter() - t0))
            if api_bekle(lambda d: not d["cevrimici"] and d["son_durum"] == "offline"):
                api_ms.append(ms(time.perf_counter() - t0))
            else:
                kayip += 1
            time.sleep(1)
    finally:
        izleyici.loop_stop()
        izleyici.disconnect()
    print(f"    broker LWT: {len(broker_ms)}, API çevrimdışı: {len(api_ms)}, başarısız: {kayip}")
    return {"broker_ms": broker_ms, "api_ms": api_ms, "basarisiz": kayip}


# ---------------- 4. E-posta ----------------

def olc_eposta():
    print("[4] E-posta: SMTP gönderim süresi (eposta_test.py, 1 gerçek gönderim)")
    import eposta_test
    t0 = time.perf_counter()
    kod = eposta_test.main()
    sure = ms(time.perf_counter() - t0)
    return {"sure_ms": sure, "basarili": kod == 0}


# ---------------- 5. Mesaj kaybı ----------------

def olc_mesaj_kaybi(client, adet=500):
    print(f"[5] Mesaj kaybı: QoS 1 ile {adet} ölçüm, art arda (beklemesiz)")
    db = sqlite3.connect(ts.db_yolu(), timeout=5)
    try:
        yayinla(client, "duman", 400)  # histerezis normal: aşağıdaki değerler olay üretmez
        time.sleep(0.5)
        onceki = db.execute("SELECT COALESCE(MAX(id), 0) FROM sensor_gecmis").fetchone()[0]
        t0 = time.perf_counter()
        bilgiler = []
        for i in range(adet):
            konu = f"kampus/guvenlik/{DUGUM}/duman"
            yuk = json.dumps({"dugum": DUGUM, "sensor": "duman", "deger": 1000 + i, "zaman": int(time.time())})
            bilgiler.append(client.publish(konu, yuk, qos=1))
        for b in bilgiler:
            b.wait_for_publish(10)
        yayin_sn = time.perf_counter() - t0
        onaylanan = sum(b.is_published() for b in bilgiler)

        sorgu = ("SELECT COUNT(*), COUNT(DISTINCT deger) FROM sensor_gecmis "
                 "WHERE id > ? AND dugum = ? AND sensor = 'duman' AND deger BETWEEN 1000 AND ?")
        son, sabit_bas = (0, 0), time.perf_counter()
        while time.perf_counter() - t0 < 60:
            simdi = db.execute(sorgu, (onceki, DUGUM, 1000 + adet - 1)).fetchone()
            if simdi != son:
                son, sabit_bas = simdi, time.perf_counter()
            if simdi[0] >= adet or time.perf_counter() - sabit_bas > 3:
                break
            time.sleep(0.05)
        yazma_sn = time.perf_counter() - t0
    finally:
        db.close()
    yazilan, farkli = son
    print(f"    gönderilen {adet}, PUBACK alınan {onaylanan}, DB'ye yazılan {yazilan} ({farkli} farklı)")
    return {"gonderilen": adet, "puback": onaylanan, "yazilan": yazilan, "farkli": farkli,
            "yayin_sn": yayin_sn, "tamamlanma_sn": yazma_sn}


# ---------------- Ortam ----------------

def _ps(komut):
    try:
        komut = "[Console]::OutputEncoding = [Text.Encoding]::UTF8; " + komut
        return subprocess.run(["powershell", "-NoProfile", "-Command", komut], capture_output=True,
                              encoding="utf-8", errors="replace", timeout=20).stdout.strip()
    except Exception:
        return ""


def ortam_bilgisi():
    bilgi = {
        "tarih": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "isletim_sistemi": platform.platform(),
        "python": platform.python_version(),
        "paho_mqtt": importlib.metadata.version("paho-mqtt"),
        "websockets": websockets.__version__,
    }
    if platform.system() == "Windows":
        ad, cekirdek, mantiksal = (_ps("$c = Get-CimInstance Win32_Processor | Select-Object -First 1; "
                                       "$c.Name.Trim(); $c.NumberOfCores; $c.NumberOfLogicalProcessors")
                                   .splitlines() + ["?", "?", "?"])[:3]
        bilgi["cpu"] = f"{ad} ({cekirdek} çekirdek / {mantiksal} mantıksal işlemci)"
        ram = _ps("(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory")
        bilgi["ram"] = f"{int(ram) / 1024 ** 3:.1f} GB" if ram.isdigit() else "?"
        bilgi["isletim_sistemi"] = _ps("(Get-CimInstance Win32_OperatingSystem | ForEach-Object "
                                       "{ \"$($_.Caption) $($_.Version)\" })") or bilgi["isletim_sistemi"]
    else:
        bilgi["cpu"] = platform.processor()
        bilgi["ram"] = "?"
    mosq = shutil.which("mosquitto") or r"C:\Program Files\mosquitto\mosquitto.exe"
    try:
        cikti = subprocess.run([mosq, "-h"], capture_output=True, text=True, timeout=10)
        ilk = (cikti.stdout or cikti.stderr).splitlines()[0]
        bilgi["mosquitto"] = ilk.replace("mosquitto version", "").strip()
    except Exception:
        bilgi["mosquitto"] = "?"
    return bilgi


# ---------------- Rapor ----------------

def satir(ad, o):
    if not o:
        return f"| {ad} | 0 | — | — | — | — | — |"
    return (f"| {ad} | {o['n']} | {o['ort']:.1f} | {o['medyan']:.1f} | {o['p95']:.1f} "
            f"| {o['min']:.1f} | {o['max']:.1f} |")


def markdown(s):
    o = s["ortam"]
    m = [
        f"### Ölçüm ortamı ({o['tarih']})",
        "",
        "| Bileşen | Değer |",
        "|---|---|",
        f"| İşletim sistemi | {o['isletim_sistemi']} |",
        f"| CPU | {o['cpu']} |",
        f"| RAM | {o['ram']} |",
        f"| Python | {o['python']} (paho-mqtt {o['paho_mqtt']}, websockets {o['websockets']}) |",
        f"| Mosquitto | {o['mosquitto']} |",
        "| Yerleşim | Broker, backend ve ölçüm betiği aynı makinede (localhost); ağ gecikmesi yok |",
        "",
        "### Gecikmeler (ms)",
        "",
        "| Ölçüm | n | Ortalama | Medyan | p95 | Min | Max |",
        "|---|---|---|---|---|---|---|",
        satir("Uçtan uca: MQTT yayını → WebSocket olayı (hareket)", ozet(s["uctan_uca"]["sureler_ms"])),
        satir("Olay üretimi: yayın → SQLite (duman eşik aşımı)", ozet(s["olay"]["duman"]["sureler_ms"])),
        satir("Olay üretimi: yayın → SQLite (alev)", ozet(s["olay"]["alev"]["sureler_ms"])),
        satir("LWT: kopma → broker LWT yayını", ozet(s["lwt"]["broker_ms"])),
        satir("LWT: kopma → /api/dugumler çevrimdışı", ozet(s["lwt"]["api_ms"])),
        "",
        f"Zaman aşımı / başarısız: uçtan uca {s['uctan_uca']['zaman_asimi']}, "
        f"duman {s['olay']['duman']['zaman_asimi']}, alev {s['olay']['alev']['zaman_asimi']}, "
        f"LWT {s['lwt']['basarisiz']}.",
        "",
    ]
    if s.get("eposta"):
        e = s["eposta"]
        m += ["### E-posta", "",
              "| Ölçüm | Süre | Sonuç |", "|---|---|---|",
              f"| SMTP SSL (465) bağlantı + giriş + gönderim, 1 gerçek mail | {e['sure_ms']:.0f} ms "
              f"| {'gönderildi' if e['basarili'] else 'BAŞARISIZ'} |", ""]
    k = s["kayip"]
    oran = 100.0 * (k["gonderilen"] - k["yazilan"]) / k["gonderilen"]
    m += ["### Mesaj kaybı (QoS 1)", "",
          "| Gönderilen | PUBACK alınan | sensor_gecmis'e yazılan | Farklı değer | Kayıp | Yayın süresi | Tümünün yazılma süresi | Verim |",
          "|---|---|---|---|---|---|---|---|",
          f"| {k['gonderilen']} | {k['puback']} | {k['yazilan']} | {k['farkli']} | %{oran:.1f} "
          f"| {k['yayin_sn']:.2f} sn | {k['tamamlanma_sn']:.2f} sn "
          f"| {k['yazilan'] / k['tamamlanma_sn']:.0f} mesaj/sn |", ""]
    m += ["Yöntem notları:",
          "- Süreler `time.perf_counter()` ile aynı makinede ölçüldü (saat senkronu gerekmez).",
          f"- Olay üretimi SQLite'ı {DB_YOKLAMA_SN * 1000:.0f} ms aralıkla yoklayarak ölçüldü "
          f"(çözünürlük ~{DB_YOKLAMA_SN * 1000:.0f} ms). Her tekrardan önce histerezis normale çekildi.",
          f"- LWT süreleri socket'in DISCONNECT gönderilmeden kapatıldığı andan başlar; API süresi "
          f"/api/dugumler {API_YOKLAMA_SN * 1000:.0f} ms aralıkla yoklanarak ölçüldü.",
          "- Uçtan uca ölçüm her yayında bir olay üreten hareket=1 ile yapıldı; WebSocket yalnızca "
          "olayları iletir.",
          "- Mesaj kaybı testinde 500 mesaj beklemesiz art arda yayınlandı (yük testi); değerler "
          "1000-1499 olduğundan olay üretmez, yalnızca ölçüm olarak yazılır.",
          ""]
    return "\n".join(m)


def main():
    ap = argparse.ArgumentParser(description="Performans ölçümleri (test_dugum)")
    ap.add_argument("--json", help="ham sonuçları bu dosyaya yaz")
    ap.add_argument("--eposta-yok", action="store_true", help="gerçek e-posta ölçümünü atla")
    arg = ap.parse_args()

    sonuc = {"ortam": ortam_bilgisi()}
    baslangic = ts.son_kayit_idleri()
    client = ts.mqtt_baglan()
    try:
        time.sleep(1)
        ts.normale_cek(client)
        sonuc["uctan_uca"] = olc_uctan_uca(client)
        sonuc["olay"] = olc_olay_uretim(client)
        sonuc["lwt"] = olc_lwt()
        sonuc["kayip"] = olc_mesaj_kaybi(client)
        if not arg.eposta_yok:
            sonuc["eposta"] = olc_eposta()
    finally:
        client.loop_stop()
        client.disconnect()
        time.sleep(1)  # son mesajlar yazılsın
        ts.test_verisini_temizle(baslangic)
        with sqlite3.connect(ts.db_yolu()) as db:
            kalan = {t: db.execute(f"SELECT COUNT(*) FROM {t} WHERE dugum = ?", (DUGUM,)).fetchone()[0]
                     for t in ts.TABLOLAR}
        print(f"Doğrulama: veritabanında kalan {DUGUM} kaydı: {kalan}")
        sonuc["temizlik_sonrasi_kalan"] = kalan

    if arg.json:
        with open(arg.json, "w", encoding="utf-8") as f:
            json.dump(sonuc, f, ensure_ascii=False, indent=2)
    print()
    print(markdown(sonuc))
    return 0


if __name__ == "__main__":
    sys.exit(main())
