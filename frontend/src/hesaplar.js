// Olay verisinden panel göstergelerini hesaplayan saf fonksiyonlar.
// Olay listeleri yeni → eski sıralıdır (REST ve WebSocket bu sırayı korur).
import {
  SEVIYELER, SEVIYE_AD, TEHDIT_PENCERE_SN, DURUMLAR, AKIS_SEVIYELERI, YANGIN_TEYIT,
} from "./sabitler";

// Türkçe karakterleri ASCII'ye çevirir ("yüksek" → "yuksek")
export const asciiye = (metin) =>
  String(metin ?? "")
    .toLocaleLowerCase("tr-TR")
    .replace(/ü/g, "u")
    .replace(/ı/g, "i")
    .replace(/ö/g, "o")
    .replace(/ş/g, "s")
    .replace(/ğ/g, "g")
    .replace(/ç/g, "c");

// Bilinen bir seviyenin ASCII anahtarı, bilinmiyorsa null
export const seviyeAnahtari = (seviye) => {
  const anahtar = asciiye(seviye);
  return SEVIYELER.includes(anahtar) ? anahtar : null;
};

// "ALEV ALGILANDI" → "Alev algılandı"
export const cumleDuzeni = (metin) => {
  const kucuk = String(metin ?? "").toLocaleLowerCase("tr-TR");
  return kucuk.charAt(0).toLocaleUpperCase("tr-TR") + kucuk.slice(1);
};

export const saatBicim = (unix) =>
  unix
    ? new Date(unix * 1000).toLocaleTimeString("tr-TR", {
        hour: "2-digit", minute: "2-digit", second: "2-digit",
      })
    : "-";

// Bugünse yalnızca saat, değilse "gün.ay saat"
export const tarihSaatBicim = (unix, simdi = new Date()) => {
  if (!unix) return "-";
  if (unix >= bugunBaslangicSn(simdi)) return saatBicim(unix);
  const t = new Date(unix * 1000);
  return `${t.toLocaleDateString("tr-TR", { day: "2-digit", month: "2-digit" })} ${saatBicim(unix)}`;
};

export const bugunBaslangicSn = (simdi) => {
  const g = new Date(simdi);
  g.setHours(0, 0, 0, 0);
  return Math.floor(g.getTime() / 1000);
};

export const pencereIcinde = (olaylar, simdiSn, pencereSn) =>
  olaylar.filter((o) => o.zaman && simdiSn - o.zaman <= pencereSn);

// ---- Olay yaşam döngüsü ----

// Seviyesi operatör akışına giren (orta, yüksek, kritik) olay mı
export const akistaMi = (o) => AKIS_SEVIYELERI.includes(seviyeAnahtari(o.seviye));

// Olayın durumu; alanı olmayan (eski) kayıtlar seviyesine göre varsayılır
export const durumu = (o) =>
  DURUMLAR.includes(o.durum) ? o.durum : akistaMi(o) ? "yeni" : "cozuldu";

export const acikMi = (o) => akistaMi(o) && durumu(o) !== "cozuldu";

// Sıradaki durum (çözülmüş veya akış dışı olayda null)
export const siradakiDurum = (o) =>
  acikMi(o) ? DURUMLAR[DURUMLAR.indexOf(durumu(o)) + 1] : null;

// Olay listesinde id'si eşleşen kaydı yerinde günceller
export const olayGuncelle = (liste, yeni) =>
  liste.some((o) => o.id === yeni.id)
    ? liste.map((o) => (o.id === yeni.id ? { ...o, ...yeni } : o))
    : liste;

// 42 → "42 sn", 134 → "2 dk 14 sn", 7260 → "2 sa 1 dk"
export function sureBicim(sn) {
  if (sn == null || !Number.isFinite(sn) || sn < 0) return "—";
  const t = Math.round(sn);
  if (t < 60) return `${t} sn`;
  if (t < 3600) return `${Math.floor(t / 60)} dk${t % 60 ? ` ${t % 60} sn` : ""}`;
  const dk = Math.floor((t % 3600) / 60);
  return `${Math.floor(t / 3600)} sa${dk ? ` ${dk} dk` : ""}`;
}

