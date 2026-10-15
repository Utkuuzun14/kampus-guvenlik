import { useState, useEffect, useCallback } from "react";
import { API } from "../sabitler";

// Güvenlik modu: GET/PUT /api/ayarlar/mod → { mod, etkin_mod, aciklama }.
// Başka sekmedeki değişiklik ve otomatik modda saatle değişen etkin mod
// WebSocket "mod" mesajıyla gelir; App onu `uygula` ile buraya iletir.
export default function useGuvenlikModu() {
  const [bilgi, setBilgi] = useState(null);
  const [hata, setHata] = useState(null);
  const [kaydediliyor, setKaydediliyor] = useState(false);

  const yenile = useCallback(async () => {
    try {
      const cevap = await fetch(`${API}/api/ayarlar/mod`);
      if (cevap.ok) setBilgi(await cevap.json());
    } catch {
      // sessiz geç; WS yeniden bağlanınca tekrar denenir
    }
  }, []);

  useEffect(() => {
    yenile();
  }, [yenile]);

  const degistir = useCallback(async (mod) => {
    setKaydediliyor(true);
    setHata(null);
    try {
      const cevap = await fetch(`${API}/api/ayarlar/mod`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mod }),
      });
      if (!cevap.ok) throw new Error(`Sunucu hatası: ${cevap.status}`);
      setBilgi(await cevap.json());
    } catch (e) {
      // Seçici sunucudaki değere döner (bilgi değişmedi)
      setHata(e.message === "Failed to fetch" ? "Sunucuya ulaşılamadı." : e.message);
    } finally {
      setKaydediliyor(false);
    }
  }, []);

  return { bilgi, hata, kaydediliyor, degistir, uygula: setBilgi, yenile };
}
