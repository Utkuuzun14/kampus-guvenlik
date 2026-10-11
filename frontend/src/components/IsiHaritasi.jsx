import { GUNLER, isiMatrisi } from "../hesaplar";

const SAAT = (h) => String(h).padStart(2, "0");

// olaylar: analitik listesi (en fazla `limit` kayıt)
export default function IsiHaritasi({ olaylar, simdiSn, limit }) {
  const { matris, toplam, enCok } = isiMatrisi(olaylar, simdiSn);
  // Liste sınıra dayandıysa 7 günün tamamı gelmemiş olabilir
  const kesik = olaylar.length >= limit;

  return (
    <div className="kart panel-kart">
      <div className="bolum-ust">
        <div className="baslik-grup">
          <span className="bolum-baslik">Haftalık olay yoğunluğu</span>
          <span className="bolum-alt">
            Saat ve güne göre olay sayısı · son 7 gün · {toplam} olay
            {kesik && ` (son ${limit} kayıt)`}
          </span>
        </div>
        <div className="isi-lejant" aria-hidden="true">
          Az
          {[0.1, 0.35, 0.6, 0.9].map((a) => (
            <span key={a} style={{ background: `rgba(34,211,238,${a})` }} />
          ))}
          Çok
        </div>
      </div>

      <div className="yatay-kaydir">
        <div className="isi-izgara" role="table" aria-label="Gün ve saate göre olay sayısı">
          {GUNLER.map((g, d) => (
            <div key={g} className="isi-satir" role="row">
              <span className="isi-gun" role="rowheader">{g}</span>
              <div className="isi-hucreler">
                {matris[d].map((adet, h) => {
                  const v = enCok ? adet / enCok : 0;
                  return (
                    <span
                      key={h}
                      role="cell"
                      title={`${g} ${SAAT(h)}:00 · ${adet} olay`}
                      aria-label={`${g} ${SAAT(h)}:00, ${adet} olay`}
                      style={{ background: `rgba(34,211,238,${(0.07 + v * 0.85).toFixed(2)})` }}
                    />
                  );
                })}
              </div>
            </div>
          ))}
          <div className="isi-satir">
            <span className="isi-gun" />
            <div className="isi-saatler">
              <span>00</span><span>06</span><span>12</span><span>18</span><span>23</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
