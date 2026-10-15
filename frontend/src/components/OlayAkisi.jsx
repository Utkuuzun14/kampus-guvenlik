import { SEVIYE_RENK, SENSOR_AD } from "../sabitler";
import { akistaMi, cumleDuzeni, saatBicim, seviyeAnahtari } from "../hesaplar";
import DurumRozeti from "./DurumRozeti";
import DurumIlerlet from "./DurumIlerlet";

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
// Orta+ olaylarda durum rozeti ve sıradaki adımın butonu; başlık detayı açar.
export default function OlayAkisi({ olaylar, konumlar, onGuncellendi, onDetay }) {
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
                  <button type="button" className="akis-ad metin-btn" onClick={() => onDetay(o)}>
                    {baslikYap(o.mesaj)}
                  </button>
                  <span className="kucuk-mono">{saatBicim(o.zaman)}</span>
                </div>
                <span className="bolum-alt">{detayYap(o, konumlar)}</span>
                {akistaMi(o) && (
                  <div className="akis-durum">
                    <DurumRozeti olay={o} />
                    <DurumIlerlet olay={o} onGuncellendi={onGuncellendi} />
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
