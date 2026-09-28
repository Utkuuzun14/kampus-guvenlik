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
   +  kritik olayda → e-posta (SMTP)
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
| Duman/gaz | MQ-2 | `deger > ESIK_DUMAN` (varsayılan 1800) | yüksek | Olay kaydı + alarm konusu + e-posta |
| Alev | KY-026 | `deger == 1` | kritik | Olay kaydı + alarm konusu + e-posta (öncelikli) |
| Cihaz çevrimdışı | ESP32 | `durum == "offline"` veya X sn mesaj yok | uyarı | Olay kaydı + panelde "çevrimdışı" işareti |

Alarm seviyeleri: `bilgi < uyari < orta < yuksek < kritik`

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
- `GET /api/durum` → tüm düğümlerin anlık durumu (online/offline, son değerler)
- `GET /api/saglik` → servis sağlık kontrolü

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
