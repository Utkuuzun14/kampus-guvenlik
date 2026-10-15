"""
FastAPI ana uygulaması.
- Açılışta veritabanını kurar ve MQTT dinleyiciyi arka planda başlatır.
- REST uçları: /api/olaylar, /api/olaylar/{id}, PATCH /api/olaylar/{id}/durum,
  /api/istatistik/mudahale, /api/durum, /api/dugumler, /api/gecmis, /api/saglik,
  GET/PUT /api/ayarlar/mod (güvenlik modu), POST /api/giris, GET /api/ben,
  /api/kullanicilar (admin)
- /api/saglik ve /api/giris dışındaki tüm uçlar Bearer token ister (app/kimlik.py).
- WebSocket /ws?token=...: yeni olayları, durum güncellemelerini ve güvenlik modu
  değişikliklerini bağlı istemcilere canlı iletir; token geçersizse 4401 ile kapanır.
"""
import asyncio
import json
import logging
import re
import time
from contextlib import asynccontextmanager
from typing import Annotated, Literal

from fastapi import (APIRouter, Depends, FastAPI, HTTPException, Request, WebSocket,
                     WebSocketDisconnect)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, StringConstraints

from app import config, kimlik, kurallar, veritabani, mqtt_dinleyici
from app.kimlik import admin_gerekli, aktif_kullanici

# Otomatik modda etkin mod (mesai/gece) saat ilerledikçe değişir; bu aralıkla
# kontrol edilip değişince WS "mod" mesajı yayınlanır.
MOD_KONTROL_SN = 30
# Modu en son kimin, ne zaman değiştirdiği (ayarlar tablosu)
MOD_DEGISTIREN_ANAHTAR = "guvenlik_modu_degistiren"
MOD_ZAMAN_ANAHTAR = "guvenlik_modu_zaman"
# Geçersiz token'la açılan WebSocket bu kodla kapatılır (HTTP 401'in karşılığı)
WS_YETKISIZ = 4401


class _TokenMaskesi(logging.Filter):
    """uvicorn loglarında ?token=... değerini gizler (WS adresi erişim loguna düşer)."""
    _desen = re.compile(r"(token=)[^&\s\"']+")

    def filter(self, record):
        mesaj = record.getMessage()
        if "token=" in mesaj:
            record.msg, record.args = self._desen.sub(r"\1***", mesaj), ()
        return True


for _ad in ("uvicorn.access", "uvicorn.error"):
    logging.getLogger(_ad).addFilter(_TokenMaskesi())


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


def _mod_yaniti(bilgi):
    """kurallar.mod_bilgisi() + modu en son kimin, ne zaman değiştirdiği."""
    zaman = veritabani.ayar_getir(MOD_ZAMAN_ANAHTAR)
    return {
        **bilgi,
        "degistiren": veritabani.ayar_getir(MOD_DEGISTIREN_ANAHTAR),
        "degistirme_zaman": float(zaman) if zaman else None,
    }


async def _mod_izle():
    """Etkin mod değişince (ör. 23:00'te gece başlar) tüm sekmelere bildirir."""
    onceki = None
    while True:
        try:
            bilgi = _mod_yaniti(kurallar.mod_bilgisi())
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
    if veritabani.kullanici_sayisi() == 0:
        print("[APP] UYARI: Henüz kullanıcı yok: python scripts/kullanici_ekle.py")
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
    allow_origins=config.CORS_KAYNAKLAR,
    allow_methods=["GET", "POST", "PUT", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
    expose_headers=["Retry-After"],
)

# /api/saglik ve /api/giris dışındaki her uç bu router'da: token tek yerde zorunlu
korumali = APIRouter(dependencies=[Depends(aktif_kullanici)])


@app.get("/api/saglik")
def saglik():
    """Servis ayakta mı + backend'in MQTT broker bağlantısı. Token istemez."""
    return {"durum": "calisiyor", "mqtt": "bagli" if mqtt_dinleyici.bagli else "kopuk"}


# ---------------- Kimlik doğrulama ----------------

GIRIS_HATA_MESAJI = "Kullanıcı adı veya parola hatalı"


