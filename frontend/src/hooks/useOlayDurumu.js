import { useState, useEffect, useCallback } from "react";
import { apiFetch, apiJson } from "../api";

// Olay yaşam döngüsü: PATCH /api/olaylar/{id}/durum ve /api/istatistik/mudahale.
// Durum değişikliği tüm sekmelere WebSocket "olay_guncelleme" mesajıyla da ulaşır.
// Onaylayan backend'de token'dan alınır; istemci göndermez.
const ISTATISTIK_YENILEME_MS = 30000;

// Hata: { durum: HTTP kodu, mevcut: 409'da sunucudaki durum, mesaj }
export async function durumIlerlet(id, durum, not) {
  let cevap;
  try {
    cevap = await apiFetch(`/api/olaylar/${id}/durum`, {
      method: "PATCH",
      body: JSON.stringify({ durum, not: not || null }),
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

export const olayGetir = (id) => apiJson(`/api/olaylar/${id}`);

// { acik_sayisi, ort_gorulme_sn, ort_cozum_sn, cozulen_sayisi } | null ve elle yenileme
export function useMudahaleIstatistigi() {
  const [istatistik, setIstatistik] = useState(null);

  const yenile = useCallback(async () => {
    const veri = await apiJson("/api/istatistik/mudahale");
    if (veri) setIstatistik(veri); // hata: sessiz geç, bir sonraki yenilemede tekrar denenir
  }, []);

  useEffect(() => {
    yenile();
    const zaman = setInterval(yenile, ISTATISTIK_YENILEME_MS);
    return () => clearInterval(zaman);
  }, [yenile]);

  return [istatistik, yenile];
}
