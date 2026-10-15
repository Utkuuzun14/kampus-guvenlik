import { useId } from "react";
import { KURUM, MODLAR, MOD_AD, ROL_AD } from "../sabitler";
import { bugunBaslangicSn } from "../hesaplar";

const BAGLANTI = {
  canli: { metin: "Canlı", durum: "canli" },
  kopuk: { metin: "Bağlantı yok", durum: "hata" },
  baglaniyor: { metin: "Bağlanıyor…", durum: "uyari" },
};

const KILIT_IPUCU = "Mod yalnızca admin tarafından değiştirilebilir";

// "14:32" (bugün) ya da "14.10 14:32"
function kisaZaman(unix) {
  const t = new Date(unix * 1000);
  const saat = t.toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" });
  if (unix >= bugunBaslangicSn(new Date())) return saat;
  return `${t.toLocaleDateString("tr-TR", { day: "2-digit", month: "2-digit" })} ${saat}`;
}

function KilitIkonu() {
  return (
    <svg aria-hidden="true" width="14" height="14" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="4" y="11" width="16" height="10" rx="2" />
      <path d="M8 11V7a4 4 0 0 1 8 0v4" />
    </svg>
  );
}

// Güvenlik modu seçici. Otomatikte o an geçerli mod yanında gösterilir;
// etkin mod gece ise kutu uyarı rengiyle vurgulanır. Operatörde salt okunur.
function ModSecici({ mod, duzenlenebilir }) {
  const id = useId();
  const bilgi = mod.bilgi;
  const gece = bilgi?.etkin_mod === "gece";
  const ipucu = mod.hata ?? (duzenlenebilir ? bilgi?.aciklama
    : `${KILIT_IPUCU}${bilgi?.aciklama ? ` · ${bilgi.aciklama}` : ""}`);
  return (
    <div className={gece ? "mod-kutu mod-gece" : "mod-kutu"} title={ipucu}>
      <label htmlFor={id} className="tehdit-etiket">
        Güvenlik modu
        {!duzenlenebilir && <span className="mod-kilit"><KilitIkonu /></span>}
      </label>
      <div className="mod-satir">
        <select
          id={id}
          className={duzenlenebilir ? "mod-secim" : "mod-secim mod-secim-kilitli"}
          value={bilgi?.mod ?? ""}
          disabled={!bilgi || mod.kaydediliyor || !duzenlenebilir}
          title={duzenlenebilir ? undefined : KILIT_IPUCU}
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
      {bilgi?.degistiren && (
        <span className="mod-degistiren">
          değiştiren: {bilgi.degistiren}
          {bilgi.degistirme_zaman ? `, ${kisaZaman(bilgi.degistirme_zaman)}` : ""}
        </span>
      )}
      {mod.hata && <span className="isik-not" role="status">{mod.hata}</span>}
    </div>
  );
}

function KullaniciKutusu({ kullanici, onCikis }) {
  const ad = kullanici.ad_soyad || kullanici.kullanici_adi;
  return (
    <div className="kullanici-kutu">
      <div className="kullanici-bilgi">
        <span className="kullanici-ad" title={kullanici.kullanici_adi}>{ad}</span>
        <span className={`rol-rozet rol-${kullanici.rol}`}>{ROL_AD[kullanici.rol] ?? kullanici.rol}</span>
      </div>
      <button type="button" className="cikis-btn" onClick={onCikis}>Çıkış</button>
    </div>
  );
}

// isiklar: [{ ad, durum: "ok" | "uyari" | "hata" | "bekliyor", not?, ipucu? }]
// mod: useGuvenlikModu() sonucu; kullanici: oturumdaki { kullanici_adi, ad_soyad, rol }
export default function UstBar({ simdi, tehdit, isiklar, baglanti, mod, kullanici, onCikis }) {
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

        <ModSecici mod={mod} duzenlenebilir={kullanici.rol === "admin"} />

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

        <KullaniciKutusu kullanici={kullanici} onCikis={onCikis} />
      </div>
    </header>
  );
}
