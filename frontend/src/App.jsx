import { useState, useEffect, useRef, useMemo } from "react";
import "./App.css";
import DumanGrafik from "./DumanGrafik";
import SolMenu from "./components/SolMenu";
import UstBar from "./components/UstBar";
import AlarmBandi from "./components/AlarmBandi";
import OzetKartlari from "./components/OzetKartlari";
import VeriHatti from "./components/VeriHatti";
import useDugumler from "./hooks/useDugumler";
import { API, WS_URL, ESIK_DUMAN_VARSAYILAN } from "./sabitler";
import {
  seviyeAnahtari, olayKimligi, sonKritikOlay, tehditHesapla,
} from "./hesaplar";

const ANALITIK_LIMIT = 1000;

function App() {
  const [olaylar, setOlaylar] = useState([]);
  const [analitik, setAnalitik] = useState([]); // ısı haritası, özet kartları vb. için geniş liste
  const [hata, setHata] = useState(null);
  const [baglanti, setBaglanti] = useState("baglaniyor"); // canli | kopuk | baglaniyor
  const [durum, setDurum] = useState(null);
  const [apiDurum, setApiDurum] = useState("bekliyor"); // ok | hata | bekliyor
  const [dbDurum, setDbDurum] = useState("bekliyor"); // ok | hata | bekliyor
  const [filtre, setFiltre] = useState("hepsi");
  const [onaylananKimlik, setOnaylananKimlik] = useState(null);
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
      setDbDurum("ok");
    } catch (e) {
      setHata(e.message);
      setDbDurum("hata");
    }
  };

  // Analitik için daha geniş olay listesi (dakikada bir yenilenir)
  const analitikGetir = async () => {
    try {
      const cevap = await fetch(`${API}/api/olaylar?limit=${ANALITIK_LIMIT}`);
      if (!cevap.ok) throw new Error("Sunucu hatası: " + cevap.status);
      setAnalitik(await cevap.json());
      setDbDurum("ok");
    } catch {
      setDbDurum("hata");
    }
  };

  const durumGetir = async () => {
    try {
      const cevap = await fetch(`${API}/api/durum`);
      if (cevap.ok) setDurum(await cevap.json());
    } catch {
      // sessiz geç
    }
  };

  const saglikGetir = async () => {
    try {
      const cevap = await fetch(`${API}/api/saglik`);
      setApiDurum(cevap.ok ? "ok" : "hata");
    } catch {
      setApiDurum("hata");
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
            setAnalitik((oncekiler) => [mesaj.veri, ...oncekiler].slice(0, ANALITIK_LIMIT));
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
    } catch {
      setBaglanti("kopuk");
    }
  };

  useEffect(() => {
    olaylariGetir();
    analitikGetir();
    durumGetir();
    saglikGetir();
    const durumZaman = setInterval(() => {
      durumGetir();
      saglikGetir();
    }, 5000);
    const analitikZaman = setInterval(analitikGetir, 60000);
    const kapatildiRef = { value: false };
    wsBaglan(kapatildiRef);
    return () => {
      kapatildiRef.value = true;
      clearInterval(durumZaman);
      clearInterval(analitikZaman);
      if (yenidenBaglanRef.current) clearTimeout(yenidenBaglanRef.current);
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  // Canlı saat (yalnızca görünüm; 5 dk'lık pencereler de buna göre kayar)
  useEffect(() => {
    const saatZaman = setInterval(() => setSimdi(new Date()), 1000);
    return () => clearInterval(saatZaman);
  }, []);

  const zamanBicim = (unix) => {
    if (!unix) return "-";
    return new Date(unix * 1000).toLocaleString("tr-TR");
  };

  // ---- Türetilmiş görünüm verileri ----
  const simdiSn = Math.floor(simdi.getTime() / 1000);
  const kaynak = analitik.length >= olaylar.length ? analitik : olaylar;
  const esik = durum?.esik_duman ?? ESIK_DUMAN_VARSAYILAN;

  // Yalnızca backend'den görülen düğümler
  const dugumIdleri = useMemo(() => {
    const idler = new Set(kaynak.map((o) => o.dugum).filter(Boolean));
    if (durum?.son_gorulme != null) idler.add("dugum1"); // /api/durum dugum1'e bakar
    return [...idler].sort();
  }, [kaynak, durum?.son_gorulme]);
  const { dugumler, cevrimiciGecmis } = useDugumler(dugumIdleri);
  const dugumListesi = dugumIdleri.map((id) => dugumler[id] ?? { id, cevrimici: false });
  const dugumOzet = {
    toplam: dugumListesi.length,
    cevrimici: dugumListesi.filter((d) => d.cevrimici).length,
    cevrimdisi: dugumListesi.filter((d) => !d.cevrimici).map((d) => d.id),
  };

  const tehdit = tehditHesapla(kaynak, simdiSn, onaylananKimlik);
  const kritikOlay = sonKritikOlay(kaynak, simdiSn);
  const alarmGoster = kritikOlay && olayKimligi(kritikOlay) !== onaylananKimlik;

  const brokerDurum = durum == null ? "bekliyor" : durum.cevrimici ? "ok" : "uyari";
  const isiklar = [
    {
      ad: "Broker",
      durum: brokerDurum,
      not: brokerDurum === "uyari" ? "veri yok" : null,
      ipucu: "Son 30 sn içinde düğümden veri geldi mi (dolaylı gösterge)",
    },
    { ad: "API", durum: apiDurum, ipucu: "/api/saglik" },
    { ad: "Veritabanı", durum: dbDurum, ipucu: "/api/olaylar" },
  ];

  const hatDurumlari = {
    esp: dugumOzet.toplam === 0 ? "bekliyor" : dugumOzet.cevrimici > 0 ? "ok" : "uyari",
    mqtt: brokerDurum,
    api: apiDurum,
    db: dbDurum,
    panel: baglanti === "canli" ? "ok" : baglanti === "kopuk" ? "hata" : "uyari",
  };

  const rozetSinifi = (seviye) => {
    const anahtar = seviyeAnahtari(seviye);
    return anahtar ? `rozet rozet-${anahtar}` : "rozet rozet-bilinmeyen";
  };

  return (
    <div className="kabuk">
      <SolMenu />

      <div className="icerik">
        <UstBar simdi={simdi} tehdit={tehdit} isiklar={isiklar} baglanti={baglanti} />

        {alarmGoster && (
          <AlarmBandi
            olay={kritikOlay}
            onOnayla={() => setOnaylananKimlik(olayKimligi(kritikOlay))}
          />
        )}

        {hata && (
          <div className="hata">
            Backend'e bağlanılamadı ({hata}). Broker ve backend çalışıyor mu?
          </div>
        )}

        <OzetKartlari
          olaylar={kaynak}
          simdi={simdi}
          esik={esik}
          dugumOzet={dugumOzet}
          cevrimiciGecmis={cevrimiciGecmis}
        />

        <VeriHatti durumlar={hatDurumlari} />

        {/* Geçici: B aşamasında harita + gösterge ile değişecek */}
        <div id="harita">
          <DumanGrafik />
        </div>

        {/* Geçici: C aşamasında OlayTablosu bileşenine taşınacak */}
        <section id="olaylar" className="kart bolum olay-bolum">
          <div className="olay-ustbar">
            <span className="bolum-baslik">Son Olaylar</span>
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

        <footer className="altbilgi">
          <span>ESP32-S2 → MQTT (QoS 1, LWT) → Mosquitto → FastAPI → SQLite → React</span>
          <span className="mono">kampus/guvenlik/#</span>
        </footer>
      </div>
    </div>
  );
}

export default App;
