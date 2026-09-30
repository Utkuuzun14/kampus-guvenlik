import { useState, useEffect, useRef } from "react";
import "./App.css";

const API = "http://127.0.0.1:8000";
const WS_URL = "ws://127.0.0.1:8000/ws";

const seviyeRenk = {
  bilgi: "#4ade80",
  uyari: "#facc15",
  orta: "#fb923c",
  yuksek: "#f87171",
  kritik: "#ef4444",
};

function App() {
  const [olaylar, setOlaylar] = useState([]);
  const [hata, setHata] = useState(null);
  const [baglanti, setBaglanti] = useState("baglaniyor"); // canli | kopuk | baglaniyor
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
    const kapatildiRef = { value: false };
    wsBaglan(kapatildiRef);
    return () => {
      kapatildiRef.value = true;
      if (yenidenBaglanRef.current) clearTimeout(yenidenBaglanRef.current);
      if (wsRef.current) wsRef.current.close();
    };
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
    canli: { metin: "CANLI", renk: "#4ade80" },
    kopuk: { metin: "BAĞLANTI KOPUK", renk: "#ef4444" },
    baglaniyor: { metin: "Bağlanıyor...", renk: "#facc15" },
  }[baglanti];

  return (
    <div className="panel">
      <header className="baslik">
        <div className="baslik-ust">
          <h1>Kampüs Güvenlik Paneli</h1>
          <span className="durum" style={{ color: baglantiEtiket.renk }}>
            ● {baglantiEtiket.metin}
          </span>
        </div>
        <span className="alt">IoT Tabanlı Güvenlik İzleme Sistemi</span>
      </header>

      {hata && (
        <div className="hata">
          Backend'e bağlanılamadı ({hata}). Broker ve backend çalışıyor mu?
        </div>
      )}

      <div className="ozet">
        <div className="kart">
          <div className="kart-sayi">{olaylar.length}</div>
          <div className="kart-etiket">Toplam Olay</div>
        </div>
        <div className="kart kritik-kart">
          <div className="kart-sayi">{kritikSayi}</div>
          <div className="kart-etiket">Kritik</div>
        </div>
        <div className="kart yuksek-kart">
          <div className="kart-sayi">{yuksekSayi}</div>
          <div className="kart-etiket">Yüksek</div>
        </div>
        <div className="kart">
          <div className="kart-sayi-kucuk">
            {sonOlay ? sonOlay.mesaj : "-"}
          </div>
          <div className="kart-etiket">Son Olay</div>
        </div>
      </div>

      <div className="olay-bolum">
        <h2>Son Olaylar</h2>
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
            {olaylar.map((o, i) => (
              <tr key={o.id ?? i}>
                <td>{zamanBicim(o.zaman)}</td>
                <td>{o.dugum}</td>
                <td>{o.sensor}</td>
                <td>{o.deger}</td>
                <td>
                  <span
                    className="rozet"
                    style={{ background: seviyeRenk[o.seviye] || "#999" }}
                  >
                    {o.seviye}
                  </span>
                </td>
                <td>{o.mesaj}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default App;
