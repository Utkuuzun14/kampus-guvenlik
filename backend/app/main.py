"""
FastAPI ana uygulaması.
- Açılışta veritabanını kurar ve MQTT dinleyiciyi arka planda başlatır.
- REST uçları: /api/olaylar, /api/olaylar/{id}, PATCH /api/olaylar/{id}/durum,
  /api/istatistik/mudahale, /api/durum, /api/dugumler, /api/gecmis, /api/saglik,
  GET/PUT /api/ayarlar/mod (güvenlik modu)
- WebSocket /ws: yeni olayları, durum güncellemelerini ve güvenlik modu
  değişikliklerini bağlı istemcilere canlı iletir.
"""
import asyncio
import json
import time
from contextlib import asynccontextmanager
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, StringConstraints

from app import config, kurallar, veritabani, mqtt_dinleyici

# Otomatik modda etkin mod (mesai/gece) saat ilerledikçe değişir; bu aralıkla
# kontrol edilip değişince WS "mod" mesajı yayınlanır.
MOD_KONTROL_SN = 30


class BaglantiYoneticisi:
    def __init__(self):
        self.aktif = []

    async def baglan(self, ws: WebSocket):
        await ws.accept()
        self.aktif.append(ws)

    def ayril(self, ws: WebSocket):
        if ws in self.aktif:
            self.aktif.remove(ws)

    async def yayinla(self, mesaj: dict):
        olu = []
        for ws in self.aktif:
            try:
                await ws.send_text(json.dumps(mesaj, ensure_ascii=False))
            except Exception:
                olu.append(ws)
        for ws in olu:
            self.ayril(ws)


yonetici = BaglantiYoneticisi()
_ana_dongu = None


def _olay_geldi(olay: dict):
    if _ana_dongu is None:
        return
    mesaj = {"tip": "olay", "veri": olay}
    asyncio.run_coroutine_threadsafe(yonetici.yayinla(mesaj), _ana_dongu)


async def _mod_izle():
    """Etkin mod değişince (ör. 23:00'te gece başlar) tüm sekmelere bildirir."""
    onceki = None
    while True:
        try:
            bilgi = kurallar.mod_bilgisi()
            if onceki is not None and bilgi["etkin_mod"] != onceki:
                await yonetici.yayinla({"tip": "mod", "veri": bilgi})
            onceki = bilgi["etkin_mod"]
        except Exception as e:
            print(f"[MOD] izleme hatası: {e}")
        await asyncio.sleep(MOD_KONTROL_SN)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _ana_dongu
    _ana_dongu = asyncio.get_event_loop()
    veritabani.kur()
    mqtt_dinleyici.olay_geri_cagirma = _olay_geldi
    client = mqtt_dinleyici.baslat_arka_planda()
    izleyici = asyncio.create_task(_mod_izle())
    print("[APP] Backend hazir: MQTT dinleyici + API calisiyor.")
    yield
    izleyici.cancel()
    try:
        client.disconnect()
    except Exception:
        pass


app = FastAPI(title="Kampus Guvenlik API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/saglik")
def saglik():
    """Servis ayakta mı + backend'in MQTT broker bağlantısı."""
    return {"durum": "calisiyor", "mqtt": "bagli" if mqtt_dinleyici.bagli else "kopuk"}


@app.get("/api/olaylar")
def olaylar(limit: int = 50, durum: Literal["acik"] | None = None):
    """durum=acik: yalnızca çözülmemiş olaylar (durum != cozuldu)."""
    return veritabani.son_olaylar(limit, sadece_acik=durum == "acik")


@app.get("/api/olaylar/{olay_id}")
def olay(olay_id: int):
    """Tek olay ve durum adımları (zaman çizelgesi için)."""
    kayit = veritabani.olay_getir(olay_id)
    if kayit is None:
        raise HTTPException(404, "Olay bulunamadı")
    return kayit


class DurumIstegi(BaseModel):
    durum: Literal["goruldu", "mudahale", "cozuldu"]
    onaylayan: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]
    not_: Annotated[str, StringConstraints(strip_whitespace=True, max_length=300)] | None = Field(
        None, alias="not")


@app.patch("/api/olaylar/{olay_id}/durum")
async def olay_durum(olay_id: int, istek: DurumIstegi):
    """
    Olayı ileri bir duruma geçirir (yeni → goruldu → mudahale → cozuldu, adım atlanabilir).
    404: olay yok · 409: geri/aynı duruma geçiş · 422: geçersiz gövde.
    """
    sonuc, veri = veritabani.olay_durum_guncelle(
        olay_id, istek.durum, istek.onaylayan, istek.not_ or None)
    if sonuc == "yok":
        raise HTTPException(404, "Olay bulunamadı")
    if sonuc == "geri":
        return JSONResponse(status_code=409, content={
            "detail": f"Geri veya aynı duruma geçilemez ({veri} → {istek.durum})",
            "mevcut": veri,
        })
    await yonetici.yayinla({"tip": "olay_guncelleme", "veri": veri})
    return veri


