# Ortak Sözleşmeler — IoT Tabanlı Kampüs Güvenlik Sistemi

Bu doküman, sistemin tüm parçalarının (ESP32-S2 firmware, FastAPI backend,
React arayüz) uyacağı ortak kuralları tanımlar. Herhangi bir parçayı yazmadan
önce buraya bakılır. Buradaki bir şey değişirse, tüm parçalar birlikte güncellenir.

---

## 1. Mimari zinciri

```
ESP32-S2 (sensör düğümü)
   │  Wi-Fi + MQTT publish (JSON, QoS 1, LWT)
   ▼
Mosquitto broker  (auth + ileride TLS)
   │  MQTT subscribe
   ▼
FastAPI backend  (kural motoru + SQLite + REST/WebSocket)
   │  REST (geçmiş veri)  +  WebSocket (canlı olay)
   ▼
React dashboard
   +  kritik/yüksek olayda → e-posta (SMTP, bkz. §8)
```

---

## 2. MQTT konu (topic) yapısı

Kök önek: `kampus/guvenlik`. Her sensör düğümünün bir `dugum_id`'si vardır
(örn. `dugum1`), böylece ileride birden fazla düğüm eklenebilir.

| Konu | Yön | Yayınlayan | Açıklama |
|------|-----|-----------|----------|
| `kampus/guvenlik/<dugum_id>/hareket` | yukarı | ESP32 | PIR hareket olayı |
| `kampus/guvenlik/<dugum_id>/duman`   | yukarı | ESP32 | MQ-2 duman/gaz seviyesi |
| `kampus/guvenlik/<dugum_id>/alev`    | yukarı | ESP32 | KY-026 alev durumu |
| `kampus/guvenlik/<dugum_id>/durum`   | yukarı | ESP32 | Cihaz çevrimiçi/çevrimdışı (LWT bunu kullanır) |
| `kampus/guvenlik/<dugum_id>/alarm`   | aşağı  | backend | Merkezi servisin ürettiği alarm kararı |

Demo kontrol konusu (yalnızca sahte üreteç ve `scripts/senaryo.py`; backend dinlemez,
gerçek firmware kullanmaz): `kampus/demo/<dugum_id>/senaryo` →
`{"komut": "duraklat", "sure": 120}`, `{"komut": "devam"}`, `{"komut": "kopma", "sure": 30}`.

Ölçüm yayını: düğüm her turda (3 sn) duman, hareket (0/1) ve alev (0/1) ölçümünü
yayınlar; yalnızca 1 gönderilseydi paneldeki "son ölçüm" eski bir alarmı göstermeye
devam ederdi. Alarm olayı yalnızca kuralı sağlayan ölçümden doğar (§4).

Backend, gelen tüm sensör verilerini tek abonelikle yakalar:
`kampus/guvenlik/+/hareket`, `kampus/guvenlik/+/duman`, vb. (`+` = tek seviye joker).

---

## 3. JSON mesaj şeması

Her sensör mesajı bir JSON nesnesidir. Ham `0/1` yerine yapılandırılmış veri
kullanılır ki backend tek tip işlesin ve ileride alan eklenebilsin.

### Hareket (PIR) — `.../hareket`
```json
{ "dugum": "dugum1", "sensor": "hareket", "deger": 1, "zaman": 1730000000 }
```
- `deger`: 1 = hareket algılandı, 0 = yok

### Duman/gaz (MQ-2) — `.../duman`
```json
{ "dugum": "dugum1", "sensor": "duman", "deger": 512, "zaman": 1730000000 }
```
- `deger`: 0–4095 arası analog okuma (ESP32-S2 ADC ham değeri)

### Alev (KY-026) — `.../alev`
```json
{ "dugum": "dugum1", "sensor": "alev", "deger": 1, "zaman": 1730000000 }
```
- `deger`: 1 = alev algılandı, 0 = yok

### Cihaz durumu — `.../durum`
```json
{ "dugum": "dugum1", "durum": "online", "zaman": 1730000000 }
```
- `durum`: "online" (kart bağlanınca) / "offline" (LWT ile broker basar)
- LWT: her düğüm kendi client'ı ile bağlanırken `.../<dugum_id>/durum` konusuna
  `{"dugum": "<dugum_id>", "durum": "offline", "zaman": 0}` yükünü bırakır (QoS 1).
  Yük bağlanırken sabitlendiği için `zaman` 0'dır; backend geliş anını yazar.
  Temiz kapanışta düğüm "offline"ı kendisi yayınlar, ardından DISCONNECT gönderir.

