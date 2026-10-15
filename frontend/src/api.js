import { API, WS_URL, OTURUM_ANAHTAR, ESKI_OPERATOR_ANAHTAR } from "./sabitler";

// Oturum ve backend erişimi. Tüm REST çağrıları apiFetch'ten geçer (Authorization:
// Bearer). Herhangi bir istek 401 alırsa oturum temizlenir ve OTURUM_DUSTU olayı
// yayılır; useOturum bunu dinleyip giriş ekranına döner.
// Oturum { token, kullanici: { kullanici_adi, ad_soyad, rol } } sessionStorage'da,
// "Beni hatırla" işaretliyse localStorage'da tutulur.

export const OTURUM_DUSTU = "kg-oturum-dustu";

// Depolama erişimi gizli pencere / engellenmiş site verisinde hata verebilir
const depo = (kalici) => {
  try {
    return kalici ? window.localStorage : window.sessionStorage;
  } catch {
    return null;
  }
};

function depodanOku() {
  for (const kalici of [false, true]) {
    try {
      const o = JSON.parse(depo(kalici)?.getItem(OTURUM_ANAHTAR) ?? "null");
      if (o?.token && o?.kullanici) return { oturum: o, kalici };
    } catch {
      // bozuk kayıt: yok say
    }
  }
  return { oturum: null, kalici: false };
}

function depoyaYaz(oturum, kalici) {
  depoTemizle();
  try {
    depo(kalici)?.setItem(OTURUM_ANAHTAR, JSON.stringify(oturum));
  } catch {
    // saklanamazsa oturum yalnızca bu sayfa açıkken sürer
  }
}

function depoTemizle() {
  for (const kalici of [false, true]) {
    try {
      depo(kalici)?.removeItem(OTURUM_ANAHTAR);
    } catch {
      // yok say
    }
  }
}

// Operatör adı artık token'dan geliyor; eski panelin hatırladığı ad bir kez silinir
try {
  window.localStorage.removeItem(ESKI_OPERATOR_ANAHTAR);
} catch {
  // yok say
}

let { oturum: aktif, kalici: aktifKalici } = depodanOku();

export const aktifOturum = () => aktif;

// Sunucudan gelen güncel kullanıcı bilgisi (ör. rol değişmiş) oturuma yazılır
export function kullaniciGuncelle(kullanici) {
  if (!aktif) return null;
  aktif = { ...aktif, kullanici };
  depoyaYaz(aktif, aktifKalici);
  return aktif;
}

export function oturumDusur() {
  const vardi = Boolean(aktif);
  aktif = null;
  depoTemizle();
  if (vardi) window.dispatchEvent(new Event(OTURUM_DUSTU));
}

export function cikisYap() {
  aktif = null;
  depoTemizle();
}

// Hata: { durum: HTTP kodu (0: sunucuya ulaşılamadı), mesaj, kalan: 429'da saniye }
export async function girisYap(kullaniciAdi, parola, hatirla) {
  let cevap;
  try {
    cevap = await fetch(`${API}/api/giris`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ kullanici_adi: kullaniciAdi, parola }),
    });
  } catch {
    throw { durum: 0 };
  }
  const veri = await cevap.json().catch(() => null);
  if (!cevap.ok) {
    const kalan = Number(cevap.headers.get("Retry-After") ?? veri?.kalan_sn) || null;
    throw { durum: cevap.status, mesaj: veri?.detail, kalan };
  }
  aktif = { token: veri.token, kullanici: veri.kullanici };
  aktifKalici = Boolean(hatirla);
  depoyaYaz(aktif, aktifKalici);
  return aktif;
}

// fetch ile aynı imza; yol "/api/..." biçiminde. Gövde varsa JSON başlığı eklenir.
export async function apiFetch(yol, secenek = {}) {
  const basliklar = { ...secenek.headers };
  if (secenek.body != null) basliklar["Content-Type"] = "application/json";
  const token = aktif?.token;
  if (token) basliklar.Authorization = `Bearer ${token}`;
  const cevap = await fetch(`${API}${yol}`, { ...secenek, headers: basliklar });
  // Yanıt gelene kadar başka biri (çıkış, yeni giriş) oturumu değiştirmiş olabilir
  if (cevap.status === 401 && token && aktif?.token === token) oturumDusur();
  return cevap;
}

// JSON gövde ya da null (ağ hatası / başarısız yanıt)
export async function apiJson(yol, secenek) {
  try {
    const cevap = await apiFetch(yol, secenek);
    return cevap.ok ? await cevap.json() : null;
  } catch {
    return null;
  }
}

// WebSocket adresi; backend geçersiz token'da bağlantıyı 4401 ile kapatır
export const WS_YETKISIZ = 4401;
export const wsAdresi = () => `${WS_URL}?token=${encodeURIComponent(aktif?.token ?? "")}`;
