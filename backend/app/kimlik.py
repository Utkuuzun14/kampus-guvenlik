"""
Kimlik doğrulama ve yetkilendirme (docs/SOZLESMELER.md §9).
- JWT (HS256) üretme/çözme: sub (kullanici_adi), rol, ad, iat, exp
- FastAPI bağımlılıkları: aktif_kullanici (geçerli token), admin_gerekli (rol)
- WebSocket için aynı doğrulama: ws_kullanici
- Kaba kuvvet koruması: (kullanıcı adı, IP) başına hatalı deneme sayacı (bellekte)
Rol her istekte veritabanından okunur; token'daki rol yalnızca bilgi amaçlıdır.
Böylece pasif yapılan ya da rolü düşürülen kullanıcının eski token'ı hemen etkisizleşir.
"""
import secrets
import threading
import time

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app import config, veritabani

ALGORITMA = "HS256"
_bearer = HTTPBearer(auto_error=False)
# Kullanıcı yoksa da aynı süren scrypt hesabı için sabit sahte özet
_SAHTE_OZET, _SAHTE_TUZ = veritabani.parola_ozeti(secrets.token_urlsafe(16))


def gorunen_ad(kullanici):
    """Zaman çizelgesi ve 'değiştiren' alanı için: ad_soyad, yoksa kullanici_adi."""
    return kullanici.get("ad_soyad") or kullanici["kullanici_adi"]


def token_uret(kullanici, sure_sn=None, simdi=None):
    simdi = int(simdi if simdi is not None else time.time())
    sure_sn = sure_sn if sure_sn is not None else int(config.TOKEN_SURE_SAAT * 3600)
    yuk = {
        "sub": kullanici["kullanici_adi"],
        "rol": kullanici["rol"],
        "ad": gorunen_ad(kullanici),
        "iat": simdi,
        "exp": simdi + sure_sn,
    }
    return jwt.encode(yuk, config.JWT_GIZLI_ANAHTAR, algorithm=ALGORITMA)


def token_coz(token):
    """Geçerli token'ın yükü; bozuk/süresi dolmuş/imzası yanlışsa None."""
    try:
        return jwt.decode(token, config.JWT_GIZLI_ANAHTAR, algorithms=[ALGORITMA],
                          options={"require": ["sub", "exp"]})
    except jwt.PyJWTError:
        return None


def token_kullanicisi(token):
    """Token geçerli ve kullanıcı aktifse kullanıcı sözlüğü (DB'den), değilse None."""
    yuk = token_coz(token) if token else None
    if not yuk:
        return None
    kullanici = veritabani.kullanici_getir(yuk["sub"])
    if not kullanici or not kullanici["aktif"]:
        return None
    return kullanici


def _yetkisiz(mesaj="Oturum geçersiz veya süresi dolmuş"):
    return HTTPException(401, mesaj, headers={"WWW-Authenticate": "Bearer"})


def aktif_kullanici(kimlik: HTTPAuthorizationCredentials | None = Depends(_bearer)):
    """Bearer token zorunlu: yoksa/bozuksa/süresi dolmuşsa/kullanıcı pasifse 401."""
    if kimlik is None:
        raise _yetkisiz("Giriş yapılmamış")
    kullanici = token_kullanicisi(kimlik.credentials)
    if kullanici is None:
        raise _yetkisiz()
    return kullanici


def admin_gerekli(kullanici=Depends(aktif_kullanici)):
    if kullanici["rol"] != "admin":
        raise HTTPException(403, "Bu işlem için admin yetkisi gerekli")
    return kullanici


def istemci_ip(istek: Request):
    return istek.client.host if istek.client else "?"


# ---------------- Giriş ve kaba kuvvet koruması ----------------

class KabaKuvvet:
    """(kullanıcı adı, IP) başına ardışık hata sayısı; sınırda kilit. İş parçacığı güvenli."""

    def __init__(self, sinir, kilit_sn, saat=time.monotonic):
        self.sinir, self.kilit_sn, self._saat = sinir, kilit_sn, saat
        self._kayit = {}  # anahtar -> [hata_sayisi, kilit_bitis]
        self._kilit = threading.Lock()

    def kalan(self, anahtar):
        """Kilit sürüyorsa kalan saniye (yukarı yuvarlanmış), yoksa 0."""
        with self._kilit:
            k = self._kayit.get(anahtar)
            if not k or not k[1]:
                return 0
            kalan = k[1] - self._saat()
            if kalan <= 0:  # kilit bitti: sayaç baştan
                del self._kayit[anahtar]
                return 0
            return int(kalan) + 1

    def hata(self, anahtar):
        with self._kilit:
            k = self._kayit.setdefault(anahtar, [0, 0.0])
            k[0] += 1
            if k[0] >= self.sinir:
                k[1] = self._saat() + self.kilit_sn

    def basari(self, anahtar):
        with self._kilit:
            self._kayit.pop(anahtar, None)


kaba_kuvvet = KabaKuvvet(config.GIRIS_HATA_SINIRI, config.GIRIS_KILIT_SN)


def giris_yap(kullanici_adi, parola, ip):
    """
    (sonuç, veri):
      ("kilitli", kalan_sn)  çok fazla hatalı deneme (parola doğru olsa bile)
      ("hatali", None)       kullanıcı yok / parola yanlış / pasif (ayrım yapılmaz)
      ("tamam", (token, kullanici))
    Her deneme giris_kayitlari'na yazılır. Parola hiçbir yerde loglanmaz.
    """
    ad = (kullanici_adi or "").strip().lower()
    anahtar = (ad, ip)
    kalan = kaba_kuvvet.kalan(anahtar)
    if kalan:
        veritabani.giris_kaydet(ad, ip, False)
        return "kilitli", kalan

    kayit = veritabani.kullanici_getir(ad, hassas=True) if ad else None
    if kayit is None:
        # Kullanıcı yokken de aynı süren hesap: yanıt süresinden varlığı anlaşılmasın
        veritabani.parola_dogru(parola or "", _SAHTE_OZET, _SAHTE_TUZ)
        dogru = False
    else:
        dogru = veritabani.parola_dogru(parola or "", kayit["parola_hash"], kayit["tuz"])
    if not dogru or not kayit["aktif"]:
        kaba_kuvvet.hata(anahtar)
        veritabani.giris_kaydet(ad, ip, False)
        return "hatali", None

    kaba_kuvvet.basari(anahtar)
    veritabani.giris_kaydet(ad, ip, True)
    veritabani.son_giris_yaz(ad)
    kullanici = veritabani.kullanici_getir(ad)
    return "tamam", (token_uret(kullanici), kullanici)
