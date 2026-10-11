import { TEHDIT_PENCERE_SN } from "../sabitler";
import {
  seviyeAnahtari, bugunBaslangicSn, kovalaraBol, sparkNoktalari,
} from "../hesaplar";

function Kart({ etiket, sayi, alt, trend, renk, noktalar, vurgulu, sayiRenkli }) {
  return (
    <div className={vurgulu ? "kart ozet-kart vurgulu" : "kart ozet-kart"} style={{ "--renk": renk }}>
      <div className="ozet-ust">
        <span className="ozet-etiket">{etiket}</span>
        <span className="ozet-trend">{trend}</span>
      </div>
      <div className="ozet-orta">
        <span className={sayiRenkli ? "ozet-sayi renkli" : "ozet-sayi"}>{sayi}</span>
        <svg aria-hidden="true" width="96" height="34" viewBox="0 0 96 34" className="spark">
          <polyline fill="none" stroke={renk} strokeWidth="2" strokeLinejoin="round"
            strokeLinecap="round" points={noktalar} />
        </svg>
      </div>
      <span className="ozet-alt">{alt}</span>
    </div>
  );
}

// olaylar: analitik listesi (yeni → eski); dugumOzet: { toplam, cevrimici, cevrimdisi[] }
export default function OzetKartlari({ olaylar, simdi, esik, dugumOzet, cevrimiciGecmis }) {
  const simdiSn = Math.floor(simdi.getTime() / 1000);
  const bugun = bugunBaslangicSn(simdi);
  const bugunku = olaylar.filter((o) => o.zaman >= bugun);

  const seviyeli = (s) => (o) => seviyeAnahtari(o.seviye) === s;
  const sonSaat = (filtre) =>
    olaylar.filter((o) => simdiSn - o.zaman < 3600 && simdiSn - o.zaman >= 0 && filtre(o)).length;
  const hepsi = () => true;

  const kritikAktif = olaylar.some(
    (o) => seviyeli("kritik")(o) && simdiSn - o.zaman <= TEHDIT_PENCERE_SN
  );
  const kritikBugun = bugunku.filter(seviyeli("kritik")).length;

  const aktifSeri = [...Array(Math.max(0, 9 - cevrimiciGecmis.length)).fill(cevrimiciGecmis[0] ?? 0), ...cevrimiciGecmis];

  const kartlar = [
    {
      etiket: "Toplam olay",
      sayi: bugunku.length,
      alt: "Bugün · tüm düğümler",
      trend: `+${sonSaat(hepsi)} / sa`,
      renk: "#22d3ee",
      noktalar: sparkNoktalari(kovalaraBol(olaylar, simdiSn)),
    },
    {
      etiket: "Kritik",
      sayi: kritikBugun,
      alt: "Alev algılama",
      trend: kritikAktif ? "AKTİF" : `+${sonSaat(seviyeli("kritik"))} / sa`,
      renk: "#fb7185",
      noktalar: sparkNoktalari(kovalaraBol(olaylar, simdiSn, { filtre: seviyeli("kritik") })),
      vurgulu: kritikAktif,
      sayiRenkli: kritikBugun > 0,
    },
    {
      etiket: "Yüksek",
      sayi: bugunku.filter(seviyeli("yuksek")).length,
      alt: `Duman eşiği (>${esik})`,
      trend: `+${sonSaat(seviyeli("yuksek"))} / sa`,
      renk: "#fb923c",
      noktalar: sparkNoktalari(kovalaraBol(olaylar, simdiSn, { filtre: seviyeli("yuksek") })),
    },
    {
      etiket: "Aktif düğüm",
      sayi: `${dugumOzet.cevrimici}/${dugumOzet.toplam}`,
      alt: dugumOzet.toplam === 0
        ? "Düğüm bilgisi yok"
        : dugumOzet.cevrimdisi.length
          ? `${dugumOzet.cevrimdisi.join(", ")} çevrimdışı`
          : "Tümü çevrimiçi",
      trend: "LWT",
      renk: "#34d399",
      noktalar: sparkNoktalari(aktifSeri, { max: dugumOzet.toplam }),
    },
  ];

  return (
    <section className="ozet" aria-label="Özet">
      {kartlar.map((k) => (
        <Kart key={k.etiket} {...k} />
      ))}
    </section>
  );
}