Ortak alanlar:
- `dugum` (string): hangi düğüm
- `zaman` (int): Unix zaman damgası (saniye). Kart RTC yoksa 0 gönderir,
  backend kendi zamanını yazar.

---

## 4. Eşik ve alarm kuralları

Backend, gelen mesajları bu kurallara göre değerlendirir. Eşikler test
aşamasında güncellenebilir (yapılandırma dosyasından okunur).

| Olay | Kaynak | Kural | Alarm seviyesi | Sistem tepkisi |
|------|--------|-------|---------------|----------------|
| Hareket | PIR | `deger == 1` | orta | Olay kaydı + panelde göster |
| Duman/gaz | MQ-2 | normal → `deger > ESIK_DUMAN` (1800) geçişi | yuksek | Olay kaydı + alarm konusu + e-posta |
| Duman normale döndü | MQ-2 | alarmda → `deger < ESIK_DUMAN_NORMAL` (1600) geçişi | bilgi | Olay kaydı |
| Alev | KY-026 | `0 → 1` geçişi | kritik | Olay kaydı + alarm konusu + e-posta (öncelikli) |
| Alev söndü | KY-026 | `1 → 0` geçişi | bilgi | Olay kaydı |
| Cihaz çevrimdışı | ESP32 | `durum == "offline"` (LWT veya temiz kapanış) | uyari | Olay kaydı + panelde "çevrimdışı" işareti |

Alarm seviyeleri: `bilgi < uyari < orta < yuksek < kritik`

### Histerezis (alarm fırtınası önleme)
- Duman ve alev için olay yalnızca **durum değişiminde** üretilir. Duman 1800'ü
  ilk aştığında 1 `yuksek` olay oluşur; değer **1600'ün altına inene kadar** o
  düğüm için yeni duman olayı oluşmaz (1600-1800 arası ölü bant). 1600 altına
  inince 1 `bilgi` olayı ("Duman/gaz normale döndü") oluşur.
- Alev: `0 → 1` geçişinde 1 `kritik` olay; 1 olarak kaldıkça yeni olay yok;
  `1 → 0` geçişinde 1 `bilgi` olayı ("Alev söndü").
- Durum düğüm bazında backend belleğinde tutulur. Backend yeniden başlarsa tüm
  düğümler "normal" kabul edilir (alarm sürüyorsa bir sonraki eşik üstü ölçüm
  yeni bir olay üretir).
- Ölçümler (`sensor_gecmis`) her mesajda kaydedilir; histerezis yalnızca olay
  üretimini etkiler. Hareket olayları histerezissiz (her `deger == 1` bir olay).
- Eşikler `.env`: `ESIK_DUMAN` (1800), `ESIK_DUMAN_NORMAL` (1600).
- Sessiz kalan (mesaj göndermeyen) düğüm olay üretmez; panelde `/api/dugumler`
  kuralıyla çevrimdışı görünür (§6).

---

## 5. Veritabanı şeması (SQLite)

### Tablo: `olaylar`
Her anlamlı olay (alarm dahil) buraya bir satır olarak yazılır.

| Sütun | Tip | Açıklama |
|-------|-----|----------|
| `id` | INTEGER PK | otomatik artan |
| `dugum` | TEXT | hangi düğüm |
| `sensor` | TEXT | hareket / duman / alev / durum |
| `deger` | INTEGER | okunan değer |
| `seviye` | TEXT | bilgi/uyari/orta/yuksek/kritik |
| `mesaj` | TEXT | insan-okur açıklama ("Alev algılandı") |
| `zaman` | INTEGER | Unix zaman damgası |
| `olusturma` | DATETIME | DB kayıt zamanı (varsayılan now) |

### Tablo: `sensor_gecmis`
Ham sensör okumaları (grafik/trend için). Opsiyonel ama trend analizi için faydalı.

| Sütun | Tip | Açıklama |
|-------|-----|----------|
| `id` | INTEGER PK | otomatik artan |
| `dugum` | TEXT | düğüm |
| `sensor` | TEXT | sensör tipi |
| `deger` | INTEGER | okuma |
| `zaman` | INTEGER | Unix zaman damgası |

---

## 6. Backend API sözleşmesi (React'in kullanacağı)

