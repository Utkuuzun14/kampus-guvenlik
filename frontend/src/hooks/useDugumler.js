import { useState, useEffect } from "react";
import { API, CEVRIMDISI_SANIYE } from "../sabitler";

// Tek kaynak: /api/dugumler. Düğüm listesi, konum adı, çevrimiçi durumu ve SON
// ÖLÇÜMLER (PIR, MQ-2, Alev) yalnızca buradan gelir; gösterge, harita detay
// kartı ve "Aktif düğüm" kartı aynı değeri gösterir. WebSocket olayları ölçüm
// değerini değiştirmez (olay akışı/tablo içindir). Küçük grafiğin geçmişi
// useDumanSerisi ile çekilir ve son noktası bu son ölçüme hizalanır.
const YENILEME_MS = 3000;
const DUMAN_SERI = 40; // ~2 dk (3 sn aralık)

async function jsonGetir(yol) {
  try {
    const cevap = await fetch(`${API}${yol}`);
    return cevap.ok ? await cevap.json() : null;
  } catch {
    return null;
  }
}

// /api/dugumler satırı → panel düğüm nesnesi
const donustur = (d) => ({
  id: d.id,
  konum: d.konum,
  cevrimici: d.cevrimici,
  veriYok: d.veri_yok,
  sonZaman: d.son_veri_zamani,
  duman: d.son?.duman ?? null,
  hareket: d.son?.hareket ?? null,
  alev: d.son?.alev ?? null,
});

export default function useDugumler(simdiSn) {
  const [liste, setListe] = useState([]);
  const [cevrimiciGecmis, setCevrimiciGecmis] = useState([]);

  useEffect(() => {
    let iptal = false;
    const getir = async () => {
      const veri = await jsonGetir("/api/dugumler");
      if (iptal || !Array.isArray(veri)) return;
      const yeni = veri.map(donustur);
      setListe(yeni);
      // Aktif düğüm trend çizgisi için çevrimiçi sayısını kaydet
      setCevrimiciGecmis((g) => [...g, yeni.filter((d) => d.cevrimici).length].slice(-9));
    };
    getir();
    const zaman = setInterval(getir, YENILEME_MS);
    return () => {
      iptal = true;
      clearInterval(zaman);
    };
  }, []);

  // Backend'e ulaşılamazsa eski "çevrimiçi" bilgisi sonsuza dek kalmasın
  const dugumler = liste.map((d) => ({
    ...d,
    cevrimici: d.cevrimici && d.sonZaman != null && simdiSn - d.sonZaman <= CEVRIMDISI_SANIYE,
  }));

  return { dugumler, cevrimiciGecmis };
}

// Seçili düğümün son ~2 dk'lık MQ-2 okumaları (eski → yeni). sonOlcum
// (/api/dugumler) verilirse seri ona hizalanır: ondan yeni noktalar atılır,
// eksikse eklenir. Böylece grafiğin son noktası gösterge ve kartla aynıdır.
export function useDumanSerisi(dugum, sonOlcum) {
  const [seri, setSeri] = useState({ dugum: null, veri: [] });

  useEffect(() => {
    if (!dugum) return;
    let iptal = false;
    const getir = async () => {
      const veri = await jsonGetir(
        `/api/gecmis?sensor=duman&dugum=${encodeURIComponent(dugum)}&limit=${DUMAN_SERI}`
      );
      if (!iptal && Array.isArray(veri)) setSeri({ dugum, veri });
    };
    getir();
    const zaman = setInterval(getir, YENILEME_MS);
    return () => {
      iptal = true;
      clearInterval(zaman);
    };
  }, [dugum]);

  // Seçim değişince eski düğümün serisi bir an bile gösterilmesin
  const veri = seri.dugum === dugum ? seri.veri : [];
  if (!sonOlcum) return veri;
  const onceki = veri.filter((o) => o.zaman < sonOlcum.zaman);
  return [...onceki, { zaman: sonOlcum.zaman, deger: sonOlcum.deger }].slice(-DUMAN_SERI);
}
