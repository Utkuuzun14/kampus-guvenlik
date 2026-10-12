import { useState } from "react";
import { DUGUM_KONUMLARI } from "../sabitler";
import { KUS_KROKI, KUS_FOTO, PERSP_KROKI, PERSP_FOTO } from "./haritaKatmanlari";

// Harita: docs/tasarim/KomutaMerkezi.dc.html. 2 açı × 2 zemin = 4 görünüm.
// Her açının kendi viewBox'ı (fotoğraf pikseli) ve Mosquitto konumu var; zemin
// "kroki" tamamen vektör, "foto" fotoğraf + SVG katmanı. Statik katmanlar
// haritaKatmanlari.jsx'te, canlı katman (hale, akış çizgileri, Mosquitto,
// düğümler) burada çizilir.
const ACILAR = {
  kus: {
    ad: "Kuşbakışı",
    vb: { x: 15, y: 0, gen: 1985, yuk: 1230 },
    konumlar: DUGUM_KONUMLARI.kusbakisi,
    hub: { x: 777, y: 246, etiketY: 317 },
    haleR: 120,
    zemin: {
      kroki: {
        katman: KUS_KROKI, haleSaydam: 0.18,
        aria: "Kampüs krokisi (hava fotoğrafından çizilmiş): ana bina A Kanadı, Rotunda ve B Kanadı, T şeklinde kapalı yol, üç halı saha, spor kompleksi, otopark, park, yurt ve sanayi bölgesi",
      },
      foto: {
        katman: KUS_FOTO, haleSaydam: 0.16, foto: "/kampus-hava.jpg",
        aria: "Kampüs hava görünümü: ana bina (A Kanadı, Rotunda, B Kanadı), kapalı yürüyüş yolu, halı sahalar, spor kompleksi, otopark, park ve yurt",
      },
    },
  },
  persp: {
    ad: "Perspektif",
    vb: { x: 0, y: 60, gen: 2000, yuk: 1239 },
    konumlar: DUGUM_KONUMLARI.perspektif,
    hub: { x: 1292, y: 405, etiketY: 477 },
    haleR: 125,
    zemin: {
      kroki: {
        katman: PERSP_KROKI, haleSaydam: 0.18,
        aria: "Kampüs perspektif krokisi: A Kanadı, Rotunda ve B Kanadı cepheleriyle, ana giriş, spor kompleksi, halı sahalar, kapalı yol ve otopark",
      },
      foto: {
        katman: PERSP_FOTO, haleSaydam: 0.16, foto: "/kampus-perspektif.jpg",
        aria: "Kampüs perspektif görünümü: A Kanadı, Rotunda ve B Kanadı cepheleri, ana giriş, spor kompleksi, halı sahalar, kapalı yürüyüş yolu ve otopark",
      },
    },
  },
};
const ZEMINLER = { kroki: "Kroki", foto: "Fotoğraf" };

const TIP = {
  alarm: { renk: "#f43f5e", durum: "Alarm", nokta: "n-kirmizi" },
  ok: { renk: "#34d399", durum: "Çevrimiçi", nokta: "n-yesil" },
  off: { renk: "#64748b", durum: "Çevrimdışı", nokta: "" },
  yok: { renk: "#64748b", durum: "Veri yok", nokta: "" },
};

// Görünüm tercihi tarayıcıda hatırlanır (gizli pencere vb. durumda varsayılana döner)
const tercihOku = (anahtar, izinli, varsayilan) => {
  try {
    const deger = localStorage.getItem(anahtar);
    return izinli.includes(deger) ? deger : varsayilan;
  } catch {
    return varsayilan;
  }
};
const tercihYaz = (anahtar, deger) => {
  try {
    localStorage.setItem(anahtar, deger);
  } catch {
    // depolama kapalıysa yalnızca bu oturumda geçerli
  }
};

const sureMetni = (sn) => {
  if (sn == null) return "—";
  if (sn < 60) return `${Math.max(0, sn)} sn önce`;
  if (sn < 3600) return `${Math.floor(sn / 60)} dk önce`;
  return `${Math.floor(sn / 3600)} sa önce`;
};

