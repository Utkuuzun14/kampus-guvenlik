import { useState, useEffect, useRef, useId } from "react";
import { DURUMLAR, DURUM_AD, DURUM_EYLEM } from "../sabitler";
import { cumleDuzeni, durumu, siradakiDurum } from "../hesaplar";
import { durumIlerlet, operatorOku, operatorYaz } from "../hooks/useOlayDurumu";

const NOT_SINIR = 300;

const hataMetni = (h) => {
  if (h.durum === 409) {
    return `Bu olay başka bir sekmede ilerletildi${h.mevcut ? ` (şu an: ${DURUM_AD[h.mevcut] ?? h.mevcut})` : ""}.`;
  }
  if (h.durum === 404) return "Olay bulunamadı (silinmiş olabilir).";
  if (h.durum === 422) return "Operatör adı 1-40, not en fazla 300 karakter olmalı.";
  return h.mesaj || "İşlem yapılamadı.";
};

// Sıradaki adımın butonu (+ ara adımları atlayan "Çöz" kısayolu) ve onay penceresi.
// Pencere native <dialog>: odak içeride kalır, Esc ile kapanır.
// onGuncellendi(olay): sunucunun döndürdüğü güncel olay (WS mesajı da ayrıca gelir).
export default function DurumIlerlet({ olay, onGuncellendi, anaSinif = "durum-btn" }) {
  const siradaki = siradakiDurum(olay);
  const [hedef, setHedef] = useState(null);
  const [ad, setAd] = useState("");
  const [not, setNot] = useState("");
  const [hata, setHata] = useState(null);
  const [gonderiliyor, setGonderiliyor] = useState(false);
  const dialogRef = useRef(null);
  const baslikId = useId();

  useEffect(() => {
    const d = dialogRef.current;
    if (hedef && d && !d.open) d.showModal();
  }, [hedef]);

  if (!siradaki && !hedef) return null;

  const ac = (durum) => {
    setAd(operatorOku());
    setNot("");
    setHata(null);
    setHedef(durum);
  };

  const kapat = () => dialogRef.current?.close();

  const gonder = async (e) => {
    e.preventDefault();
    const temizAd = ad.trim();
    if (!temizAd || gonderiliyor) return;
    setGonderiliyor(true);
    setHata(null);
    try {
      const guncel = await durumIlerlet(olay.id, hedef, temizAd, not.trim());
      operatorYaz(temizAd);
      onGuncellendi?.(guncel);
      kapat();
    } catch (h) {
      setHata(hataMetni(h));
    } finally {
      setGonderiliyor(false);
    }
  };

  const mevcut = durumu(olay);
  const atlanan = hedef
    ? DURUMLAR.slice(DURUMLAR.indexOf(mevcut) + 1, DURUMLAR.indexOf(hedef))
    : [];

  return (
    <>
      {siradaki && (
        <span className="durum-eylemler">
          <button type="button" className={anaSinif} onClick={() => ac(siradaki)}>
            {DURUM_EYLEM[siradaki]}
          </button>
          {siradaki !== "cozuldu" && (
            <button type="button" className="durum-btn ikincil" onClick={() => ac("cozuldu")}
              title="Ara adımları atlayıp doğrudan çöz">
              Çöz
            </button>
          )}
        </span>
      )}

      <dialog ref={dialogRef} className="durum-dialog kart" aria-labelledby={baslikId}
        onClose={() => setHedef(null)}>
        {hedef && (
          <form className="durum-form" onSubmit={gonder}>
            <div className="baslik-grup">
              <span id={baslikId} className="bolum-baslik">
                {DURUM_AD[hedef]} olarak işaretle
              </span>
              <span className="bolum-alt">
                #{olay.id} · {cumleDuzeni(olay.mesaj)} · şu an {DURUM_AD[mevcut]}
              </span>
              {atlanan.length > 0 && (
                <span className="kucuk-mono">
                  Atlanan adım: {atlanan.map((d) => DURUM_AD[d]).join(", ")} (aynı saatle kaydedilir)
                </span>
              )}
            </div>

            <label className="durum-alan">
              <span>Operatör adı</span>
              <input type="text" value={ad} onChange={(e) => setAd(e.target.value)}
                maxLength={40} required autoFocus autoComplete="name" />
            </label>

            <label className="durum-alan">
              <span>
                Not <span className="kucuk-mono">(isteğe bağlı · {not.length}/{NOT_SINIR})</span>
              </span>
              <textarea value={not} onChange={(e) => setNot(e.target.value)}
                maxLength={NOT_SINIR} rows={3} />
            </label>

            {hata && <p role="alert" className="durum-hata">{hata}</p>}

            <div className="durum-dugmeler">
              <button type="button" className="filtre-btn" onClick={kapat}>Vazgeç</button>
              <button type="submit" className="filtre-btn aktif"
                disabled={gonderiliyor || !ad.trim()}>
                {gonderiliyor ? "Kaydediliyor…" : "Onayla"}
              </button>
            </div>
          </form>
        )}
      </dialog>
    </>
  );
}