class GirisIstegi(BaseModel):
    kullanici_adi: Annotated[str, StringConstraints(max_length=64)]
    parola: Annotated[str, StringConstraints(max_length=256)]


def _kullanici_ozeti(k):
    return {"kullanici_adi": k["kullanici_adi"], "ad_soyad": k["ad_soyad"], "rol": k["rol"]}


@app.post("/api/giris")
def giris(istek: GirisIstegi, http: Request):
    """
    {token, kullanici}. 401: hatalı/pasif (hangisi olduğu söylenmez).
    429: aynı kullanıcı adı + IP için çok fazla hatalı deneme (Retry-After).
    """
    sonuc, veri = kimlik.giris_yap(istek.kullanici_adi, istek.parola, kimlik.istemci_ip(http))
    if sonuc == "kilitli":
        return JSONResponse(status_code=429, headers={"Retry-After": str(veri)}, content={
            "detail": f"Çok fazla hatalı deneme. {veri} sn sonra tekrar deneyin.",
            "kalan_sn": veri,
        })
    if sonuc == "hatali":
        raise HTTPException(401, GIRIS_HATA_MESAJI)
    token, kullanici = veri
    return {"token": token, "kullanici": _kullanici_ozeti(kullanici)}


@korumali.get("/api/ben")
def ben(kullanici=Depends(aktif_kullanici)):
    """Token sahibinin bilgisi (rol veritabanından)."""
    return _kullanici_ozeti(kullanici)


class KullaniciIstegi(BaseModel):
    kullanici_adi: Annotated[str, StringConstraints(max_length=64)]
    ad_soyad: Annotated[str, StringConstraints(max_length=200)] | None = None
    rol: Literal["admin", "operator"]
    parola: Annotated[str, StringConstraints(max_length=256)]


class KullaniciGuncelleme(BaseModel):
    rol: Literal["admin", "operator"] | None = None
    ad_soyad: Annotated[str, StringConstraints(max_length=200)] | None = None
    aktif: bool | None = None
    yeni_parola: Annotated[str, StringConstraints(max_length=256)] | None = None


@korumali.get("/api/kullanicilar", dependencies=[Depends(admin_gerekli)])
def kullanicilar():
    """Tüm kullanıcılar (parola özeti ve tuz dönmez)."""
    return veritabani.kullanicilari_listele()


@korumali.post("/api/kullanicilar", status_code=201, dependencies=[Depends(admin_gerekli)])
def kullanici_olustur(istek: KullaniciIstegi):
    """422: geçersiz ad/parola (parola en az 8) · 409: kullanıcı adı alınmış."""
    try:
        return veritabani.kullanici_ekle(istek.kullanici_adi, istek.ad_soyad, istek.rol,
                                         istek.parola)
    except veritabani.KullaniciHatasi as e:
        raise HTTPException(422, str(e)) from None
    except veritabani.KullaniciVar:
        raise HTTPException(409, "Bu kullanıcı adı zaten kayıtlı") from None


@korumali.patch("/api/kullanicilar/{ad}")
def kullanici_degistir(ad: str, istek: KullaniciGuncelleme, admin=Depends(admin_gerekli)):
    """
    rol, ad_soyad, aktif, yeni_parola. 404: yok · 422: geçersiz değer ·
    409: admin kendini pasif yapamaz; son aktif admin pasif yapılamaz / operatöre düşürülemez.
    """
    if ad.strip().lower() == admin["kullanici_adi"] and istek.aktif is False:
        raise HTTPException(409, "Kendi hesabınızı pasif yapamazsınız")
    try:
        sonuc, veri = veritabani.kullanici_guncelle(
            ad, rol=istek.rol, ad_soyad=istek.ad_soyad, aktif=istek.aktif,
            yeni_parola=istek.yeni_parola)
    except veritabani.KullaniciHatasi as e:
        raise HTTPException(422, str(e)) from None
    if sonuc == "yok":
        raise HTTPException(404, "Kullanıcı bulunamadı")
    if sonuc == "son_admin":
        raise HTTPException(409, "Son aktif admin pasif yapılamaz veya operatöre düşürülemez")
    return veri