// Alarm bandındaki olay: çözülmemiş kritik/yüksek olaylardan en ağırı; kritiklerde
// yangın teyidi tekil alevden önce gelir; eşitse en yenisi.
// Zaman penceresi yok; olay çözülünce bant kaybolur.
export function bantOlayi(acikAlarmlar) {
  const bant = acikAlarmlar.filter(
    (o) => acikMi(o) && ["kritik", "yuksek"].includes(seviyeAnahtari(o.seviye))
  );
  if (bant.length === 0) return { olay: null, adet: 0 };
  const agirlik = (o) =>
    SEVIYELER.indexOf(seviyeAnahtari(o.seviye)) * 2 + (o.sensor === YANGIN_TEYIT ? 1 : 0);
  const olay = bant.reduce((en, o) =>
    agirlik(o) > agirlik(en) || (agirlik(o) === agirlik(en) && o.id > en.id) ? o : en
  );
  return { olay, adet: bant.length };
}

// Çözülmüş akış olayları tehdit seviyesine ve harita alarmına girmez
export const tehditteMi = (o) => !(akistaMi(o) && durumu(o) === "cozuldu");

// Son 5 dakikadaki en yüksek seviyeden tehdit durumu. Kritik olay operatörce
// görüldü/müdahaledeyse İZLENİYOR, çözüldüyse hesaba girmez.
export function tehditHesapla(olaylar, simdiSn) {
  const son = pencereIcinde(olaylar, simdiSn, TEHDIT_PENCERE_SN).filter(tehditteMi);
  const kritikler = son.filter((o) => seviyeAnahtari(o.seviye) === "kritik");
  if (kritikler.length) {
    return kritikler.some((o) => durumu(o) === "yeni")
      ? { tip: "kritik", metin: "KRİTİK" }
      : { tip: "izleniyor", metin: "İZLENİYOR" };
  }
  let enYuksek = -1;
  for (const o of son) {
    enYuksek = Math.max(enYuksek, SEVIYELER.indexOf(seviyeAnahtari(o.seviye)));
  }
  if (enYuksek <= 0) return { tip: "normal", metin: "NORMAL" };
  const anahtar = SEVIYELER[enYuksek];
  return { tip: anahtar, metin: SEVIYE_AD[anahtar].toLocaleUpperCase("tr-TR") };
}

// Son `sureSn` saniyeyi `kova` eşit parçaya bölüp her parçadaki olayları sayar
export function kovalaraBol(olaylar, simdiSn, { sureSn = 3600, kova = 9, filtre = () => true } = {}) {
  const adim = sureSn / kova;
  const sayilar = Array(kova).fill(0);
  for (const o of olaylar) {
    if (!filtre(o)) continue;
    const yas = simdiSn - o.zaman;
    if (yas < 0 || yas >= sureSn) continue;
    sayilar[kova - 1 - Math.floor(yas / adim)]++;
  }
  return sayilar;
}

// Değer dizisini 96×34'lük küçük trend çizgisi noktalarına çevirir
export function sparkNoktalari(degerler, { max, genislik = 96, ust = 6, alt = 30 } = {}) {
  const tepe = Math.max(1, max ?? Math.max(0, ...degerler));
  const adim = degerler.length > 1 ? (genislik - 4) / (degerler.length - 1) : 0;
  return degerler
    .map((v, i) => `${(2 + i * adim).toFixed(1)},${(alt - (v / tepe) * (alt - ust)).toFixed(1)}`)
    .join(" ");
}

export const GUNLER = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"];
const HAFTA_SN = 7 * 86400;

// Son 7 günün olaylarını haftanın günü × saat (7×24) matrisine sayar
export function isiMatrisi(olaylar, simdiSn) {
  const matris = GUNLER.map(() => Array(24).fill(0));
  let toplam = 0;
  for (const o of olaylar) {
    if (!o.zaman || simdiSn - o.zaman > HAFTA_SN || o.zaman > simdiSn + 60) continue;
    const t = new Date(o.zaman * 1000);
    const gun = (t.getDay() + 6) % 7; // Pazartesi = 0
    matris[gun][t.getHours()]++;
    toplam++;
  }
  const enCok = Math.max(0, ...matris.flat());
  return { matris, toplam, enCok };
}

// Son 7 gündeki olayların seviyelere göre sayısı
export function seviyeSayilari(olaylar, simdiSn) {
  const sayilar = Object.fromEntries(SEVIYELER.map((s) => [s, 0]));
  for (const o of olaylar) {
    if (!o.zaman || simdiSn - o.zaman > HAFTA_SN) continue;
    const s = seviyeAnahtari(o.seviye);
    if (s) sayilar[s]++;
  }
  return sayilar;
}