function Segment({ etiket, secenekler, secili, onSec }) {
  return (
    <div role="group" aria-label={etiket} className="segment">
      {Object.entries(secenekler).map(([anahtar, ad]) => (
        <button key={anahtar} type="button" className="segment-btn"
          aria-pressed={secili === anahtar} onClick={() => onSec(anahtar)}>
          {ad}
        </button>
      ))}
    </div>
  );
}

// Canlı katman: alarm halesi, düğüm → Mosquitto akış çizgileri (durum renginde), Mosquitto
function CanliKatman({ noktalar, hub, haleR, haleSaydam }) {
  return (
    <>
      {noktalar.filter((n) => n.tip === "alarm").map((n) => (
        <circle key={`hale-${n.id}`} cx={n.x} cy={n.y} r={haleR} fill={`rgba(244,63,94,${haleSaydam})`} />
      ))}

      {/* Çevrimdışı / veri yok: gri, kesik ve akışsız */}
      {noktalar.map((n) =>
        n.tip === "off" || n.tip === "yok" ? (
          <line key={`hat-${n.id}`} x1={n.x} y1={n.y} x2={hub.x} y2={hub.y}
            stroke={TIP[n.tip].renk} strokeWidth="4" strokeDasharray="6 12" />
        ) : (
          <line key={`hat-${n.id}`} className={n.tip === "alarm" ? "akis2-hizli" : "akis2"}
            x1={n.x} y1={n.y} x2={hub.x} y2={hub.y}
            stroke={TIP[n.tip].renk}
            strokeWidth={n.tip === "alarm" ? 6 : 5}
            strokeDasharray="20 36" strokeLinecap="round" />
        )
      )}

      <circle className="hub2-halka" cx={hub.x} cy={hub.y} r="46" fill="none"
        stroke="rgba(34,211,238,.45)" strokeWidth="4" />
      <circle cx={hub.x} cy={hub.y} r="32" fill="#0b1730" stroke="#22d3ee" strokeWidth="4" />
      <path d={`M${hub.x - 14} ${hub.y - 10}h28v9h-28zM${hub.x - 14} ${hub.y + 4}h28v9h-28z`}
        fill="none" stroke="#22d3ee" strokeWidth="3" />
      <rect x={hub.x - 77} y={hub.y + 46} width="154" height="36" rx="10" fill="rgba(6,11,22,.92)"
        stroke="#24345a" strokeWidth="2" />
      <text x={hub.x} y={hub.etiketY} textAnchor="middle" fill="#a9b6cf" fontSize="21"
        fontFamily="JetBrains Mono, monospace">Mosquitto</text>
    </>
  );
}

