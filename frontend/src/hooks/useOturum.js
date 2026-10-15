import { useState, useEffect, useCallback } from "react";
import {
  OTURUM_DUSTU, aktifOturum, apiFetch, cikisYap, girisYap, kullaniciGuncelle,
} from "../api";

// Oturum durumu: kayıtlı token açılışta GET /api/ben ile doğrulanır (süresi
// dolmuş ya da pasif yapılmış kullanıcıda 401 → giriş ekranı). Herhangi bir
// istekteki 401 de OTURUM_DUSTU olayıyla buraya ulaşır.
export default function useOturum() {
  const [oturum, setOturum] = useState(aktifOturum);

  useEffect(() => {
    const dustu = () => setOturum(null);
    window.addEventListener(OTURUM_DUSTU, dustu);
    return () => window.removeEventListener(OTURUM_DUSTU, dustu);
  }, []);

  useEffect(() => {
    if (!aktifOturum()) return undefined;
    let iptal = false;
    apiFetch("/api/ben")
      .then(async (cevap) => {
        if (cevap.ok && !iptal) setOturum(kullaniciGuncelle(await cevap.json()));
      })
      .catch(() => {
        // sunucuya ulaşılamadı: kayıtlı oturumla devam, panel bağlantı hatasını gösterir
      });
    return () => {
      iptal = true;
    };
  }, []);

  const giris = useCallback(async (kullaniciAdi, parola, hatirla) => {
    setOturum(await girisYap(kullaniciAdi, parola, hatirla));
  }, []);

  const cikis = useCallback(() => {
    cikisYap();
    setOturum(null);
  }, []);

  return { oturum, giris, cikis };
}
