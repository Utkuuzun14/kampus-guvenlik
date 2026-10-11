import { useState, useEffect, useRef } from "react";
import "./App.css";
import DumanGrafik from "./DumanGrafik";

const API = "http://127.0.0.1:8000";
const WS_URL = "ws://127.0.0.1:8000/ws";

// Seviye değerleri docs/SOZLESMELER.md'den: bilgi < uyari < orta < yuksek < kritik
const BILINEN_SEVIYELER = ["bilgi", "uyari", "orta", "yuksek", "kritik"];

// Türkçe karakterleri ASCII'ye çevirir ("yüksek" → "yuksek")
const asciiye = (metin) =>
  String(metin ?? "")
    .toLocaleLowerCase("tr-TR")
    .replace(/ü/g, "u")
    .replace(/ı/g, "i")
    .replace(/ö/g, "o")
    .replace(/ş/g, "s")
    .replace(/ğ/g, "g")
    .replace(/ç/g, "c");

const rozetSinifi = (seviye) => {
  const anahtar = asciiye(seviye);
  return BILINEN_SEVIYELER.includes(anahtar)
    ? `rozet rozet-${anahtar}`
    : "rozet rozet-bilinmeyen";
};

function App() {
  const [olaylar, setOlaylar] = useState([]);
  const [hata, setHata] = useState(null);
  const [baglanti, setBaglanti] = useState("baglaniyor"); // canli | kopuk | baglaniyor
  const [durum, setDurum] = useState(null);
  const [filtre, setFiltre] = useState("hepsi");
  const [simdi, setSimdi] = useState(() => new Date());
  const wsRef = useRef(null);
  const yenidenBaglanRef = useRef(null);

  // Başlangıçta geçmiş olayları REST ile çek
  const olaylariGetir = async () => {
    try {
      const cevap = await fetch(`${API}/api/olaylar?limit=50`);
      if (!cevap.ok) throw new Error("Sunucu hatası: " + cevap.status);
      const veri = await cevap.json();
      setOlaylar(veri);
      setHata(null);
    } catch (e) {
      setHata(e.message);
    }
  };

  const durumGetir = async () => {
    try {
      const cevap = await fetch(`${API}/api/durum`);
      if (cevap.ok) setDurum(await cevap.json());
    } catch (e) {
      // sessiz geç
    }
  };

  // WebSocket bağlantısı kur (canlı olaylar)
  const wsBaglan = (kapatildiRef) => {
    try {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => setBaglanti("canli");

      ws.onmessage = (olay) => {
        try {
          const mesaj = JSON.parse(olay.data);
          if (mesaj.tip === "olay" && mesaj.veri) {
            setOlaylar((oncekiler) => [mesaj.veri, ...oncekiler].slice(0, 50));
          }
        } catch (e) {
          console.error("WS mesaj çözme hatası:", e);
        }
      };

      ws.onclose = () => {
        setBaglanti("kopuk");
        if (!kapatildiRef.value) {
          yenidenBaglanRef.current = setTimeout(
            () => wsBaglan(kapatildiRef),
            3000
          );
        }
      };

      ws.onerror = () => {
        setBaglanti("kopuk");
        ws.close();
      };
    } catch (e) {
      setBaglanti("kopuk");
    }
  };

  useEffect(() => {
    olaylariGetir();
    durumGetir();
    const durumZaman = setInterval(durumGetir, 5000);
    const kapatildiRef = { value: false };
    wsBaglan(kapatildiRef);
    return () => {
      kapatildiRef.value = true;
      clearInterval(durumZaman);
      if (yenidenBaglanRef.current) clearTimeout(yenidenBaglanRef.current);
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  // Üst bardaki canlı saat (yalnızca görünüm)
  useEffect(() => {
    const saatZaman = setInterval(() => setSimdi(new Date()), 1000);
    return () => clearInterval(saatZaman);
  }, []);

  const zamanBicim = (unix) => {
    if (!unix) return "-";
    return new Date(unix * 1000).toLocaleString("tr-TR");
  };

  // Özet sayılar
  const kritikSayi = olaylar.filter((o) => o.seviye === "kritik").length;
  const yuksekSayi = olaylar.filter((o) => o.seviye === "yuksek").length;
  const sonOlay = olaylar[0] || null;

  const baglantiEtiket = {
    canli: { metin: "Canlı", sinif: "nokta-canli" },
    kopuk: { metin: "Bağlantı yok", sinif: "nokta-kopuk" },
    baglaniyor: { metin: "Bağlanıyor…", sinif: "nokta-baglaniyor" },
  }[baglanti];

  const saatMetni = simdi.toLocaleTimeString("tr-TR");
  const tarihMetni = simdi.toLocaleDateString("tr-TR", {
    weekday: "long", day: "numeric", month: "long", year: "numeric",
  });

  return (
    <>
      <header className="ustbar">
        <div className="ustbar-sol">
          <span className="ustbar-simge" aria-hidden="true">🛡️</span>
          <h1>Kampüs Güvenlik Merkezi</h1>
        </div>
        <div className="ustbar-saat">
          <span className="saat">{saatMetni}</span>
          <span className="tarih">{tarihMetni}</span>
        </div>
        <div className="ustbar-sag">
          <span className="baglanti">
            <span className={`nokta ${baglantiEtiket.sinif}`} />
            {baglantiEtiket.metin}
          </span>
        </div>
      </header>

      <main className="panel">
        <div className="yerlesim">
          {hata && (
            <div className="hata">
              Backend'e bağlanılamadı ({hata}). Broker ve backend çalışıyor mu?
            </div>
          )}

          <section className="ozet">
            <div className="kart ozet-kart toplam-kart">
              <h2 className="kart-baslik">Toplam Olay</h2>
              <div className="kart-sayi">{olaylar.length}</div>
            </div>
            <div className="kart ozet-kart kritik-kart">
              <h2 className="kart-baslik">Kritik</h2>
              <div className="kart-sayi">{kritikSayi}</div>
            </div>
            <div className="kart ozet-kart yuksek-kart">
              <h2 className="kart-baslik">Yüksek</h2>
              <div className="kart-sayi">{yuksekSayi}</div>
            </div>
            <div className="kart ozet-kart">
              <h2 className="kart-baslik">Son Olay</h2>
              <div className="kart-sayi-kucuk">
                {sonOlay ? sonOlay.mesaj : "-"}
              </div>
            </div>
          </section>

          <DumanGrafik />

          <section className="kart dugum-kart">
            <h2 className="kart-baslik">Düğüm Durumu</h2>
            {durum ? (
              <div className="dugum-satir">
                <span
                  className={`nokta ${durum.cevrimici ? "nokta-canli" : "nokta-kopuk"}`}
                />
                <div className="dugum-bilgi">
                  <span>
                    <span className="dugum-ad">dugum1</span> —{" "}
                    {durum.cevrimici ? "Çevrimiçi" : "Çevrimdışı"}
                  </span>
                  {durum.gecen_saniye != null && (
                    <span className="dugum-alt">
                      son veri <span className="mono">{durum.gecen_saniye}</span> sn önce
                    </span>
                  )}
                </div>
              </div>
            ) : (
              <div className="bekleniyor">Veri bekleniyor…</div>
            )}
          </section>

          <section className="kart olay-bolum">
            <div className="olay-ustbar">
              <h2 className="kart-baslik">Son Olaylar</h2>
              <div className="filtreler">
                {["hepsi", "kritik", "yuksek", "orta", "uyari", "bilgi"].map((f) => (
                  <button
                    key={f}
                    className={filtre === f ? "filtre-btn aktif" : "filtre-btn"}
                    onClick={() => setFiltre(f)}
                  >
                    {f}
                  </button>
                ))}
              </div>
            </div>
            <div className="tablo-sarmal">
              <table className="olay-tablo">
                <thead>
                  <tr>
                    <th>Zaman</th>
                    <th>Düğüm</th>
                    <th>Sensör</th>
                    <th>Değer</th>
                    <th>Seviye</th>
                    <th>Mesaj</th>
                  </tr>
                </thead>
                <tbody>
                  {olaylar.length === 0 && (
                    <tr>
                      <td colSpan="6" className="bos">Henüz olay yok.</td>
                    </tr>
                  )}
                  {olaylar.filter((o) => filtre === "hepsi" || o.seviye === filtre).map((o, i) => (
                    <tr key={o.id ?? i}>
                      <td className="mono">{zamanBicim(o.zaman)}</td>
                      <td className="mono">{o.dugum}</td>
                      <td>{o.sensor}</td>
                      <td className="mono">{o.deger}</td>
                      <td>
                        <span className={rozetSinifi(o.seviye)}>{o.seviye}</span>
                      </td>
                      <td>{o.mesaj}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      </main>
    </>
  );
}

export default App;