// dugumler: [{ id, konum, cevrimici, veriYok, duman, hareket, alev, sonZaman }]
// alarmdakiler: son 5 dk'da kritik olayı olan düğüm id'leri (Set)
export default function KampusHaritasi({ dugumler, alarmdakiler, secili, onSec, simdiSn }) {
  const [aci, setAci] = useState(() => tercihOku("harita.aci", Object.keys(ACILAR), "kus"));
  const [zemin, setZemin] = useState(() => tercihOku("harita.zemin", Object.keys(ZEMINLER), "kroki"));
  // Yüklenemeyen fotoğraflar: koyu zemin (#070c18) ve SVG katmanı kalır
  const [bozukFotolar, setBozukFotolar] = useState(() => new Set());

  const aciSec = (deger) => { setAci(deger); tercihYaz("harita.aci", deger); };
  const zeminSec = (deger) => { setZemin(deger); tercihYaz("harita.zemin", deger); };

  const gorunum = ACILAR[aci];
  const katman = gorunum.zemin[zemin];
  const { vb } = gorunum;
  const yuzdeX = (px) => ((px - vb.x) / vb.gen) * 100;
  const yuzdeY = (py) => ((py - vb.y) / vb.yuk) * 100;

  // Yalnızca bu açıda koordinatı tanımlı düğümler çizilir (konum adı backend'den)
  const noktalar = dugumler
    .filter((d) => gorunum.konumlar[d.id])
    .map((d) => ({
      ...d,
      ...gorunum.konumlar[d.id],
      tip: d.veriYok ? "yok" : alarmdakiler.has(d.id) ? "alarm" : d.cevrimici ? "ok" : "off",
    }));
  // Seçim App'te tutulur; görünüm değişince seçili düğüm ve detay kartı korunur
  const sec = noktalar.find((n) => n.id === secili) ?? noktalar[0];
  const fotoGoster = katman.foto && !bozukFotolar.has(katman.foto);

  return (
    <div className="kart panel-kart harita-kart">
      <div className="bolum-ust">
        <div className="baslik-grup">
          <span className="bolum-baslik">Kampüs haritası</span>
          <span className="bolum-alt">Düğüme tıklayarak ayrıntıları gör</span>
        </div>
        <div className="segmentler">
          <Segment etiket="Harita açısı" secili={aci} onSec={aciSec}
            secenekler={Object.fromEntries(Object.entries(ACILAR).map(([k, v]) => [k, v.ad]))} />
          <Segment etiket="Harita zemini" secili={zemin} onSec={zeminSec} secenekler={ZEMINLER} />
        </div>
        <div className="lejant">
          <span><i style={{ background: TIP.ok.renk }} />Çevrimiçi</span>
          <span><i style={{ background: TIP.alarm.renk }} />Alarm</span>
          <span><i style={{ background: TIP.off.renk }} />Çevrimdışı</span>
        </div>
      </div>

      <div className="harita">
        <div className="harita-alan">
          {fotoGoster && (
            <img key={katman.foto} className="harita-foto" src={katman.foto} alt=""
              onError={() => setBozukFotolar((s) => new Set(s).add(katman.foto))} />
          )}
          <svg role="img" viewBox={`${vb.x} ${vb.y} ${vb.gen} ${vb.yuk}`} width="100%" height="100%"
            aria-label={katman.aria}>
            {katman.katman}
            <CanliKatman noktalar={noktalar} hub={gorunum.hub} haleR={gorunum.haleR}
              haleSaydam={katman.haleSaydam} />
          </svg>

          {noktalar.map((n) => {
            const aktif = sec?.id === n.id;
            const renk = TIP[n.tip].renk;
            return (
              <button
                key={n.id}
                type="button"
                className="dugum-btn"
                style={{ left: `${yuzdeX(n.x)}%`, top: `${yuzdeY(n.y)}%`, "--renk": renk }}
                aria-label={`${n.id}, ${n.konum ?? "konum tanımsız"}, ${TIP[n.tip].durum}`}
                aria-pressed={aktif}
                onClick={() => onSec(n.id)}
              >
                <span className={`dugum-nokta ${TIP[n.tip].nokta} ${aktif ? "aktif" : ""}`} />
                <span className={aktif ? "dugum-etiket aktif" : "dugum-etiket"}>
                  {n.id}
                  {n.tip === "yok" && <span className="dugum-etiket-not"> · veri yok</span>}
                </span>
              </button>
            );
          })}

          {noktalar.length === 0 && (
            <div className="harita-bos">Haritada konumu tanımlı düğüm yok</div>
          )}
        </div>

        {sec && (
          <div className="dugum-detay">
            <div className="detay-ust">
              <div className="baslik-grup">
                <span className="detay-id">{sec.id}</span>
                <span className="bolum-alt">{sec.konum ?? "Konum tanımsız"}</span>
              </div>
              <span className="durum-hap" style={{ "--renk": TIP[sec.tip].renk }}>
                {TIP[sec.tip].durum}
              </span>
            </div>
            <div className="detay-izgara">
              <div>
                <span>PIR</span>
                <b>{sec.hareket == null ? "—" : sec.hareket.deger ? "Aktif" : "Pasif"}</b>
              </div>
              <div>
                <span>MQ-2</span>
                <b className="mono vurgu">{sec.duman?.deger ?? "—"}</b>
              </div>
              <div>
                <span>Alev</span>
                <b className={sec.alev?.deger ? "alev-var" : ""}>
                  {sec.alev == null ? "—" : sec.alev.deger ? "VAR" : "Yok"}
                </b>
              </div>
            </div>
            <span className="detay-son">
              Son veri: <span className="mono">
                {sureMetni(sec.sonZaman ? simdiSn - sec.sonZaman : null)}
              </span>
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
