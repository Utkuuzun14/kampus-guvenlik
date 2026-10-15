import { useState, useEffect, useId } from "react";
import { KURUM } from "../sabitler";

const hataMetni = (h, kalan) => {
  if (h.durum === 429) {
    return kalan > 0
      ? `Çok fazla hatalı deneme. ${kalan} sn sonra tekrar deneyin.`
      : "Tekrar deneyebilirsiniz.";
  }
  if (h.durum === 401) return "Kullanıcı adı veya parola hatalı.";
  if (h.durum === 0) return "Sunucuya ulaşılamadı. Backend çalışıyor mu?";
  if (h.durum === 422) return "Kullanıcı adı ve parola girin.";
  return h.mesaj || `Giriş yapılamadı (HTTP ${h.durum}).`;
};

function GozIkonu({ acik }) {
  return (
    <svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
      <circle cx="12" cy="12" r="3" />
      {!acik && <line x1="3" y1="3" x2="21" y2="21" />}
    </svg>
  );
}

// Tam ekran giriş. onGiris(kullaniciAdi, parola, hatirla) hata nesnesi fırlatır:
// { durum: HTTP kodu (0: sunucu yok), kalan: 429'da saniye }
export default function GirisEkrani({ onGiris }) {
  const [ad, setAd] = useState("");
  const [parola, setParola] = useState("");
  const [goster, setGoster] = useState(false);
  const [hatirla, setHatirla] = useState(false);
  const [hata, setHata] = useState(null);
  const [kalan, setKalan] = useState(0); // 429 sonrası geri sayım
  const [gonderiliyor, setGonderiliyor] = useState(false);
  const baslikId = useId();
  const hataId = useId();

  useEffect(() => {
    if (kalan <= 0) return undefined;
    const zaman = setTimeout(() => setKalan((k) => k - 1), 1000);
    return () => clearTimeout(zaman);
  }, [kalan]);

  // Kilit sunucuda kullanıcı adı + IP başına: başka bir adla denemek serbest
  const adDegisti = (e) => {
    setAd(e.target.value);
    if (kalan > 0) {
      setKalan(0);
      setHata(null);
    }
  };

  const gonder = async (e) => {
    e.preventDefault();
    if (gonderiliyor || kalan > 0) return;
    setGonderiliyor(true);
    setHata(null);
    try {
      await onGiris(ad.trim(), parola, hatirla);
      // başarılı: App paneli gösterir, bu bileşen kaldırılır
    } catch (h) {
      setHata(h);
      if (h.durum === 429) setKalan(h.kalan || 60);
      if (h.durum === 401) setParola("");
      setGonderiliyor(false);
    }
  };

  return (
    <main className="giris-zemin">
      <form className="giris-kart kart" onSubmit={gonder} aria-labelledby={baslikId}
        aria-describedby={hata ? hataId : undefined}>
        <div className="giris-ust">
          <div className="logo giris-logo">
            <svg aria-hidden="true" width="28" height="28" viewBox="0 0 24 24" fill="none"
              stroke="#04202a" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
              <path d="M9 12l2 2 4-4" />
            </svg>
          </div>
          <div className="giris-baslik">
            <span className="ust-etiket">{KURUM}</span>
            <h1 id={baslikId}>Kampüs Güvenlik · Komuta Merkezi</h1>
          </div>
        </div>

        <label className="durum-alan">
          <span>Kullanıcı adı</span>
          <input type="text" value={ad} onChange={adDegisti}
            autoComplete="username" autoCapitalize="none" spellCheck={false}
            maxLength={64} required autoFocus />
        </label>

        <label className="durum-alan">
          <span>Parola</span>
          <span className="parola-kutu">
            <input type={goster ? "text" : "password"} value={parola}
              onChange={(e) => setParola(e.target.value)} autoComplete="current-password"
              maxLength={256} required />
            <button type="button" className="parola-goster" onClick={() => setGoster((g) => !g)}
              aria-label={goster ? "Parolayı gizle" : "Parolayı göster"} aria-pressed={goster}
              title={goster ? "Parolayı gizle" : "Parolayı göster"}>
              <GozIkonu acik={goster} />
            </button>
          </span>
        </label>

        <label className="giris-hatirla">
          <input type="checkbox" checked={hatirla} onChange={(e) => setHatirla(e.target.checked)} />
          <span>Beni hatırla <span className="kucuk-mono">(bu tarayıcıda açık kalır)</span></span>
        </label>

        {hata && (
          <p id={hataId} role="alert" className="durum-hata">{hataMetni(hata, kalan)}</p>
        )}

        <button type="submit" className="filtre-btn aktif giris-btn"
          disabled={gonderiliyor || kalan > 0 || !ad.trim() || !parola}>
          {gonderiliyor ? "Giriş yapılıyor…" : kalan > 0 ? `Bekleyin (${kalan} sn)` : "Giriş yap"}
        </button>
      </form>
    </main>
  );
}
