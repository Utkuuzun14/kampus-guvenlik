import { useState, useEffect, useRef, useId, useCallback } from "react";
import { ROLLER, ROL_AD } from "../sabitler";
import { tarihSaatBicim } from "../hesaplar";
import { apiFetch } from "../api";

const PAROLA_EN_AZ = 8;
const BOS_FORM = { kullanici_adi: "", ad_soyad: "", rol: "operator", parola: "" };

// Backend hata gövdesi → Türkçe metin (422'de Pydantic listesi de gelebilir)
async function hataMetni(cevap) {
  const veri = await cevap.json().catch(() => null);
  if (typeof veri?.detail === "string") return veri.detail;
  if (cevap.status === 422) return "Geçersiz değer: kullanıcı adı 3-32 karakter, parola en az 8 karakter.";
  return `İşlem yapılamadı (HTTP ${cevap.status}).`;
}

// İstek; başarısızsa Türkçe mesajla hata fırlatır
async function istek(yol, yontem, govde) {
  let cevap;
  try {
    cevap = await apiFetch(yol, { method: yontem, body: govde && JSON.stringify(govde) });
  } catch {
    throw new Error("Sunucuya ulaşılamadı.");
  }
  if (!cevap.ok) throw new Error(await hataMetni(cevap));
  return cevap.json();
}

function ParolaSifirla({ kullanici, onSonuc }) {
  const [acik, setAcik] = useState(false);
  const [parola, setParola] = useState("");
  const [gonderiliyor, setGonderiliyor] = useState(false);

  if (!acik) {
    return (
      <button type="button" className="durum-btn ikincil" onClick={() => setAcik(true)}>
        Parola sıfırla
      </button>
    );
  }

  const kaydet = async (e) => {
    e.preventDefault();
    setGonderiliyor(true);
    try {
      await istek(`/api/kullanicilar/${encodeURIComponent(kullanici.kullanici_adi)}`, "PATCH",
        { yeni_parola: parola });
      onSonuc({ tamam: `${kullanici.kullanici_adi} için parola değiştirildi.` });
      setAcik(false);
      setParola("");
    } catch (h) {
      onSonuc({ hata: h.message });
    } finally {
      setGonderiliyor(false);
    }
  };

  return (
    <form className="parola-sifirla" onSubmit={kaydet}>
      <input type="password" value={parola} onChange={(e) => setParola(e.target.value)}
        minLength={PAROLA_EN_AZ} maxLength={128} required autoFocus autoComplete="new-password"
        placeholder="Yeni parola" aria-label={`${kullanici.kullanici_adi} yeni parola`} />
      <button type="submit" className="durum-btn" disabled={gonderiliyor || parola.length < PAROLA_EN_AZ}>
        Kaydet
      </button>
      <button type="button" className="durum-btn ikincil" onClick={() => setAcik(false)}>Vazgeç</button>
    </form>
  );
}

