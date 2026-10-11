import { useState, useEffect, useCallback } from "react";
import { API, CEVRIMDISI_SANIYE } from "../sabitler";

// Tek kaynak: her düğümün sensör okumaları. Gösterge, küçük grafik, harita
// detay kartı ve düğüm durumu hep buradan okur; böylece aynı anda güncellenir.
const DUMAN_SERI = 40; // ~2 dk (3 sn aralık)
const LIMIT = { duman: DUMAN_SERI, hareket: 1, alev: 1 };
const SENSORLER = Object.keys(LIMIT);

async function okumalariGetir(sensor, dugum) {
  try {
    const cevap = await fetch(
      `${API}/api/gecmis?sensor=${sensor}&dugum=${encodeURIComponent(dugum)}&limit=${LIMIT[sensor]}`
    );
    if (!cevap.ok) return null;
    return await cevap.json(); // eski → yeni
  } catch {
    return null;
  }
}

// İki okuma listesini zamana göre birleştirir (aynı zaman damgası tek kayıt)
function birlestir(eski = [], yeni = [], sinir) {
  const harita = new Map();
  for (const o of [...eski, ...yeni]) harita.set(o.zaman, o);
  return [...harita.values()].sort((a, b) => a.zaman - b.zaman).slice(-sinir);
}

export default function useDugumler(dugumIdleri, simdiSn) {
  // okumalar: { [dugum]: { duman: [...], hareket: [...], alev: [...] } }
  const [okumalar, setOkumalar] = useState({});
  const [cevrimiciGecmis, setCevrimiciGecmis] = useState([]);
  const anahtar = dugumIdleri.join(",");

  // WebSocket'ten gelen olay da bir sensör okumasıdır: anında ekle
  const okumaEkle = useCallback((olay) => {
    if (!olay?.dugum || !LIMIT[olay.sensor] || olay.zaman == null) return;
    setOkumalar((onceki) => {
      const dugum = onceki[olay.dugum] ?? {};
      const yeni = { zaman: olay.zaman, deger: olay.deger, dugum: olay.dugum, sensor: olay.sensor };
      return {
        ...onceki,
        [olay.dugum]: {
          ...dugum,
          [olay.sensor]: birlestir(dugum[olay.sensor], [yeni], LIMIT[olay.sensor]),
        },
      };
    });
  }, []);

  useEffect(() => {
    if (!anahtar) return;
    const idler = anahtar.split(",");
    let iptal = false;

    const getir = async () => {
      const gelen = {};
      await Promise.all(
        idler.map(async (id) => {
          const listeler = await Promise.all(SENSORLER.map((s) => okumalariGetir(s, id)));
          gelen[id] = Object.fromEntries(SENSORLER.map((s, i) => [s, listeler[i]]));
        })
      );
      if (iptal) return;
      setOkumalar((onceki) => {
        const sonuc = { ...onceki };
        for (const id of idler) {
          const eski = onceki[id] ?? {};
          sonuc[id] = Object.fromEntries(
            SENSORLER.map((s) => [
              s,
              gelen[id][s] ? birlestir(eski[s], gelen[id][s], LIMIT[s]) : eski[s] ?? [],
            ])
          );
        }
        return sonuc;
      });
      // Aktif düğüm trend çizgisi için çevrimiçi sayısını kaydet
      const anSn = Math.floor(Date.now() / 1000);
      const sayi = idler.filter((id) => {
        const son = sonZamanBul(gelen[id]);
        return son != null && anSn - son <= CEVRIMDISI_SANIYE;
      }).length;
      setCevrimiciGecmis((g) => [...g, sayi].slice(-9));
    };

    getir();
    const zaman = setInterval(getir, 3000);
    return () => {
      iptal = true;
      clearInterval(zaman);
    };
  }, [anahtar]);

  // Türetilmiş düğüm durumu (her render'da aynı okumalardan hesaplanır)
  const dugumler = {};
  for (const id of dugumIdleri) {
    const o = okumalar[id] ?? {};
    const sonZaman = sonZamanBul(o);
    dugumler[id] = {
      id,
      dumanSeri: o.duman ?? [],
      duman: o.duman?.at(-1) ?? null,
      hareket: o.hareket?.at(-1) ?? null,
      alev: o.alev?.at(-1) ?? null,
      sonZaman,
      cevrimici: sonZaman != null && simdiSn - sonZaman <= CEVRIMDISI_SANIYE,
    };
  }

  return { dugumler, cevrimiciGecmis, okumaEkle };
}

function sonZamanBul(okuma) {
  const zamanlar = SENSORLER.map((s) => okuma?.[s]?.at(-1)?.zaman ?? 0);
  const son = Math.max(0, ...zamanlar);
  return son || null;
}
