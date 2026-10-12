import { SEVIYE_RENK, SENSOR_AD } from "../sabitler";
import { cumleDuzeni, saatBicim, seviyeAnahtari } from "../hesaplar";

// "Duman/gaz eşiği aşıldı (deger=2140)" → "Duman/gaz eşiği aşıldı"
const baslikYap = (mesaj) => cumleDuzeni(String(mesaj ?? "").replace(/\s*\([^)]*\)\s*$/, ""));

const detayYap = (o, konumlar) => {
  if (o.sensor === "duman") return `${o.dugum} · ${o.deger}`;
  const konum = konumlar[o.dugum];
  return `${o.dugum} · ${konum ?? SENSOR_AD[o.sensor] ?? o.sensor}`;
};

const GOSTERILEN = 20;

// Son olaylar, zaman çizelgesi biçiminde (olaylar yeni → eski).
// Liste kartın içinde dikey kayar. konumlar: { dugum: konum adı } (/api/dugumler)
export default function OlayAkisi({ olaylar, konumlar }) {
  const son = olaylar.slice(0, GOSTERILEN);

  return (
    <div className="kart panel-kart akis-kart">
      <span className="bolum-baslik">Son olaylar</span>
      <div className="akis-liste">
        {son.length === 0 && <span className="bolum-alt">Henüz olay yok.</span>}
        {son.map((o, i) => {
          const renk = SEVIYE_RENK[seviyeAnahtari(o.seviye)] ?? "#94a3b8";
          return (
            <div key={o.id ?? i} className="akis-satir">
              <div className="akis-ray">
                <span className="akis-nokta" style={{ "--renk": renk }} />
                {i < son.length - 1 && <span className="akis-cizgi" />}
              </div>
              <div className="akis-icerik">
                <div className="akis-ust">
                  <span className="akis-ad">{baslikYap(o.mesaj)}</span>
                  <span className="kucuk-mono">{saatBicim(o.zaman)}</span>
                </div>
                <span className="bolum-alt">{detayYap(o, konumlar)}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
