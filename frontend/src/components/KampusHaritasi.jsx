import { DUGUM_KONUMLARI } from "../sabitler";

const HUB = { x: 400, y: 220 }; // Mosquitto (krokide merkez)

const TIP = {
  alarm: { renk: "#f43f5e", durum: "Alarm", nokta: "n-kirmizi" },
  ok: { renk: "#34d399", durum: "Çevrimiçi", nokta: "n-yesil" },
  off: { renk: "#64748b", durum: "Çevrimdışı", nokta: "" },
  yok: { renk: "#64748b", durum: "Veri yok", nokta: "" },
};

const BINALAR = [
  { ad: "Mühendislik Fakültesi", x: 60, y: 50, w: 270, h: 140 },
  { ad: "Kütüphane", x: 450, y: 40, w: 170, h: 140 },
  { ad: "Rektörlük", x: 650, y: 110, w: 120, h: 80 },
  { ad: "Yurtlar", x: 60, y: 250, w: 270, h: 160 },
  { ad: "Yemekhane", x: 650, y: 260, w: 120, h: 150 },
];

const sureMetni = (sn) => {
  if (sn == null) return "—";
  if (sn < 60) return `${Math.max(0, sn)} sn önce`;
  if (sn < 3600) return `${Math.floor(sn / 60)} dk önce`;
  return `${Math.floor(sn / 3600)} sa önce`;
};

// Yalnızca sabitler.js'de koordinatı tanımlı düğümler çizilir (konum adı backend'den)
const konumluDugumler = (dugumler) =>
  dugumler
    .filter((d) => DUGUM_KONUMLARI[d.id])
    .map((d) => ({ ...d, ...DUGUM_KONUMLARI[d.id] }));

// dugumler: [{ id, konum, cevrimici, veriYok, duman, hareket, alev, sonZaman }]
// alarmdakiler: son 5 dk'da kritik olayı olan düğüm id'leri (Set)
export default function KampusHaritasi({ dugumler, alarmdakiler, secili, onSec, simdiSn }) {
  const noktalar = konumluDugumler(dugumler).map((d) => ({
    ...d,
    tip: d.veriYok ? "yok" : alarmdakiler.has(d.id) ? "alarm" : d.cevrimici ? "ok" : "off",
    px: (d.x / 100) * 800,
    py: (d.y / 100) * 440,
  }));
  const sec = noktalar.find((n) => n.id === secili) ?? noktalar[0];

  return (
    <div className="kart panel-kart harita-kart">
      <div className="bolum-ust">
        <div className="baslik-grup">
          <span className="bolum-baslik">Kampüs haritası</span>
          <span className="bolum-alt">Düğüme tıklayarak ayrıntıları gör</span>
        </div>
        <div className="lejant">
          <span><i style={{ background: TIP.ok.renk }} />Çevrimiçi</span>
          <span><i style={{ background: TIP.alarm.renk }} />Alarm</span>
          <span><i style={{ background: TIP.off.renk }} />Çevrimdışı</span>
        </div>
      </div>

      <div className="harita">
        <div className="harita-alan">
          <svg role="img" viewBox="0 0 800 440" width="100%" height="100%"
            aria-label="Kampüs krokisi: Mühendislik Fakültesi, Kütüphane, Rektörlük, Yurtlar, Yemekhane ve Merkezi Park">
            <rect x="0" y="0" width="800" height="440" fill="#08101f" />
            <g stroke="#121c33" strokeWidth="20" strokeLinecap="round">
              <line x1="0" y1="220" x2="800" y2="220" />
              <line x1="400" y1="0" x2="400" y2="440" />
              <line x1="400" y1="220" x2="800" y2="20" />
            </g>
            <g stroke="#1b2847" strokeWidth="1.5" strokeDasharray="8 8">
              <line x1="0" y1="220" x2="800" y2="220" />
              <line x1="400" y1="0" x2="400" y2="440" />
            </g>
            <rect x="430" y="250" width="190" height="160" rx="18"
              fill="rgba(52,211,153,.07)" stroke="rgba(52,211,153,.25)" />
            <text x="448" y="276" fill="#4d8f76" fontSize="13" className="harita-yazi">Merkezi Park</text>
            {BINALAR.map((b) => (
              <g key={b.ad}>
                <rect x={b.x} y={b.y} width={b.w} height={b.h} rx="12" fill="#0f1a31" stroke="#24345a" />
                <text x={b.x + 18} y={b.y + 26} fill="#a9b6cf" fontSize="14" fontWeight="600"
                  className="harita-yazi">{b.ad}</text>
              </g>
            ))}

            {/* Alarmdaki düğümün çevresinde kırmızı hale */}
            {noktalar.filter((n) => n.tip === "alarm").map((n) => (
              <circle key={`hale-${n.id}`} cx={n.px} cy={n.py} r="70" fill="rgba(244,63,94,.10)" />
            ))}

            {/* Düğüm → Mosquitto akış çizgileri, düğümün durum renginde.
                Çevrimdışı / veri yok: sönük, kesik ve akışsız. */}
            {noktalar.map((n) =>
              n.tip === "off" || n.tip === "yok" ? (
                <line key={`hat-${n.id}`} x1={n.px} y1={n.py} x2={HUB.x} y2={HUB.y}
                  stroke={TIP[n.tip].renk} strokeOpacity="0.35" strokeWidth="2" strokeDasharray="3 6" />
              ) : (
                <line key={`hat-${n.id}`} className={n.tip === "alarm" ? "akis-hizli" : "akis"}
                  x1={n.px} y1={n.py} x2={HUB.x} y2={HUB.y}
                  stroke={TIP[n.tip].renk}
                  strokeWidth={n.tip === "alarm" ? 3 : 2.5}
                  strokeDasharray="10 18" strokeLinecap="round" />
              )
            )}

            <circle className="hub-halka" cx={HUB.x} cy={HUB.y} r="26" fill="none"
              stroke="rgba(34,211,238,.35)" strokeWidth="2" />
            <circle cx={HUB.x} cy={HUB.y} r="19" fill="#0b1730" stroke="#22d3ee" strokeWidth="2" />
            <path d="M392 214h16v5h-16zM392 222h16v5h-16z" fill="none" stroke="#22d3ee" strokeWidth="1.6" />
            <rect x="356" y="250" width="88" height="22" rx="6" fill="rgba(6,11,22,.9)" stroke="#24345a" />
            <text x="400" y="265" textAnchor="middle" fill="#a9b6cf" fontSize="12"
              fontFamily="JetBrains Mono, monospace">Mosquitto</text>
          </svg>

          {noktalar.map((n) => {
            const aktif = sec?.id === n.id;
            const renk = TIP[n.tip].renk;
            return (
              <button
                key={n.id}
                type="button"
                className="dugum-btn"
                style={{ left: `${n.x}%`, top: `${n.y}%`, "--renk": renk }}
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