# ---------------- Olaylar ----------------

@korumali.get("/api/olaylar")
def olaylar(limit: int = 50, durum: Literal["acik"] | None = None):
    """durum=acik: yalnızca çözülmemiş olaylar (durum != cozuldu)."""
    return veritabani.son_olaylar(limit, sadece_acik=durum == "acik")


@korumali.get("/api/olaylar/{olay_id}")
def olay(olay_id: int):
    """Tek olay ve durum adımları (zaman çizelgesi için)."""
    kayit = veritabani.olay_getir(olay_id)
    if kayit is None:
        raise HTTPException(404, "Olay bulunamadı")
    return kayit


class DurumIstegi(BaseModel):
    durum: Literal["goruldu", "mudahale", "cozuldu"]
    # Eski istemcilerle uyum için kabul edilir ama YOK SAYILIR: onaylayan token'dan gelir
    onaylayan: str | None = Field(None)
    not_: Annotated[str, StringConstraints(strip_whitespace=True, max_length=300)] | None = Field(
        None, alias="not")


@korumali.patch("/api/olaylar/{olay_id}/durum")
async def olay_durum(olay_id: int, istek: DurumIstegi, kullanici=Depends(aktif_kullanici)):
    """
    Olayı ileri bir duruma geçirir (yeni → goruldu → mudahale → cozuldu, adım atlanabilir).
    Onaylayan (olaylar.onaylayan, olay_adimlari.kim) token sahibidir.
    404: olay yok · 409: geri/aynı duruma geçiş · 422: geçersiz gövde.
    """
    sonuc, veri = veritabani.olay_durum_guncelle(
        olay_id, istek.durum, kimlik.gorunen_ad(kullanici), istek.not_ or None)
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


@korumali.get("/api/ayarlar/mod")
def mod_getir():
    """
    {mod, etkin_mod, aciklama, degistiren, degistirme_zaman}; etkin_mod otomatikte
    o an geçerli olan mod.
    """
    return _mod_yaniti(kurallar.mod_bilgisi())


@korumali.put("/api/ayarlar/mod")
async def mod_ayarla(istek: ModIstegi, admin=Depends(admin_gerekli)):
    """Güvenlik modunu kalıcı olarak değiştirir. Yalnızca admin (403). 422: geçersiz mod."""
    onceki = kurallar.mod_getir()
    veritabani.ayar_yaz(kurallar.MOD_ANAHTAR, istek.mod)
    if istek.mod != onceki:
        veritabani.ayar_yaz(MOD_DEGISTIREN_ANAHTAR, kimlik.gorunen_ad(admin))
        veritabani.ayar_yaz(MOD_ZAMAN_ANAHTAR, str(time.time()))
    bilgi = _mod_yaniti(kurallar.mod_bilgisi(istek.mod))
    if istek.mod != onceki:
        print(f"[MOD] Güvenlik modu: {onceki} -> {istek.mod} ({bilgi['aciklama']}, "
              f"değiştiren: {admin['kullanici_adi']})")
        await yonetici.yayinla({"tip": "mod", "veri": bilgi})
    return bilgi


@korumali.get("/api/istatistik/mudahale")
def mudahale_istatistigi():
    """acik_sayisi tüm zamanlar; ortalamalar ve cozulen_sayisi son 24 saat."""
    return veritabani.mudahale_istatistigi()


@korumali.get("/api/durum")
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


@korumali.get("/api/dugumler")
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


@korumali.get("/api/gecmis")
def gecmis(sensor: str = "duman", dugum: str = "dugum1", limit: int = 50):
    return veritabani.sensor_gecmis_getir(sensor, dugum, limit)


app.include_router(korumali)


@app.websocket("/ws")
async def ws_ucu(ws: WebSocket, token: str | None = None):
    # Önce kabul edilir: kabulsüz kapatma istemciye 4401 değil HTTP 403 olarak gider
    if kimlik.token_kullanicisi(token) is None:
        await ws.accept()
        await ws.close(code=WS_YETKISIZ, reason="Oturum geçersiz")
        return
    await yonetici.baglan(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        yonetici.ayril(ws)
