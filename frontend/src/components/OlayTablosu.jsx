import { SEVIYE_AD, SENSOR_KISA } from "../sabitler";
import { seviyeAnahtari, saatBicim, bugunBaslangicSn } from "../hesaplar";

const FILTRELER = [
  ["hepsi", "Tümü"],
  ["kritik", "Kritik"],
  ["yuksek", "Yüksek"],
  ["orta", "Orta"],
  ["uyari", "Uyarı"],
  ["bilgi", "Bilgi"],
];

// Bugünkü olaylar yalnızca saatle, eskiler gün.ay ile gösterilir
const zamanBicim = (unix, bugun) => {
  if (!unix) return "-";
  if (unix >= bugun) return saatBicim(unix);
  const t = new Date(unix * 1000);
  return `${t.toLocaleDateString("tr-TR", { day: "2-digit", month: "2-digit" })} ${saatBicim(unix)}`;
};

export default function OlayTablosu({ olaylar, filtre, onFiltre, simdi }) {
  const bugun = bugunBaslangicSn(simdi);
  // Filtre mantığı öncekiyle aynı: seviye birebir eşleşmeli
  const satirlar = olaylar.filter((o) => filtre === "hepsi" || o.seviye === filtre);

  return (
    <section id="olaylar" className="kart panel-kart">
      <div className="tablo-ust">
        <div className="tablo-baslik">
          <span className="bolum-baslik">Olay kayıtları</span>
          <span className="kucuk-mono">{satirlar.length} kayıt</span>
        </div>
        <div className="filtreler" role="group" aria-label="Seviye filtresi">
          {FILTRELER.map(([anahtar, ad]) => (
            <button
              key={anahtar}
              type="button"
              className={filtre === anahtar ? "filtre-btn aktif" : "filtre-btn"}
              aria-pressed={filtre === anahtar}
              onClick={() => onFiltre(anahtar)}
            >
              {ad}
            </button>
          ))}
        </div>
      </div>

      <div className="tablo-sarmal">
        <table className="olay-tablo">
          <thead>
            <tr>
              <th>Zaman</th>
              <th>Düğüm</th>
              <th>Sensör</th>
              <th>Değer</th>
              <th>Seviye</th>
              <th>Açıklama</th>
            </tr>
          </thead>
          <tbody>
            {satirlar.length === 0 && (
              <tr>
                <td colSpan="6" className="bos">
                  {olaylar.length === 0 ? "Henüz olay yok." : "Bu seviyede olay yok."}
                </td>
              </tr>
            )}
            {satirlar.map((o, i) => {
              const s = seviyeAnahtari(o.seviye);
              return (
                <tr key={o.id ?? i}>
                  <td className="mono soluk" title={new Date(o.zaman * 1000).toLocaleString("tr-TR")}>
                    {zamanBicim(o.zaman, bugun)}
                  </td>
                  <td className="mono">{o.dugum}</td>
                  <td>{SENSOR_KISA[o.sensor] ?? o.sensor}</td>
                  <td className="mono">{o.deger ?? "—"}</td>
                  <td>
                    <span className={s ? `rozet rozet-${s}` : "rozet rozet-bilinmeyen"}>
                      {s ? SEVIYE_AD[s] : o.seviye}
                    </span>
                  </td>
                  <td className="aciklama">{o.mesaj}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
