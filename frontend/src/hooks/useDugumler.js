import { useState, useEffect, useCallback } from "react";
import { API, CEVRIMDISI_SANIYE } from "../sabitler";

// Tek kaynak: /api/dugumler. Düğüm listesi, konum adı, çevrimiçi durumu ve son
// değerler buradan gelir; harita, detay kartı ve "Aktif düğüm" kartı aynı
// listeyi okur. Duman serisi (gösterge + küçük grafik) yalnızca seçili düğüm
// için ayrıca çekilir (useDumanSerisi).
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

  // WebSocket'ten gelen olay bir sonraki yoklamayı beklemeden yansısın
  const okumaEkle = useCallback((olay) => {
    if (!olay?.dugum || olay.zaman == null) return;
    setListe((onceki) =>
      onceki.map((d) => {
        if (d.id !== olay.dugum) return d;
        if (olay.sensor === "durum") return { ...d, cevrimici: olay.deger !== 0 };
        if (!(olay.sensor in { duman: 1, hareket: 1, alev: 1 })) return d;
        return {
          ...d,
          veriYok: false,
          cevrimici: true,
          sonZaman: Math.max(d.sonZaman ?? 0, olay.zaman),
          [olay.sensor]: { deger: olay.deger, zaman: olay.zaman },
        };
      })
    );
  }, []);

  // Backend'e ulaşılamazsa eski "çevrimiçi" bilgisi sonsuza dek kalmasın
  const dugumler = liste.map((d) => ({
    ...d,
    cevrimici: d.cevrimici && d.sonZaman != null && simdiSn - d.sonZaman <= CEVRIMDISI_SANIYE,
  }));

  return { dugumler, cevrimiciGecmis, okumaEkle };
}

// Seçili düğümün son ~2 dk'lık MQ-2 okumaları (eski → yeni)
export function useDumanSerisi(dugum) {
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
  return seri.dugum === dugum ? seri.veri : [];
}
