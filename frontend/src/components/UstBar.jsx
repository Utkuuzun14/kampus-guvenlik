import { useId } from "react";
import { KURUM, MODLAR, MOD_AD } from "../sabitler";

const BAGLANTI = {
  canli: { metin: "Canlı", durum: "canli" },
  kopuk: { metin: "Bağlantı yok", durum: "hata" },
  baglaniyor: { metin: "Bağlanıyor…", durum: "uyari" },
};

// Güvenlik modu seçici. Otomatikte o an geçerli mod yanında gösterilir;
// etkin mod gece ise kutu uyarı rengiyle vurgulanır.
function ModSecici({ mod }) {
  const id = useId();
  const bilgi = mod.bilgi;
  const gece = bilgi?.etkin_mod === "gece";
  return (
    <div className={gece ? "mod-kutu mod-gece" : "mod-kutu"} title={mod.hata ?? bilgi?.aciklama}>
      <label htmlFor={id} className="tehdit-etiket">Güvenlik modu</label>
      <div className="mod-satir">
        <select
          id={id}
          className="mod-secim"
          value={bilgi?.mod ?? ""}
          disabled={!bilgi || mod.kaydediliyor}
          onChange={(e) => mod.degistir(e.target.value)}
        >
          {!bilgi && <option value="">—</option>}
          {MODLAR.map((m) => (
            <option key={m} value={m}>{MOD_AD[m]}</option>
          ))}
        </select>
        {bilgi?.mod === "otomatik" && (
          <span className="mod-etkin">şu an: {MOD_AD[bilgi.etkin_mod] ?? bilgi.etkin_mod}</span>
        )}
      </div>
      {mod.hata && <span className="isik-not" role="status">{mod.hata}</span>}
    </div>
  );
}

// isiklar: [{ ad, durum: "ok" | "uyari" | "hata" | "bekliyor", not?, ipucu? }]
// mod: useGuvenlikModu() sonucu
export default function UstBar({ simdi, tehdit, isiklar, baglanti, mod }) {
  const saat = simdi.toLocaleTimeString("tr-TR", {
    hour: "2-digit", minute: "2-digit", second: "2-digit",
  });
  const tarih = simdi.toLocaleDateString("tr-TR", {
    day: "numeric", month: "long", year: "numeric", weekday: "long",
  });
  const ws = BAGLANTI[baglanti];

  return (
    <header className="ustbar">
      <div className="ustbar-baslik">
        <div className="ust-etiket">{KURUM}</div>
        <h1>Komuta Merkezi</h1>
      </div>

      <div className="ustbar-sag">
        <div className={`tehdit tehdit-${tehdit.tip}`}>
          <span className="tehdit-etiket">Tehdit seviyesi</span>
          <span className="tehdit-metin">{tehdit.metin}</span>
        </div>

        <ModSecici mod={mod} />

        <div className="isiklar">
          {isiklar.map((i) => (
            <span key={i.ad} className="isik" title={i.ipucu}>
              <span className={`isik-nokta isik-${i.durum}`} />
              {i.ad}
              {i.not && <span className="isik-not">{i.not}</span>}
            </span>
          ))}
          <span className={`isik isik-ws isik-ws-${ws.durum}`}>
            <span className={`isik-nokta isik-${ws.durum}`} />
            {ws.metin}
          </span>
        </div>

        <div className="saat-kutu">
          <span className="saat">{saat}</span>
          <span className="tarih">{tarih}</span>
        </div>
      </div>
    </header>
  );
}