class ModIstegi(BaseModel):
    mod: Literal["otomatik", "mesai", "mesai_disi", "gece"]


@app.get("/api/ayarlar/mod")
def mod_getir():
    """{mod, etkin_mod, aciklama}; etkin_mod otomatikte o an geçerli olan mod."""
    return kurallar.mod_bilgisi()


@app.put("/api/ayarlar/mod")
async def mod_ayarla(istek: ModIstegi):
    """Güvenlik modunu kalıcı olarak değiştirir. 422: geçersiz mod."""
    onceki = kurallar.mod_getir()
    veritabani.ayar_yaz(kurallar.MOD_ANAHTAR, istek.mod)
    bilgi = kurallar.mod_bilgisi(istek.mod)
    if istek.mod != onceki:
        print(f"[MOD] Güvenlik modu: {onceki} -> {istek.mod} ({bilgi['aciklama']})")
        await yonetici.yayinla({"tip": "mod", "veri": bilgi})
    return bilgi


@app.get("/api/istatistik/mudahale")
def mudahale_istatistigi():
    """acik_sayisi tüm zamanlar; ortalamalar ve cozulen_sayisi son 24 saat."""
    return veritabani.mudahale_istatistigi()


@app.get("/api/durum")
def durum():
    """Düğüm durumu: son olay, çevrimiçi mi, son görülme."""
    son = veritabani.son_olaylar(1)
    son_olay = son[0] if son else None
    # Son veri zamanı (sensor_gecmis'ten en güncel kayıt)
    son_veri = veritabani.sensor_gecmis_getir("duman", "dugum1", 1)
    son_zaman = son_veri[-1]["zaman"] if son_veri else None
    simdi = int(time.time())
    cevrimici = False
    gecen_sn = None
    if son_zaman:
        gecen_sn = simdi - son_zaman
        cevrimici = gecen_sn <= config.CEVRIMDISI_SANIYE
    return {
        "son_olay": son_olay,
        "esik_duman": config.ESIK_DUMAN,
        "cevrimici": cevrimici,
        "son_gorulme": son_zaman,
        "gecen_saniye": gecen_sn,
    }


@app.get("/api/dugumler")
def dugumler():
    """
    Bilinen tüm düğümler: config.DUGUM_KONUMLARI + sensor_gecmis'te görülenler.
    Çevrimdışı: en son kayıt durum=0 (LWT veya kapanış) ya da
    CEVRIMDISI_SANIYE içinde veri yok. Hiç veri yoksa veri_yok=True.
    """
    simdi = int(time.time())
    son = {}  # dugum -> {sensor: satir}
    for satir in veritabani.son_okumalar():
        son.setdefault(satir["dugum"], {})[satir["sensor"]] = satir

    idler = list(config.DUGUM_KONUMLARI) + sorted(set(son) - set(config.DUGUM_KONUMLARI))
    sonuc = []
    for dugum in idler:
        okumalar = son.get(dugum, {})
        durum = okumalar.get("durum")
        # "offline" satırı düğümün kendisinden gelen veri sayılmaz
        veri = [o for sensor, o in okumalar.items() if not (sensor == "durum" and o["deger"] == 0)]
        son_veri = max((o["zaman"] for o in veri), default=None)
        son_id = max((o["id"] for o in okumalar.values()), default=None)
        offline_son = durum is not None and durum["deger"] == 0 and durum["id"] == son_id
        cevrimici = (not offline_son and son_veri is not None
                     and simdi - son_veri <= config.CEVRIMDISI_SANIYE)
        sonuc.append({
            "id": dugum,
            "konum": config.DUGUM_KONUMLARI.get(dugum),
            "cevrimici": cevrimici,
            "veri_yok": not okumalar,
            "son_veri_zamani": son_veri,
            "son_durum": None if durum is None else ("online" if durum["deger"] else "offline"),
            "son": {
                sensor: ({"deger": okumalar[sensor]["deger"], "zaman": okumalar[sensor]["zaman"]}
                         if sensor in okumalar else None)
                for sensor in ("duman", "hareket", "alev")
            },
        })
    return sonuc


@app.get("/api/gecmis")
def gecmis(sensor: str = "duman", dugum: str = "dugum1", limit: int = 50):
    return veritabani.sensor_gecmis_getir(sensor, dugum, limit)


@app.websocket("/ws")
async def ws_ucu(ws: WebSocket):
    await yonetici.baglan(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        yonetici.ayril(ws)
