// Panelin ortak sabitleri

export const API = "http://127.0.0.1:8000";
export const WS_URL = "ws://127.0.0.1:8000/ws";

export const KURUM = "Samsun Üniversitesi · IoT Güvenlik";

// backend/app/config.py varsayılanları (durum.esik_duman gelirse o kullanılır)
export const ESIK_DUMAN_VARSAYILAN = 1800;
export const CEVRIMDISI_SANIYE = 30;

// Tehdit seviyesi ve alarm bandı için bakılan pencere
export const TEHDIT_PENCERE_SN = 5 * 60;

// docs/SOZLESMELER.md: bilgi < uyari < orta < yuksek < kritik
export const SEVIYELER = ["bilgi", "uyari", "orta", "yuksek", "kritik"];

export const SEVIYE_RENK = {
  bilgi: "#60a5fa",
  uyari: "#2dd4bf",
  orta: "#facc15",
  yuksek: "#fb923c",
  kritik: "#fb7185",
};

export const SEVIYE_AD = {
  bilgi: "Bilgi",
  uyari: "Uyarı",
  orta: "Orta",
  yuksek: "Yüksek",
  kritik: "Kritik",
};

export const SENSOR_AD = {
  hareket: "PIR hareket sensörü",
  duman: "MQ-2 duman sensörü",
  alev: "Alev sensörü",
  durum: "Durum",
};

// Tablodaki kısa sensör adları
export const SENSOR_KISA = {
  hareket: "PIR",
  duman: "MQ-2",
  alev: "Alev",
  durum: "Sistem",
};

// Düğüm → harita üzerindeki yüzde konum (800×440 kroki). Konum adı (ör.
// "Kütüphane") backend'den gelir: /api/dugumler → config.DUGUM_KONUMLARI.
// Burada olmayan düğümler haritaya çizilmez, yalnızca "Aktif düğüm" sayısına girer.
export const DUGUM_KONUMLARI = {
  dugum1: { x: 24.4, y: 28.4 },
  dugum2: { x: 66.9, y: 27.3 },
  dugum3: { x: 24.4, y: 75 },
};

