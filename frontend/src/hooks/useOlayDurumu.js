import { useState, useEffect, useCallback } from "react";
import { API, OPERATOR_ANAHTAR } from "../sabitler";

// Olay yaşam döngüsü: PATCH /api/olaylar/{id}/durum ve /api/istatistik/mudahale.
// Durum değişikliği tüm sekmelere WebSocket "olay_guncelleme" mesajıyla da ulaşır.
const ISTATISTIK_YENILEME_MS = 30000;

// Hata: { durum: HTTP kodu, mevcut: 409'da sunucudaki durum, mesaj }
export async function durumIlerlet(id, durum, onaylayan, not) {
  let cevap;
  try {
    cevap = await fetch(`${API}/api/olaylar/${id}/durum`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ durum, onaylayan, not: not || null }),
    });
  } catch {
    throw { durum: 0, mesaj: "Sunucuya ulaşılamadı." };
  }
  const veri = await cevap.json().catch(() => null);
  if (!cevap.ok) {
    throw { durum: cevap.status, mevcut: veri?.mevcut, mesaj: veri?.detail };
  }
  return veri;
}

export async function olayGetir(id) {
  try {
    const cevap = await fetch(`${API}/api/olaylar/${id}`);
    return cevap.ok ? await cevap.json() : null;
  } catch {
    return null;
  }
}

// localStorage erişimi gizli pencere vb. durumlarda hata verebilir
export function operatorOku() {
  try {
    return localStorage.getItem(OPERATOR_ANAHTAR) ?? "";
  } catch {
    return "";
  }
}

export function operatorYaz(ad) {
  try {
    localStorage.setItem(OPERATOR_ANAHTAR, ad);
  } catch {
    // hatırlanmazsa da sorun değil
  }
}

// { acik_sayisi, ort_gorulme_sn, ort_cozum_sn, cozulen_sayisi } | null ve elle yenileme
export function useMudahaleIstatistigi() {
  const [istatistik, setIstatistik] = useState(null);

  const yenile = useCallback(async () => {
    try {
      const cevap = await fetch(`${API}/api/istatistik/mudahale`);
      if (cevap.ok) setIstatistik(await cevap.json());
    } catch {
      // sessiz geç; bir sonraki yenilemede tekrar denenir
    }
  }, []);

  useEffect(() => {
    yenile();
    const zaman = setInterval(yenile, ISTATISTIK_YENILEME_MS);
    return () => clearInterval(zaman);
  }, [yenile]);

  return [istatistik, yenile];
}
