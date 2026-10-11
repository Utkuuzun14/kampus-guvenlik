// Olay verisinden panel göstergelerini hesaplayan saf fonksiyonlar.
// Olay listeleri yeni → eski sıralıdır (REST ve WebSocket bu sırayı korur).
import { SEVIYELER, SEVIYE_AD, TEHDIT_PENCERE_SN } from "./sabitler";

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

export const olayKimligi = (o) => o.id ?? `${o.zaman}-${o.dugum}-${o.sensor}`;

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

export const bugunBaslangicSn = (simdi) => {
  const g = new Date(simdi);
  g.setHours(0, 0, 0, 0);
  return Math.floor(g.getTime() / 1000);
};

export const pencereIcinde = (olaylar, simdiSn, pencereSn) =>
  olaylar.filter((o) => o.zaman && simdiSn - o.zaman <= pencereSn);

// Son 5 dakikadaki en yeni kritik olay (alarm bandı için)
export const sonKritikOlay = (olaylar, simdiSn) =>
  pencereIcinde(olaylar, simdiSn, TEHDIT_PENCERE_SN).find(
    (o) => seviyeAnahtari(o.seviye) === "kritik"
  ) ?? null;

// Son 5 dakikadaki en yüksek seviyeden tehdit durumu
export function tehditHesapla(olaylar, simdiSn, onaylananKimlik) {
  const son = pencereIcinde(olaylar, simdiSn, TEHDIT_PENCERE_SN);
  const kritik = son.find((o) => seviyeAnahtari(o.seviye) === "kritik");
  if (kritik) {
    return olayKimligi(kritik) === onaylananKimlik
      ? { tip: "izleniyor", metin: "İZLENİYOR" }
      : { tip: "kritik", metin: "KRİTİK" };
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
