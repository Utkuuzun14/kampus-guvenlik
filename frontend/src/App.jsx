import { useState, useEffect } from "react";
import "./App.css";

const API = "http://127.0.0.1:8000";

// Alarm seviyesine göre renk
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

  // Olayları backend'den çek
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

  // Sayfa açılınca ve her 5 saniyede bir yenile
  useEffect(() => {
    olaylariGetir();
    const zamanlayici = setInterval(olaylariGetir, 5000);
    return () => clearInterval(zamanlayici);
  }, []);

  const zamanBicim = (unix) => {
    if (!unix) return "-";
    return new Date(unix * 1000).toLocaleString("tr-TR");
  };

  return (
    <div className="panel">
      <header className="baslik">
        <h1>Kampüs Güvenlik Paneli</h1>
        <span className="alt">IoT Tabanlı Güvenlik İzleme Sistemi</span>
      </header>

      {hata && (
        <div className="hata">
          Backend'e bağlanılamadı ({hata}). Broker ve backend çalışıyor mu?
        </div>
      )}

      <div className="olay-bolum">
        <h2>Son Olaylar ({olaylar.length})</h2>
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
            {olaylar.map((o) => (
              <tr key={o.id}>
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
