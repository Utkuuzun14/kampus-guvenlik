import { useState, useEffect } from "react";
import { API } from "../sabitler";

// Seçili düğümün son MQ-2 okumaları (3 sn'de bir yenilenir, eski → yeni)
export default function useDumanGecmis(dugum) {
  const [veri, setVeri] = useState([]);

  useEffect(() => {
    if (!dugum) return;
    let iptal = false;

    const getir = async () => {
      try {
        const cevap = await fetch(
          `${API}/api/gecmis?sensor=duman&dugum=${encodeURIComponent(dugum)}&limit=40`
        );
        if (!cevap.ok) return;
        const gelen = await cevap.json();
        if (!iptal) setVeri(gelen);
      } catch {
        // sessiz geç
      }
    };

    getir();
    const zaman = setInterval(getir, 3000);
    return () => {
      iptal = true;
      clearInterval(zaman);
    };
  }, [dugum]);

  return veri;
}