// Kullanıcı yönetimi (yalnızca admin): liste, ekle, rol değiştir, pasif/aktif, parola sıfırla.
// ben: oturumdaki kullanıcı (kendini pasif yapma düğmesi kapalı; backend de 409 döner).
export default function Kullanicilar({ ben, onKapat }) {
  const [liste, setListe] = useState(null);
  const [form, setForm] = useState(BOS_FORM);
  const [sonuc, setSonuc] = useState(null); // { tamam } | { hata }
  const [mesgul, setMesgul] = useState(false);
  const dialogRef = useRef(null);
  const baslikId = useId();

  const yenile = useCallback(async () => {
    try {
      setListe(await istek("/api/kullanicilar", "GET"));
    } catch (h) {
      setSonuc({ hata: h.message });
    }
  }, []);

  useEffect(() => {
    const el = dialogRef.current;
    if (el && !el.open) el.showModal();
    yenile();
  }, [yenile]);

  const guncelle = async (k, alanlar, tamamMetni) => {
    setMesgul(true);
    setSonuc(null);
    try {
      await istek(`/api/kullanicilar/${encodeURIComponent(k.kullanici_adi)}`, "PATCH", alanlar);
      setSonuc({ tamam: tamamMetni });
    } catch (h) {
      setSonuc({ hata: h.message });
    } finally {
      setMesgul(false);
      yenile(); // reddedilen değişiklikte seçici sunucudaki değere döner
    }
  };

  const ekle = async (e) => {
    e.preventDefault();
    setMesgul(true);
    setSonuc(null);
    try {
      const k = await istek("/api/kullanicilar", "POST", {
        ...form, ad_soyad: form.ad_soyad.trim() || null,
      });
      setSonuc({ tamam: `${k.kullanici_adi} eklendi (${ROL_AD[k.rol]}).` });
      setForm(BOS_FORM);
      yenile();
    } catch (h) {
      setSonuc({ hata: h.message });
    } finally {
      setMesgul(false);
    }
  };

  const alan = (ad) => (e) => setForm((f) => ({ ...f, [ad]: e.target.value }));

  return (
    <dialog ref={dialogRef} className="olay-detay kullanicilar kart" aria-labelledby={baslikId}
      onClose={onKapat}>
      <div className="olay-detay-ust">
        <div className="baslik-grup">
          <span id={baslikId} className="bolum-baslik">Kullanıcılar</span>
          <span className="bolum-alt">Admin: mod değiştirir ve kullanıcıları yönetir · Operatör: alarmları ilerletir</span>
        </div>
        <button type="button" className="filtre-btn" onClick={() => dialogRef.current?.close()}>
          Kapat
        </button>
      </div>

      <form className="kullanici-ekle" onSubmit={ekle}>
        <span className="tehdit-etiket">Kullanıcı ekle</span>
        <div className="kullanici-ekle-alanlar">
          <label className="durum-alan">
            <span>Kullanıcı adı</span>
            <input type="text" value={form.kullanici_adi} onChange={alan("kullanici_adi")}
              pattern="[a-zA-Z0-9._\-]{3,32}" title="3-32 karakter: harf, rakam, . _ -"
              autoCapitalize="none" spellCheck={false} required autoComplete="off" />
          </label>
          <label className="durum-alan">
            <span>Ad soyad</span>
            <input type="text" value={form.ad_soyad} onChange={alan("ad_soyad")} maxLength={60}
              autoComplete="off" />
          </label>
          <label className="durum-alan">
            <span>Rol</span>
            <select className="mod-secim" value={form.rol} onChange={alan("rol")}>
              {ROLLER.map((r) => <option key={r} value={r}>{ROL_AD[r]}</option>)}
            </select>
          </label>
          <label className="durum-alan">
            <span>Parola <span className="kucuk-mono">(en az {PAROLA_EN_AZ})</span></span>
            <input type="password" value={form.parola} onChange={alan("parola")}
              minLength={PAROLA_EN_AZ} maxLength={128} required autoComplete="new-password" />
          </label>
        </div>
        <div className="durum-dugmeler">
          <button type="submit" className="filtre-btn aktif" disabled={mesgul}>Ekle</button>
        </div>
      </form>

      {sonuc?.hata && <p role="alert" className="durum-hata">{sonuc.hata}</p>}
      {sonuc?.tamam && <p role="status" className="durum-tamam">{sonuc.tamam}</p>}

      <div className="tablo-sarmal">
        <table className="olay-tablo kullanici-tablo">
          <thead>
            <tr>
              <th scope="col">Kullanıcı</th>
              <th scope="col">Rol</th>
              <th scope="col">Durum</th>
              <th scope="col">Son giriş</th>
              <th scope="col">Parola</th>
            </tr>
          </thead>
          <tbody>
            {liste === null && (
              <tr><td colSpan={5} className="bos">Yükleniyor…</td></tr>
            )}
            {liste?.map((k) => {
              const kendisi = k.kullanici_adi === ben.kullanici_adi;
              return (
                <tr key={k.id} className={k.aktif ? undefined : "satir-pasif"}>
                  <td>
                    <span className="kullanici-hucre">
                      <span className="mono">{k.kullanici_adi}</span>
                      <span className="soluk">{k.ad_soyad || "—"}{kendisi ? " · siz" : ""}</span>
                    </span>
                  </td>
                  <td>
                    <select className="mod-secim" value={k.rol} disabled={mesgul}
                      aria-label={`${k.kullanici_adi} rolü`}
                      onChange={(e) => guncelle(k, { rol: e.target.value },
                        `${k.kullanici_adi} artık ${ROL_AD[e.target.value]}.`)}>
                      {ROLLER.map((r) => <option key={r} value={r}>{ROL_AD[r]}</option>)}
                    </select>
                  </td>
                  <td>
                    <span className="tablo-durum">
                      <span className={k.aktif ? "rozet rozet-durum-cozuldu" : "rozet rozet-bilinmeyen"}>
                        {k.aktif ? "Aktif" : "Pasif"}
                      </span>
                      <button type="button" className="durum-btn ikincil"
                        disabled={mesgul || (kendisi && k.aktif)}
                        title={kendisi && k.aktif ? "Kendi hesabınızı pasif yapamazsınız" : undefined}
                        onClick={() => guncelle(k, { aktif: !k.aktif },
                          `${k.kullanici_adi} ${k.aktif ? "pasif yapıldı" : "yeniden aktif"}.`)}>
                        {k.aktif ? "Pasif yap" : "Aktif yap"}
                      </button>
                    </span>
                  </td>
                  <td className="soluk mono">{k.son_giris ? tarihSaatBicim(k.son_giris) : "—"}</td>
                  <td><ParolaSifirla kullanici={k} onSonuc={setSonuc} /></td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </dialog>
  );
}
