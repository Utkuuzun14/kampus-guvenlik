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
  yangin_teyit: "Yangın teyidi (duman + alev)",
};

// Tablodaki kısa sensör adları
export const SENSOR_KISA = {
  hareket: "PIR",
  duman: "MQ-2",
  alev: "Alev",
  durum: "Sistem",
  yangin_teyit: "Teyit",
};

// Bileşik (korelasyon) olayın sensör adı
export const YANGIN_TEYIT = "yangin_teyit";

// Güvenlik modu (GET/PUT /api/ayarlar/mod). Hareket seviyesi moda göre değişir.
export const MODLAR = ["otomatik", "mesai", "mesai_disi", "gece"];
export const MOD_AD = {
  otomatik: "Otomatik",
  mesai: "Mesai",
  mesai_disi: "Mesai dışı",
  gece: "Gece",
};

// Olayı üreten kural (olaylar.kural). Bilinmeyen etiket olduğu gibi gösterilir.
export const KURAL_AD = {
  histerezis: "Histerezis",
  gece_modu: "Gece kuralı",
  mesai_disi: "Mesai dışı",
  mesai: "Mesai",
  korelasyon: "Korelasyon",
  baglanti: "Bağlantı",
};

// Düğüm → harita konumu, açıya göre iki set. Koordinatlar o açının viewBox biriminde
// (fotoğraf pikseli): kusbakisi "15 0 1985 1230", perspektif "0 60 2000 1239".
// Konum adı (ör. "Spor Kompleksi") backend'den gelir: /api/dugumler → config.DUGUM_KONUMLARI.
// Burada olmayan düğümler haritaya çizilmez, yalnızca "Aktif düğüm" sayısına girer.
export const DUGUM_KONUMLARI = {
  kusbakisi: {
    dugum1: { x: 690, y: 400 }, // Ana Bina · A Kanadı
    dugum2: { x: 1297, y: 430 }, // Spor Kompleksi
    dugum3: { x: 1245, y: 62 }, // Yurt Binası
  },
  perspektif: {
    dugum1: { x: 850, y: 450 },
    dugum2: { x: 630, y: 825 },
    dugum3: { x: 1930, y: 880 }, // Yurt kadraj dışında; düğüm sağ kenarda
  },
};

// Her iki açıda da konumu tanımlı mı (gösterge/detay için seçilebilir düğümler)
export const haritadaMi = (id) =>
  Boolean(DUGUM_KONUMLARI.kusbakisi[id] && DUGUM_KONUMLARI.perspektif[id]);


// Olay yaşam döngüsü (docs/SOZLESMELER.md §6): yalnızca ileri gidilir
export const DURUMLAR = ["yeni", "goruldu", "mudahale", "cozuldu"];

// Yalnızca bu seviyeler operatör akışına girer; bilgi/uyari oluşurken çözülür
export const AKIS_SEVIYELERI = ["orta", "yuksek", "kritik"];

export const DURUM_AD = {
  yeni: "Yeni",
  goruldu: "Görüldü",
  mudahale: "Müdahalede",
  cozuldu: "Çözüldü",
};

// Durum butonlarının etiketi (hedef duruma göre)
export const DURUM_EYLEM = {
  goruldu: "Görüldü",
  mudahale: "Müdahale",
  cozuldu: "Çöz",
};

// Oturum (token + kullanıcı) bu anahtarla sessionStorage / localStorage'da tutulur
export const OTURUM_ANAHTAR = "kg_oturum";
// Eski panel operatör adını burada hatırlıyordu; artık kullanılmıyor, açılışta silinir
export const ESKI_OPERATOR_ANAHTAR = "kg_operator";

// Roller (docs/SOZLESMELER.md §9)
export const ROLLER = ["admin", "operator"];
export const ROL_AD = {
  admin: "Admin",
  operator: "Operatör",
};
