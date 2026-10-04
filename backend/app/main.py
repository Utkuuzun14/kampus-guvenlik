"""
FastAPI ana uygulaması.
- Açılışta veritabanını kurar ve MQTT dinleyiciyi arka planda başlatır.
- REST uçları: /api/olaylar, /api/durum, /api/saglik
- WebSocket /ws: yeni olayları bağlı istemcilere canlı iletir.
"""
import asyncio
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app import config, veritabani, mqtt_dinleyici


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


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _ana_dongu
    _ana_dongu = asyncio.get_event_loop()
    veritabani.kur()
    mqtt_dinleyici.olay_geri_cagirma = _olay_geldi
    client = mqtt_dinleyici.baslat_arka_planda()
    print("[APP] Backend hazir: MQTT dinleyici + API calisiyor.")
    yield
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
    return {"durum": "calisiyor"}


@app.get("/api/olaylar")
def olaylar(limit: int = 50):
    return veritabani.son_olaylar(limit)


@app.get("/api/durum")
def durum():
    """Düğüm durumu: son olay, çevrimiçi mi, son görülme."""
    import time as _t
    son = veritabani.son_olaylar(1)
    son_olay = son[0] if son else None
    # Son veri zamanı (sensor_gecmis'ten en güncel kayıt)
    son_veri = veritabani.sensor_gecmis_getir("duman", "dugum1", 1)
    son_zaman = son_veri[-1]["zaman"] if son_veri else None
    simdi = int(_t.time())
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
