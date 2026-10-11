import { KURUM } from "../sabitler";

const BAGLANTI = {
  canli: { metin: "Canlı", durum: "canli" },
  kopuk: { metin: "Bağlantı yok", durum: "hata" },
  baglaniyor: { metin: "Bağlanıyor…", durum: "uyari" },
};

// isiklar: [{ ad, durum: "ok" | "uyari" | "hata" | "bekliyor", not?, ipucu? }]
export default function UstBar({ simdi, tehdit, isiklar, baglanti }) {
  const saat = simdi.toLocaleTimeString("tr-TR", {
    hour: "2-digit", minute: "2-digit", second: "2-digit",
  });
  const tarih = simdi.toLocaleDateString("tr-TR", {
    day: "numeric", month: "long", year: "numeric", weekday: "long",
  });
  const ws = BAGLANTI[baglanti];

  return (
    <header className="ustbar">
      <div className="ustbar-baslik">
        <div className="ust-etiket">{KURUM}</div>
        <h1>Komuta Merkezi</h1>
      </div>

      <div className="ustbar-sag">
        <div className={`tehdit tehdit-${tehdit.tip}`}>
          <span className="tehdit-etiket">Tehdit seviyesi</span>
          <span className="tehdit-metin">{tehdit.metin}</span>
        </div>

        <div className="isiklar">
          {isiklar.map((i) => (
            <span key={i.ad} className="isik" title={i.ipucu}>
              <span className={`isik-nokta isik-${i.durum}`} />
              {i.ad}
              {i.not && <span className="isik-not">{i.not}</span>}
            </span>
          ))}
          <span className={`isik isik-ws isik-ws-${ws.durum}`}>
            <span className={`isik-nokta isik-${ws.durum}`} />
            {ws.metin}
          </span>
        </div>

        <div className="saat-kutu">
          <span className="saat">{saat}</span>
          <span className="tarih">{tarih}</span>
        </div>
      </div>
    </header>
  );
}
