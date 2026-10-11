import { DUGUM_KONUMLARI, SEVIYE_RENK, SENSOR_AD } from "../sabitler";
import { cumleDuzeni, saatBicim, seviyeAnahtari } from "../hesaplar";

// "Duman/gaz eşiği aşıldı (deger=2140)" → "Duman/gaz eşiği aşıldı"
const baslikYap = (mesaj) => cumleDuzeni(String(mesaj ?? "").replace(/\s*\([^)]*\)\s*$/, ""));

const detayYap = (o) => {
  if (o.sensor === "duman") return `${o.dugum} · ${o.deger}`;
  const konum = DUGUM_KONUMLARI[o.dugum]?.konum;
  return `${o.dugum} · ${konum ?? SENSOR_AD[o.sensor] ?? o.sensor}`;
};

// Son 5 olay, zaman çizelgesi biçiminde (olaylar yeni → eski)
export default function OlayAkisi({ olaylar }) {
  const son = olaylar.slice(0, 5);

  return (
    <div className="kart panel-kart akis-kart">
      <span className="bolum-baslik akis-baslik">Son olaylar</span>
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
              <span className="bolum-alt">{detayYap(o)}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
