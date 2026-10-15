import { useState, useEffect, useRef, useId } from "react";
import { DURUM_AD, SEVIYE_AD, SENSOR_AD } from "../sabitler";
import {
  akistaMi, cumleDuzeni, durumu, seviyeAnahtari, sureBicim, tarihSaatBicim,
} from "../hesaplar";
import { olayGetir } from "../hooks/useOlayDurumu";
import DurumRozeti from "./DurumRozeti";
import DurumIlerlet from "./DurumIlerlet";

const ADIM_RENK = {
  olustu: "var(--metin-soluk)",
  goruldu: "var(--uyari)",
  mudahale: "var(--vurgu)",
  cozuldu: "var(--ok)",
};

// Zaman çizelgesi: oluştu → görüldü → müdahale → çözüldü.
// Kim + not olay_adimlari'ndan; adımı olmayan ama zamanı dolu durum atlanmıştır.
function adimlariKur(olay, adimlar) {
  const satirlar = [{
    anahtar: "olustu", ad: "Oluştu", zaman: olay.zaman,
    kim: olay.dugum, not: null, durum: "tamam",
  }];
  for (const d of ["goruldu", "mudahale", "cozuldu"]) {
    const adim = [...adimlar].reverse().find((a) => a.durum === d);
    const zaman = olay[`${d}_zaman`] ?? adim?.zaman ?? null;
    satirlar.push({
      anahtar: d,
      ad: d === "mudahale" ? "Müdahale" : DURUM_AD[d],
      zaman,
      kim: adim?.kim ?? null,
      not: adim?.not_metni ?? null,
      durum: adim ? "tamam" : zaman ? "atlandi" : "bekliyor",
    });
  }
  return satirlar;
}

// Olay detayı ve zaman çizelgesi. olay: listelerdeki güncel kayıt (WS ile güncellenir).
export default function OlayDetay({ olay, konumlar, onKapat, onGuncellendi }) {
  const [adimlar, setAdimlar] = useState(null);
  const dialogRef = useRef(null);
  const baslikId = useId();
  const d = durumu(olay);

  useEffect(() => {
    const el = dialogRef.current;
    if (el && !el.open) el.showModal();
  }, []);

  // Liste kaydında adımlar yoksa açılışta çekilir. Durum güncellemesi (PATCH yanıtı
  // ya da WS "olay_guncelleme") adımları da taşır ve olay.adimlar olarak gelir.
  useEffect(() => {
    if (olay.adimlar) return undefined;
    let iptal = false;
    olayGetir(olay.id).then((v) => {
      if (!iptal) setAdimlar(v?.adimlar ?? []);
    });
    return () => {
      iptal = true;
    };
  }, [olay.id, olay.adimlar]);

  const s = seviyeAnahtari(olay.seviye);
  const konum = konumlar[olay.dugum];
  const akista = akistaMi(olay);
  const satirlar = adimlariKur(olay, olay.adimlar ?? adimlar ?? []);

  return (
    <dialog ref={dialogRef} className="olay-detay kart" aria-labelledby={baslikId}
      onClose={onKapat}>
      <div className="olay-detay-ust">
        <div className="baslik-grup">
          <span className="kucuk-mono">Olay #{olay.id}</span>
          <span id={baslikId} className="bolum-baslik">{cumleDuzeni(olay.mesaj)}</span>
          <span className="bolum-alt">
            {olay.dugum}{konum ? ` · ${konum}` : ""} · {SENSOR_AD[olay.sensor] ?? olay.sensor}
            {olay.deger != null ? ` · değer ${olay.deger}` : ""}
          </span>
        </div>
        <button type="button" className="filtre-btn" onClick={() => dialogRef.current?.close()}
          aria-label="Kapat">
          Kapat
        </button>
      </div>

      <div className="olay-detay-rozetler">
        <span className={s ? `rozet rozet-${s}` : "rozet rozet-bilinmeyen"}>
          {s ? SEVIYE_AD[s] : olay.seviye}
        </span>
        {akista && <DurumRozeti olay={olay} />}
      </div>

      {akista ? (
        <ol className="zaman-cizelgesi" aria-label="Zaman çizelgesi">
          {satirlar.map((a, i) => {
            const onceki = satirlar.slice(0, i).reverse().find((x) => x.zaman);
            const fark = a.zaman && onceki ? a.zaman - onceki.zaman : null;
            return (
              <li key={a.anahtar} className={`akis-satir zc-${a.durum}`}>
                <div className="akis-ray">
                  <span className="akis-nokta"
                    style={{ "--renk": a.durum === "bekliyor" ? "var(--kenar-belirgin)" : ADIM_RENK[a.anahtar] }} />
                  {i < satirlar.length - 1 && <span className="akis-cizgi" />}
                </div>
                <div className="akis-icerik">
                  <div className="akis-ust">
                    <span className="akis-ad">{a.ad}</span>
                    <span className="kucuk-mono">
                      {a.zaman ? tarihSaatBicim(a.zaman) : "bekliyor"}
                      {fark != null && fark >= 0 && i > 0 ? ` · +${sureBicim(fark)}` : ""}
                    </span>
                  </div>
                  {a.durum === "tamam" && a.kim && (
                    <span className="bolum-alt">{i === 0 ? "Kaynak" : "Operatör"}: {a.kim}</span>
                  )}
                  {a.durum === "atlandi" && (
                    <span className="bolum-alt">Atlandı (sonraki adımla birlikte kaydedildi)</span>
                  )}
                  {a.not && <span className="zc-not">“{a.not}”</span>}
                </div>
              </li>
            );
          })}
        </ol>
      ) : (
        <p className="bolum-alt">
          Bu seviye operatör akışına girmez; olay oluşurken otomatik çözüldü
          ({tarihSaatBicim(olay.zaman)}).
        </p>
      )}

      {akista && d !== "cozuldu" && (
        <div className="olay-detay-alt">
          <DurumIlerlet olay={olay} onGuncellendi={onGuncellendi} />
        </div>
      )}

      <span className="kucuk-mono">
        Oluşma saati cihazdan, adım saatleri sunucudan gelir.
      </span>
    </dialog>
  );
}
