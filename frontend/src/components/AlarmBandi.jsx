import { DUGUM_KONUMLARI, SENSOR_AD } from "../sabitler";
import { cumleDuzeni, saatBicim } from "../hesaplar";

// Son 5 dakikadaki kritik olay için alarm bandı. Onay yalnızca arayüzde gizler.
export default function AlarmBandi({ olay, onOnayla }) {
  const konum = DUGUM_KONUMLARI[olay.dugum]?.konum;

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
          <span className="alarm-etiket yanip">● KRİTİK ALARM</span>
          <span className="alarm-saat">{saatBicim(olay.zaman)}</span>
        </div>
        <div className="alarm-baslik">
          {cumleDuzeni(olay.mesaj)}
          {konum && ` — ${konum}`}
        </div>
        <div className="alarm-detay">
          {olay.dugum} · {SENSOR_AD[olay.sensor] ?? olay.sensor} · değer {olay.deger}
        </div>
      </div>
      <button type="button" className="alarm-onay" onClick={onOnayla}>
        Alarmı onayla
      </button>
    </div>
  );
}
