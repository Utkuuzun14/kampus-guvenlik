import { useState, useEffect, useRef } from "react";
import "./App.css";
import SolMenu from "./components/SolMenu";
import UstBar from "./components/UstBar";
import AlarmBandi from "./components/AlarmBandi";
import OzetKartlari from "./components/OzetKartlari";
import VeriHatti from "./components/VeriHatti";
import KampusHaritasi from "./components/KampusHaritasi";
import DumanGostergesi from "./components/DumanGostergesi";
import OlayAkisi from "./components/OlayAkisi";
import IsiHaritasi from "./components/IsiHaritasi";
import SeviyeDagilimi from "./components/SeviyeDagilimi";
import OlayTablosu from "./components/OlayTablosu";
import useDugumler, { useDumanSerisi } from "./hooks/useDugumler";
import {
  API, WS_URL, ESIK_DUMAN_VARSAYILAN, TEHDIT_PENCERE_SN, haritadaMi,
} from "./sabitler";
import {
  seviyeAnahtari, olayKimligi, sonKritikOlay, tehditHesapla, pencereIcinde,
} from "./hesaplar";

const ANALITIK_LIMIT = 1000;

function App() {
  const [olaylar, setOlaylar] = useState([]);
  const [analitik, setAnalitik] = useState([]); // ısı haritası, özet kartları vb. için geniş liste
  const [hata, setHata] = useState(null);
  const [baglanti, setBaglanti] = useState("baglaniyor"); // canli | kopuk | baglaniyor
  const [durum, setDurum] = useState(null);
  const [apiDurum, setApiDurum] = useState("bekliyor"); // ok | hata | bekliyor
  const [mqttDurum, setMqttDurum] = useState("bekliyor"); // backend ↔ broker: ok | hata | bekliyor
  const [dbDurum, setDbDurum] = useState("bekliyor"); // ok | hata | bekliyor
  const [filtre, setFiltre] = useState("hepsi");
  const [onaylananKimlik, setOnaylananKimlik] = useState(null);
  const [seciliDugum, setSeciliDugum] = useState(null);
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
      const saglik = cevap.ok ? await cevap.json() : null;
      setMqttDurum(saglik?.mqtt === "bagli" ? "ok" : saglik?.mqtt === "kopuk" ? "hata" : "bekliyor");
    } catch {
      setApiDurum("hata");
      setMqttDurum("bekliyor"); // backend yoksa broker durumu bilinmiyor
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

  // ---- Türetilmiş görünüm verileri ----
  const simdiSn = Math.floor(simdi.getTime() / 1000);
  const kaynak = analitik.length >= olaylar.length ? analitik : olaylar;
  const esik = durum?.esik_duman ?? ESIK_DUMAN_VARSAYILAN;

  // Düğüm listesi /api/dugumler'den (alarm üretmemiş ve hiç veri göndermemiş düğümler dahil)
  const { dugumler: dugumListesi, cevrimiciGecmis } = useDugumler(simdiSn);
  const dugumOzet = {
    toplam: dugumListesi.length,
    cevrimici: dugumListesi.filter((d) => d.cevrimici).length,
    cevrimdisi: dugumListesi.filter((d) => !d.cevrimici && !d.veriYok).map((d) => d.id),
    veriYok: dugumListesi.filter((d) => d.veriYok).map((d) => d.id),
  };
  const konumlar = Object.fromEntries(dugumListesi.map((d) => [d.id, d.konum]));

  // Son 5 dk'da kritik olayı olan düğümler haritada alarm gösterir
  const alarmdakiler = new Set(
    pencereIcinde(kaynak, simdiSn, TEHDIT_PENCERE_SN)
      .filter((o) => seviyeAnahtari(o.seviye) === "kritik")
      .map((o) => o.dugum)
  );
  // Gösterge ve harita detayı yalnızca haritadaki (konumu tanımlı) düğümler için.
  // Seçim yoksa: önce alarmdaki düğüm, yoksa ilk düğüm
  const haritadakiler = dugumListesi.map((d) => d.id).filter(haritadaMi);
  const gosterilenDugum =
    (seciliDugum && haritadakiler.includes(seciliDugum) && seciliDugum) ||
    haritadakiler.find((id) => alarmdakiler.has(id)) ||
    haritadakiler[0] ||
    null;
  // Gösterge ve küçük grafik haritada seçili düğümü gösterir. Gösterge değeri,
  // detay kartıyla aynı son ölçüm (/api/dugumler); grafik onun geçmişi.
  const sonDuman = dugumListesi.find((d) => d.id === gosterilenDugum)?.duman ?? null;
  const dumanSeri = useDumanSerisi(gosterilenDugum, sonDuman);
  const dumanSon60 = dumanSeri.filter((o) => simdiSn - o.zaman <= 60);

  const tehdit = tehditHesapla(kaynak, simdiSn, onaylananKimlik);
  const kritikOlay = sonKritikOlay(kaynak, simdiSn);
  const alarmGoster = kritikOlay && olayKimligi(kritikOlay) !== onaylananKimlik;

  // Broker ışığı: backend'in MQTT bağlantısı (/api/saglik); tek düğümün kopması etkilemez
  const brokerDurum = mqttDurum;
  const isiklar = [
    {
      ad: "Broker",
      durum: brokerDurum,
      not: brokerDurum === "hata" ? "bağlantı yok" : null,
      ipucu: "Backend'in Mosquitto bağlantısı (/api/saglik → mqtt)",
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

  return (
    <div className="kabuk">
      <SolMenu />

      <div className="icerik">
        <UstBar simdi={simdi} tehdit={tehdit} isiklar={isiklar} baglanti={baglanti} />

        {alarmGoster && (
          <AlarmBandi
            olay={kritikOlay}
            konumlar={konumlar}
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

        <section id="harita" className="harita-satiri">
          <KampusHaritasi
            dugumler={dugumListesi}
            alarmdakiler={alarmdakiler}
            secili={gosterilenDugum}
            onSec={setSeciliDugum}
            simdiSn={simdiSn}
          />
          <div className="sag-sutun">
            <DumanGostergesi son={sonDuman?.deger ?? null} veri={dumanSon60} esik={esik} dugum={gosterilenDugum} />
            <OlayAkisi olaylar={olaylar} konumlar={konumlar} />
          </div>
        </section>

        <section id="analitik" className="satir-2">
          <IsiHaritasi olaylar={analitik} simdiSn={simdiSn} limit={ANALITIK_LIMIT} />
          <SeviyeDagilimi olaylar={analitik} simdiSn={simdiSn} />
        </section>

        <OlayTablosu olaylar={olaylar} filtre={filtre} onFiltre={setFiltre} simdi={simdi} />

        <footer className="altbilgi">
          <span>ESP32-S2 → MQTT (QoS 1, LWT) → Mosquitto → FastAPI → SQLite → React</span>
          <span className="mono">kampus/guvenlik/#</span>
        </footer>
      </div>
    </div>
  );
}

export default App;
