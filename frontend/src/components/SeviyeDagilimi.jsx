import { SEVIYE_AD, SEVIYE_RENK } from "../sabitler";
import { seviyeSayilari } from "../hesaplar";

const SIRA = ["kritik", "yuksek", "orta", "uyari", "bilgi"];

export default function SeviyeDagilimi({ olaylar, simdiSn }) {
  const sayilar = seviyeSayilari(olaylar, simdiSn);
  const enCok = Math.max(1, ...Object.values(sayilar));

  return (
    <div className="kart panel-kart">
      <div className="baslik-grup">
        <span className="bolum-baslik">Seviye dağılımı</span>
        <span className="bolum-alt">Son 7 gün</span>
      </div>
      {SIRA.map((s) => (
        <div key={s} className="dagilim-satir">
          <div className="dagilim-ust">
            <span>{SEVIYE_AD[s]}</span>
            <span className="mono">{sayilar[s]}</span>
          </div>
          <div className="dagilim-ray">
            <div
              className="dagilim-bar"
              style={{
                background: SEVIYE_RENK[s],
                width: sayilar[s] ? `${Math.max(3, Math.round((sayilar[s] / enCok) * 100))}%` : 0,
              }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}
