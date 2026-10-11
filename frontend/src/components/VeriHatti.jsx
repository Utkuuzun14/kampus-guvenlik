const ASAMALAR = [
  { anahtar: "esp", ad: "ESP32-S2", alt: "Sensör düğümleri", d: "M9 3v2M15 3v2M9 19v2M15 19v2M3 9h2M3 15h2M19 9h2M19 15h2M7 5h10a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2z" },
  { anahtar: "mqtt", ad: "MQTT", alt: "QoS 1 · LWT", d: "M5 12.55a11 11 0 0 1 14 0M8.5 16.1a6 6 0 0 1 7 0M12 20h.01M2 8.82a15 15 0 0 1 20 0" },
  { anahtar: "api", ad: "FastAPI", alt: "Kural motoru", d: "M4 4h16v6H4zM4 14h16v6H4zM8 7h.01M8 17h.01" },
  { anahtar: "db", ad: "SQLite", alt: "Kalıcı kayıt", d: "M12 3c4.4 0 8 1.3 8 3s-3.6 3-8 3-8-1.3-8-3 3.6-3 8-3zM4 6v12c0 1.7 3.6 3 8 3s8-1.3 8-3V6M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3" },
  { anahtar: "panel", ad: "Panel", alt: "WebSocket canlı", d: "M3 4h18v12H3zM8 20h8M12 16v4" },
];

// durumlar: { esp, mqtt, api, db, panel } → "ok" | "uyari" | "hata" | "bekliyor"
export default function VeriHatti({ durumlar }) {
  return (
    <section className="kart bolum" aria-label="Veri hattı">
      <div className="bolum-ust">
        <span className="bolum-baslik">Veri hattı</span>
        <span className="bolum-alt">Sensörden panele uçtan uca akış</span>
      </div>
      <div className="yatay-kaydir">
        <div className="hat">
          {ASAMALAR.map((a, i) => {
            const sonraki = ASAMALAR[i + 1];
            const akiyor = sonraki && durumlar[a.anahtar] === "ok" && durumlar[sonraki.anahtar] === "ok";
            return (
              <div key={a.anahtar} className="hat-parca">
                <div className="hat-kutu">
                  <div className="hat-ikon">
                    <svg aria-hidden="true" width="20" height="20" viewBox="0 0 24 24" fill="none"
                      stroke="#22d3ee" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                      <path d={a.d} />
                    </svg>
                  </div>
                  <div className="hat-yazi">
                    <span className="hat-ad">{a.ad}</span>
                    <span className="hat-alt">{a.alt}</span>
                  </div>
                  <span className={`isik-nokta isik-${durumlar[a.anahtar]}`} />
                </div>
                {sonraki && (
                  <div className="hat-bag">{akiyor && <span className="akan" />}</div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