### REST uç noktaları
- `GET /api/olaylar?limit=50` → son olaylar (JSON dizi)
- `GET /api/durum` → dugum1 durumu ve duman eşiği (`esik_duman`); eski uç, geriye uyumluluk için
- `GET /api/dugumler` → bilinen tüm düğümler (aşağıda)
- `GET /api/gecmis?sensor=duman&dugum=dugum1&limit=50` → bir sensörün son ham okumaları (eski → yeni)
- `GET /api/saglik` → `{"durum": "calisiyor", "mqtt": "bagli" | "kopuk"}`.
  `mqtt`, backend'in broker bağlantısıdır; paneldeki "Broker" ışığı buna bakar.
  Tek bir düğümün kopması bu değeri etkilemez.

### `GET /api/dugumler`
Düğüm listesi = `config.DUGUM_KONUMLARI` (hiç veri göndermemiş olsa da) +
`sensor_gecmis`'te görülen diğer düğümler. Konum adı için tek kaynak backend'dir.

```json
[{
  "id": "dugum3", "konum": "Lojmanlar",
  "cevrimici": false, "veri_yok": false,
  "son_veri_zamani": 1730000000, "son_durum": "offline",
  "son": { "duman": {"deger": 512, "zaman": 1730000000},
           "hareket": {"deger": 1, "zaman": 1729999990}, "alev": null }
}]
```

- `cevrimici`: en son kayıt `durum=offline` (LWT veya temiz kapanış) **değilse** ve
  son veri `CEVRIMDISI_SANIYE` (30 sn) içindeyse `true`.
- `veri_yok`: düğümden hiç kayıt yok (panelde gri, "veri yok"). Böyle bir düğüm
  için "çevrimdışı" olayı ya da e-posta üretilmez; olay yalnızca gelen
  `durum=offline` mesajından doğar.
- `son_veri_zamani`: düğümün kendisinden gelen son mesaj (LWT sayılmaz).
- `konum`: tanımsız düğümde `null`.

### WebSocket
- `WS /ws` → backend, yeni bir olay/alarm oluştuğunda bu kanaldan React'e
  anında JSON gönderir. React canlı güncellenir.

WebSocket mesaj formatı:
```json
{ "tip": "olay", "veri": { ...olay nesnesi... } }
```

---

## 7. Güvenlik kararları

- MQTT broker'da **kullanıcı adı + parola** zorunlu (anonim erişim kapalı).
- Geliştirme sonrası **TLS** (şifreli MQTT) eklenecek — rapor 2.6 ile uyumlu.
- QoS 1: kritik mesajların en az bir kez ulaşması garanti.
- LWT: kart ani kopunca broker otomatik "offline" yayınlar.

---

## 8. Bildirim kuralları (e-posta)

Kod: `backend/app/bildirim.py`, ayarlar: `backend/.env` (şablon: `backend/.env.example`).

- **Hangi olaylar:** seviyesi `BILDIRIM_SEVIYELER` içinde olanlar (varsayılan
  `kritik,yuksek`, yani alev ve duman eşik aşımı). Olay DB'ye yazıldıktan sonra tetiklenir.
- **Spam önleme:** aynı `(düğüm, sensör, seviye)` için `BILDIRIM_BEKLEME_SN`
  (varsayılan 300 sn) içinde ikinci mail gitmez. Bu sürede bastırılan olay
  sayısı bir sonraki mailde "Son 5 dk'da +N benzer olay" olarak yazılır.
- **Engellememe:** gönderim ayrı bir thread'de yapılır; MQTT dinleyici beklemez.
- **Devre dışı kalma:** `SMTP_KULLANICI` veya `SMTP_PAROLA` boşsa ya da
  `BILDIRIM_AKTIF=false` ise mail gönderilmez; başlangıçta tek uyarı loglanır.
  `BILDIRIM_ALICI` boşsa mail gönderen adrese gider.
- **Hata:** yanlış parola / bağlantı yok durumunda hata loglanır, tekrar
  denenmez; bekleme süresi denemeyle başladığı için her olayda yeniden denenmez.
- **Hariç düğüm:** `test_dugum` (canlı test senaryoları) mail üretmez.
- **Gönderim:** SMTP SSL (465), UTF-8, HTML + düz metin. Konu biçimi:
  `[KRİTİK] Alev algılandı — dugum1 (Ana Bina · A Kanadı)`.
  Düğüm konumları `config.DUGUM_KONUMLARI`'ndan gelir (frontend `sabitler.js` ile aynı tutulur).
- **Gizlilik:** parola ve adresler yalnızca `backend/.env`'de durur (git'e girmez).
  Gmail için normal parola değil, 16 haneli **uygulama şifresi** kullanılır.
- **Elle doğrulama:** `python scripts/eposta_test.py` örnek bir kritik mail gönderir.
