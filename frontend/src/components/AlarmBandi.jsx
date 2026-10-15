import { SENSOR_AD } from "../sabitler";
import { cumleDuzeni, durumu, saatBicim, seviyeAnahtari } from "../hesaplar";
import DurumRozeti from "./DurumRozeti";
import DurumIlerlet from "./DurumIlerlet";

// Çözülmemiş en ağır kritik/yüksek olay için alarm bandı; olay çözülünce kaybolur.
// adet: bant kapsamındaki açık alarm sayısı. konumlar: { dugum: konum adı } (/api/dugumler)
export default function AlarmBandi({ olay, adet, konumlar, onGuncellendi, onDetay }) {
  const konum = konumlar[olay.dugum];
  const kritik = seviyeAnahtari(olay.seviye) === "kritik";

  return (
    <div role="alert" className="alarm-bandi">
      <div className="tarama" />
      <div className="alarm-ikon">
        <svg aria-hidden="true" width="22" height="22" viewBox="0 0 24 24" fill="none"
          stroke="#1a0508" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.07-2.14 0-5.5 3-7 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.15.43-2.29 1-3a2.5 2.5 0 0 0 2.5 2.5z" />
        </svg>
      </div>
      <div className="alarm-metin">
        <div className="alarm-ust">
          <span className={durumu(olay) === "yeni" ? "alarm-etiket yanip" : "alarm-etiket"}>
            ● {kritik ? "KRİTİK" : "YÜKSEK"} ALARM
          </span>
          <span className="alarm-saat">{saatBicim(olay.zaman)}</span>
          {durumu(olay) !== "yeni" && <DurumRozeti olay={olay} />}
          {adet > 1 && <span className="alarm-saat">+{adet - 1} açık alarm</span>}
        </div>
        <button type="button" className="alarm-baslik metin-btn" onClick={() => onDetay(olay)}>
          {cumleDuzeni(olay.mesaj)}
          {konum && ` — ${konum}`}
        </button>
        <div className="alarm-detay">
          {olay.dugum} · {SENSOR_AD[olay.sensor] ?? olay.sensor} · değer {olay.deger}
        </div>
      </div>
      <DurumIlerlet olay={olay} onGuncellendi={onGuncellendi} anaSinif="alarm-onay" />
    </div>
  );
}
