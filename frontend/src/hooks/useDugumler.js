import { useState, useEffect } from "react";
import { API, CEVRIMDISI_SANIYE } from "../sabitler";

const SENSORLER = ["duman", "hareket", "alev"];

async function sonOkuma(sensor, dugum) {
  try {
    const cevap = await fetch(
      `${API}/api/gecmis?sensor=${sensor}&dugum=${encodeURIComponent(dugum)}&limit=1`
    );
    if (!cevap.ok) return null;
    const veri = await cevap.json();
    return veri.length ? veri[veri.length - 1] : null;
  } catch {
    return null;
  }
}

// Bilinen düğümlerin son sensör okumalarını 5 sn'de bir çeker.
// Çevrimiçi kuralı backend /api/durum ile aynı: son veri ≤ CEVRIMDISI_SANIYE.
export default function useDugumler(dugumIdleri) {
  const [dugumler, setDugumler] = useState({});
  const [cevrimiciGecmis, setCevrimiciGecmis] = useState([]);
  const anahtar = dugumIdleri.join(",");

  useEffect(() => {
    if (!anahtar) return;
    const idler = anahtar.split(",");
    let iptal = false;

    const getir = async () => {
      const simdiSn = Math.floor(Date.now() / 1000);
      const sonuc = {};
      await Promise.all(
        idler.map(async (id) => {
          const okumalar = await Promise.all(SENSORLER.map((s) => sonOkuma(s, id)));
          const [duman, hareket, alev] = okumalar;
          const sonZaman = Math.max(0, ...okumalar.map((o) => o?.zaman ?? 0)) || null;
          sonuc[id] = {
            id,
            duman,
            hareket,
            alev,
            sonZaman,
            cevrimici: sonZaman != null && simdiSn - sonZaman <= CEVRIMDISI_SANIYE,
          };
        })
      );
      if (iptal) return;
      setDugumler(sonuc);
      const sayi = Object.values(sonuc).filter((d) => d.cevrimici).length;
      setCevrimiciGecmis((g) => [...g, sayi].slice(-9));
    };

    getir();
    const zaman = setInterval(getir, 5000);
    return () => {
      iptal = true;
      clearInterval(zaman);
    };
  }, [anahtar]);

  return { dugumler, cevrimiciGecmis };
}
