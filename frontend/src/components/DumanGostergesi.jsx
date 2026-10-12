import DumanGrafik from "../DumanGrafik";

const OLCEK = 3000;
const YAY = "M 20 110 A 90 90 0 0 1 200 110";

// Yay üzerindeki oran (0–1) için merkezden r uzaklıktaki nokta
const yayNoktasi = (oran, r) => {
  const aci = Math.PI * (1 - oran);
  return [110 + r * Math.cos(aci), 110 - r * Math.sin(aci)];
};

const sinirla = (v) => Math.min(1, Math.max(0, v));

// son: düğümün son MQ-2 ölçümü (/api/dugumler; harita detay kartıyla aynı kaynak)
// veri: son 60 sn'lik MQ-2 okumaları (eski → yeni), tepe kutusu ve grafik için
export default function DumanGostergesi({ son, veri, esik, dugum }) {
  const oran = son == null ? 0 : sinirla(son / OLCEK);
  const esikOran = sinirla(esik / OLCEK);
  const [x1, y1] = yayNoktasi(esikOran, 80);
  const [x2, y2] = yayNoktasi(esikOran, 100);
  const asildi = son != null && son > esik;

  const tepe = veri.length ? Math.max(...veri.map((o) => o.deger)) : null;
  const asimSayisi = veri.filter((o) => o.deger > esik).length;
  const grafikUst = Math.max(OLCEK, tepe ?? 0);

  return (
    <div className="kart panel-kart gosterge-kart">
      <div className="gosterge-ust">
        <span className="bolum-baslik">Duman seviyesi</span>
        <span className="kucuk-mono">MQ-2 · {dugum ?? "—"}</span>
      </div>

      <div className="gosterge">
        <svg role="img" viewBox="0 0 220 130" width="100%" height="100%"
          aria-label={`Duman göstergesi: ${son ?? "veri yok"}, eşik ${esik}, ölçek 0 ile ${OLCEK} arası`}>
          <path d={YAY} fill="none" stroke="#16213a" strokeWidth="16" strokeLinecap="round" />
          <path d={YAY} fill="none" stroke="rgba(244,63,94,.35)" strokeWidth="16" pathLength="100"
            strokeDasharray={`${100 - esikOran * 100} 100`} strokeDashoffset={-esikOran * 100} />
          {son != null && (
            <path className="gosterge-deger" d={YAY} fill="none"
              stroke={asildi ? "#f43f5e" : "#22d3ee"} strokeWidth="16" strokeLinecap="round"
              pathLength="100" strokeDasharray={`${oran * 100} 100`} />
          )}
          <line x1={x1} y1={y1} x2={x2} y2={y2} stroke="#f43f5e" strokeWidth="3" strokeLinecap="round" />
        </svg>
        <div className="gosterge-orta">
          <span className={asildi ? "gosterge-sayi asildi" : "gosterge-sayi"}>{son ?? "—"}</span>
          <span className="gosterge-esik">eşik {esik}</span>
        </div>
      </div>
      <div className="gosterge-olcek"><span>0</span><span>{OLCEK}</span></div>

      <div className={asimSayisi ? "tepe-kutu" : "tepe-kutu sakin"}>
        {tepe == null ? (
          "Son 60 sn'de veri yok"
        ) : (
          <>
            Son 60 sn'de tepe değer <span className="mono kalin">{tepe}</span>
            {" · "}
            {asimSayisi ? `eşik ${asimSayisi} kez aşıldı` : "eşik aşılmadı"}
          </>
        )}
      </div>

      <DumanGrafik veri={veri} esik={esik} ust={grafikUst} />
    </div>
  );
}
