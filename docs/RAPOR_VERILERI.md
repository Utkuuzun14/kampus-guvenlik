# Rapor Verileri

Akademik rapor için derlenmiş proje verileri: sözleşmeler, test sonuçları, kurulum
ve sunum adımları, proje istatistikleri ve performans ölçümleri.
Derleme tarihi: 12 Ekim 2026. Ölçümler `scripts/olcum.py` ile alındı.

İçindekiler:
1. Proje istatistikleri
2. Arayüzler: API uçları, MQTT konuları, örnek mesaj, SQLite şemaları
3. Kullanılan kütüphaneler
4. Performans ölçümleri
5. Kurulum ve sunum senaryosu (README)
6. Ortak sözleşmeler (docs/SOZLESMELER.md, tamamı)
7. Test sonuçları (docs/TEST_SONUCLARI.md, tamamı)
8. Akıllı kurallar: korelasyon ve bağlama duyarlı kural motoru (15 Ekim 2026 eki)
9. Güvenlik: kimlik doğrulama ve yetkilendirme (15 Ekim 2026 eki)

---

## 1. Proje istatistikleri

| Bilgi | Değer |
|---|---|
| Commit sayısı | 33 (bu belgeyi ekleyen "Rapor" commit'i hariç) |
| İlk commit | 28.09.2026 23:51 — İlk sürüm: mimari, sözleşmeler, Mosquitto yapılandırması ve çalışan FastAPI backend (MQTT + SQLite + REST/WebSocket) |
| Son commit | 12.10.2026 15:44 — Test: 12 Ekim sonuçları |
| Commit dağılımı | 28.09.2026: 1, 29.09.2026: 1, 30.09.2026: 4, 04.10.2026: 4, 12.10.2026: 23 |

Satır sayıları (git'te izlenen dosyalar + `scripts/olcum.py`; `node_modules`, `venv`,
`dist` hariç):

| Bölüm | Dosya | Toplam satır | Boş olmayan satır |
|---|---|---|---|
| Backend — Python (`backend/app`) | 7 | 796 | 677 |
| Frontend — JSX/JS bileşen ve mantık (`frontend/src`) | 17 | 1494 | 1361 |
| Frontend — harita katmanları, tasarımdan üretilmiş JSX | 1 | 306 | 302 |
| Frontend — CSS (`frontend/src`) | 2 | 1387 | 1171 |
| Betikler — Python (`scripts`) | 6 | 1411 | 1175 |
| Betikler — Windows batch (`scripts`) | 1 | 32 | 24 |
| **Toplam kod** | **34** | **5426** | **4710** |

Notlar:
- `haritaKatmanlari.jsx`, `docs/tasarim/KomutaMerkezi.dc.html`'deki dört harita görünümünün
  statik SVG katmanlarından otomatik çevrildi; elle yazılmış koddan ayrı sayıldı.
- `frontend/src` altındaki CSS'in büyük kısmı `App.css`'tir (panel teması ve yerleşim).
- Statik analiz: `npm run lint` (oxlint 1.86.0) 0 hata, 2 uyarı verdi; ikisi de
  `App.jsx`'teki ilk yükleme effect'inde (effect içinde senkron setState ve eksik bağımlılık
  uyarısı).

## 2. Arayüzler

### REST ve WebSocket uçları (FastAPI, `backend/app/main.py`)

| Yöntem | Yol | Açıklama |
|---|---|---|
| GET | `/api/saglik` | Servis sağlık kontrolü + backend'in MQTT broker bağlantısı: `{"durum": "calisiyor", "mqtt": "bagli" \| "kopuk"}` |
| GET | `/api/olaylar?limit=50` | Son olaylar (yeni → eski) |
| GET | `/api/durum` | dugum1 durumu ve duman eşiği (`esik_duman`); geriye uyumluluk için |
| GET | `/api/dugumler` | Bilinen tüm düğümler: konum, çevrimiçi, veri_yok, son veri zamanı, son durum, son ölçümler (duman/hareket/alev) |
| GET | `/api/gecmis?sensor=duman&dugum=dugum1&limit=50` | Bir sensörün son ham ölçümleri (eski → yeni) |
| WS | `/ws` | Yeni olay oluştuğunda `{"tip": "olay", "veri": {...}}` mesajı |

### MQTT konuları (kök: `kampus/guvenlik`, QoS 1)

| Konu | Yön | Yayınlayan | Açıklama |
|---|---|---|---|
| `kampus/guvenlik/<dugum>/hareket` | düğüm → backend | ESP32 / üreteç | PIR hareket (0/1) |
| `kampus/guvenlik/<dugum>/duman` | düğüm → backend | ESP32 / üreteç | MQ-2 analog okuma (0–4095) |
| `kampus/guvenlik/<dugum>/alev` | düğüm → backend | ESP32 / üreteç | KY-026 alev (0/1) |
| `kampus/guvenlik/<dugum>/durum` | düğüm → backend | ESP32 / broker (LWT) | online / offline |
| `kampus/guvenlik/<dugum>/alarm` | backend → düğüm | backend | Alarm kararı (seviye, mesaj, zaman) |
| `kampus/demo/<dugum>/senaryo` | demo | `scripts/senaryo.py` | Yalnızca demo: üreteci duraklat / devam / kopma (backend dinlemez) |

Backend aboneliği: `kampus/guvenlik/+/hareket`, `.../+/duman`, `.../+/alev`, `.../+/durum` (QoS 1).

Örnek mesajlar:

```json
{ "dugum": "dugum1", "sensor": "duman", "deger": 512, "zaman": 1730000000 }
```

```json
{ "dugum": "dugum3", "durum": "offline", "zaman": 0 }
```

İkincisi LWT yüküdür: düğüm bağlanırken broker'a bırakılır ve bağlantı temiz olmayan
şekilde koparsa broker tarafından yayınlanır (`zaman` 0 → backend geliş zamanını yazar).

### SQLite şemaları (`backend/kampus.db`)

```sql
CREATE TABLE olaylar (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dugum TEXT NOT NULL,
    sensor TEXT NOT NULL,
    deger INTEGER,
    seviye TEXT NOT NULL,
    mesaj TEXT,
    zaman INTEGER,
    olusturma DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE sensor_gecmis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dugum TEXT NOT NULL,
    sensor TEXT NOT NULL,
    deger INTEGER,
    zaman INTEGER
);

CREATE INDEX ix_gecmis_dugum_sensor
ON sensor_gecmis (dugum, sensor, id);
```

## 3. Kullanılan kütüphaneler

Backend (Python 3.12.10, `backend/requirements.txt`, ana bağımlılıklar):

| Paket | Sürüm | Kullanım |
|---|---|---|
| fastapi | 0.141.1 | REST/WebSocket API |
| paho-mqtt | 2.1.0 | MQTT istemcisi (backend, üreteç, testler) |
| pydantic | 2.13.5 | veri doğrulama (FastAPI) |
| python-dotenv | 1.2.3 | .env ayarlarını okuma |
| PyJWT | 2.15.1 | panel oturum token'ı (JWT HS256); 15 Ekim 2026'da eklendi (§9) |
| starlette | 1.7.0 | FastAPI altyapısı |
| uvicorn | 0.54.0 | ASGI sunucusu |
| watchfiles | 1.3.0 | geliştirmede otomatik yeniden yükleme (--reload) |
| websockets | 17.1 | WebSocket (uvicorn) ve ölçüm istemcisi |

Standart kütüphane: `sqlite3` (veritabanı), `smtplib` + `ssl` + `email` (e-posta), `threading`.
`requirements.txt` toplam 20 sabitlenmiş paket içerir (dolaylı bağımlılıklar dahil; 12 Ekim'de 19, PyJWT ile 20).
Parola özeti için ek paket kullanılmadı: `hashlib.scrypt` + `hmac` (standart kütüphane).

Frontend (Node v24.21.0, `frontend/package.json`):

| Paket | Tür | package.json | Kurulu sürüm |
|---|---|---|---|
| react | çalışma | `^19.2.8` | 19.3.0 |
| react-dom | çalışma | `^19.2.8` | 19.3.0 |
| recharts | çalışma | `^3.10.1` | 3.10.1 |
| @vitejs/plugin-react | geliştirme | `^6.1.1` | 6.1.1 |
| oxlint | geliştirme | `^1.81.0` | 1.86.0 |
| vite | geliştirme | `^8.3.0` | 8.3.1 |

Altyapı: Mosquitto 2.1.2 (MQTT broker).

## 4. Performans ölçümleri

### Ölçüm ortamı (12.10.2026 15:48)

| Bileşen | Değer |
|---|---|
| İşletim sistemi | Microsoft Windows 11 Pro 10.0.26200 |
| CPU | 13th Gen Intel(R) Core(TM) i7-13700H (14 çekirdek / 20 mantıksal işlemci) |
| RAM | 15.6 GB |
| Python | 3.12.10 (paho-mqtt 2.1.0, websockets 17.1) |
| Mosquitto | 2.1.2 |
| Yerleşim | Broker, backend ve ölçüm betiği aynı makinede (localhost); ağ gecikmesi yok |

### Gecikmeler (ms)

| Ölçüm | n | Ortalama | Medyan | p95 | Min | Max |
|---|---|---|---|---|---|---|
| Uçtan uca: MQTT yayını → WebSocket olayı (hareket) | 100 | 25.7 | 23.1 | 38.0 | 17.4 | 140.9 |
| Olay üretimi: yayın → SQLite (duman eşik aşımı) | 20 | 50.2 | 43.0 | 75.7 | 23.9 | 89.0 |
| Olay üretimi: yayın → SQLite (alev) | 20 | 54.3 | 56.4 | 74.0 | 24.3 | 104.7 |
| LWT: kopma → broker LWT yayını | 5 | 2.1 | 2.2 | 2.9 | 1.0 | 2.9 |
| LWT: kopma → /api/dugumler çevrimdışı | 5 | 40.3 | 36.2 | 52.9 | 23.9 | 52.9 |

Zaman aşımı / başarısız: uçtan uca 0, duman 0, alev 0, LWT 0.

### E-posta

| Ölçüm | Süre | Sonuç |
|---|---|---|
| SMTP SSL (465) bağlantı + giriş + gönderim, 1 gerçek mail (15:46 çalıştırması) | 3409 ms | gönderildi |

### Mesaj kaybı (QoS 1)

| Gönderilen | PUBACK alınan | sensor_gecmis'e yazılan | Farklı değer | Kayıp | Yayın süresi | Tümünün yazılma süresi | Verim |
|---|---|---|---|---|---|---|---|
| 500 | 500 | 500 | 500 | %0.0 | 0.37 sn | 10.65 sn | 47 mesaj/sn |

Yöntem notları:
- Süreler `time.perf_counter()` ile aynı makinede ölçüldü (saat senkronu gerekmez).
- Olay üretimi SQLite'ı 2 ms aralıkla yoklayarak ölçüldü (çözünürlük ~2 ms). Her tekrardan önce histerezis normale çekildi.
- LWT süreleri socket'in DISCONNECT gönderilmeden kapatıldığı andan başlar; API süresi /api/dugumler 10 ms aralıkla yoklanarak ölçüldü.
- Uçtan uca ölçüm her yayında bir olay üreten hareket=1 ile yapıldı; WebSocket yalnızca olayları iletir.
- Mesaj kaybı testinde 500 mesaj beklemesiz art arda yayınlandı (yük testi); değerler 1000-1499 olduğundan olay üretmez, yalnızca ölçüm olarak yazılır.

Tutarlılık: ölçüm aynı gün iki kez çalıştırıldı. 15:46 çalıştırmasında LWT süresi istemci
tarafındaki bir bekleme yüzünden yanlış ölçüldü (paho ağ thread'inin ~1 sn'lik `select`
beklemesi süreye dahildi); betik düzeltildi ve ana sonuçlar 15:48 çalıştırmasından alındı.
Gerçek e-posta yalnızca 15:46'da gönderildi. Diğer ölçümlerin iki çalıştırmadaki değerleri:

| Ölçüm (ort / medyan / p95, ms) | 15:46 | 15:48 (ana) |
|---|---|---|
| Uçtan uca MQTT → WebSocket | 39.8 / 37.2 / 48.3 | 25.7 / 23.1 / 38.0 |
| Olay üretimi (duman) | 47.3 / 42.4 / 57.3 | 50.2 / 43.0 / 75.7 |
| Olay üretimi (alev) | 49.9 / 44.6 / 58.1 | 54.3 / 56.4 / 74.0 |
| Mesaj kaybı (500 mesaj) | 0 kayıp, 72 mesaj/sn | 0 kayıp, 47 mesaj/sn |

Değerlendirme:
- Uçtan uca gecikme (MQTT yayını → backend → SQLite → WebSocket) medyanda ~23 ms;
  p95 38 ms. Panel 3 sn'lik yoklamaya ek olarak olayları WebSocket ile anında alır.
- "Olay üretimi" (SQLite yoklamalı) değerlerinin uçtan uca değerlerden yüksek çıkması
  yöntemden kaynaklanır: olay WebSocket'e DB'ye yazıldıktan sonra gider, yani gerçek yazma
  süresi uçtan uca süreden kısadır. Muhtemel neden, 2 ms'lik yoklamanın SQLite'ta yazıcıyla
  kilit paylaşımına girerek yazmayı geciktirmesidir (doğrulanmadı). WebSocket ölçümü bu
  nedenle olay üretimi için daha güvenilir bir üst sınırdır.
- LWT: broker temiz olmayan kopmayı ~2 ms'de fark edip LWT'yi yayınladı; düğüm
  /api/dugumler'de ~36 ms içinde çevrimdışı göründü. Panel bunu en geç bir sonraki
  3 sn'lik yoklamada gösterir. Bu ölçüm socket'in kapandığı (bağlantının işletim sistemi
  tarafından kapatıldığı) durumu kapsar. Güç ya da ağ kesilmesi gibi bağlantının
  kapatılamadığı kopmalarda broker kopmayı keepalive süresinin 1,5 katı sonra fark eder
  (sahte üreteçte keepalive 60 sn → ~90 sn; ESP32 firmware'inde seçilecek değere bağlıdır).
- QoS 1 ile 500 mesajlık beklemesiz yükte kayıp olmadı. Backend her ölçümü ayrı bir SQLite
  bağlantısı ve commit ile yazdığı için verim ~47–72 mesaj/sn; üç düğümün normal yükü
  ~3 mesaj/sn (düğüm başına 3 sn'de 3 ölçüm) olduğundan bu, ~15 kat pay bırakır.
- E-posta gönderimi (TLS el sıkışma + giriş + gönderim) ~3.4 sn sürdü; gönderim ayrı
  thread'de yapıldığından MQTT dinleyiciyi bekletmez (T6: dinleyici ~1 ms'de döner).

## 5. Kurulum ve sunum senaryosu (README)

### Kurulum sırası (geliştirme planı)
1. Ortak sözleşmeler — `docs/SOZLESMELER.md`
2. Mosquitto broker kurulumu (Windows)
3. FastAPI backend
4. React dashboard
5. Sahte veri üreteci (donanım gelene kadar test)
6. ESP32-S2 firmware (donanım gelince)
7. E-posta bildirim + uçtan uca test

### Sunum senaryosu
Ön koşul: `backend/.env` dolu (e-posta için `SMTP_KULLANICI` / `SMTP_PAROLA`).
Komutlar proje kökünden, backend venv aktifken çalıştırılır.

0. **Veritabanını sıfırla:** `python scripts/db_sifirla.py`
   → önce `backend/yedekler/kampus_YYYYMMDD_HHMM.db` yedeği alınır, kayıt sayıları
   gösterilir ve "EVET" onayı istenir (sorusuz: `--evet`). olaylar ve sensor_gecmis
   boşaltılır, tablo yapısı korunur. Backend açıkken de çalışır; ardından backend'i
   yeniden başlatmak bellekteki alarm durumunu da sıfırlar.
1. **Sistemi başlat:** `scripts\baslat.bat` → Broker, Backend, Sahte Veri (üç düğüm)
   ve React paneli ayrı pencerelerde açılır. Panel: http://localhost:5173
2. **Sakin durum (~1 dk):** panelde "Aktif düğüm 3/3", haritada üç düğüm yeşil çizgiyle
   Mosquitto'ya bağlı. Üreteç varsayılan olarak sakindir: alev üretmez, duman eşiği
   düğüm başına ~10-15 dk'da bir kısa süre aşılır.
3. **İzinsiz giriş:** `python scripts/senaryo.py hareket dugum2`
   → Spor Kompleksi'nde ~25 sn art arda hareket (orta seviye olaylar, olay akışında görünür).
4. **Yangın:** haritada dugum1'e tıkla (gösterge "MQ-2 · dugum1"), sonra
   `python scripts/senaryo.py yangin dugum1`
   → duman 30 sn'de kademeli yükselip eşiği (1800) aşar, ardından alev = kritik:
   alarm bandı, tehdit seviyesi KRİTİK, kırmızı harita halesi ve e-posta.
   Histerezis sayesinde olay akışında yalnızca 4 olay görünür: duman eşiği aşıldı
   (yüksek), alev (kritik), duman normale döndü ve alev söndü (bilgi).
   60 sn sonra duman düşer, alev "Yok" olur. Alarm bandındaki "Onayla" ile alarm
   onaylanır.
5. **Bağlantı kopması (LWT):** `python scripts/senaryo.py kopma dugum3`
   → Yurt Binası düğümü DISCONNECT göndermeden düşer, broker LWT yayınlar: "Aktif düğüm
   2/3", dugum3 çizgisi sönük gri. 30 sn sonra geri gelir ve 3/3 olur.
6. **Testler (isteğe bağlı):** üreteci kapatıp `python scripts/test_senaryolari.py`
   (T1-T7, sonuçlar `docs/TEST_SONUCLARI.md`).

Notlar:
- Senaryo süresince üreteç ilgili düğümün ölçümlerini duraklatır, değerler karışmaz.
  Yangın ve hareket senaryoları üreteç kapalıyken de çalışır; kopma senaryosu için
  üretecin o düğümü çalıştırıyor olması gerekir.
- Bekleme kuralı gereği aynı düğüm/sensör/seviye için 5 dk'da en fazla bir e-posta
  gider. Yangın senaryosunu 5 dk içinde tekrarlarsan ikinci mail gelmez.
- Üreteç ayrıca dugum3'ü kendiliğinden 3-5 dk'da bir düşürür; sunum sırasında bu da
  olabilir. Yalnızca seçili düğümler için: `python scripts/sahte_veri.py --dugumler dugum1,dugum2`.

## 6. Ortak sözleşmeler (docs/SOZLESMELER.md)

### Ortak Sözleşmeler — IoT Tabanlı Kampüs Güvenlik Sistemi

Bu doküman, sistemin tüm parçalarının (ESP32-S2 firmware, FastAPI backend,
React arayüz) uyacağı ortak kuralları tanımlar. Herhangi bir parçayı yazmadan
önce buraya bakılır. Buradaki bir şey değişirse, tüm parçalar birlikte güncellenir.

---

#### 1. Mimari zinciri

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

#### 2. MQTT konu (topic) yapısı

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

#### 3. JSON mesaj şeması

Her sensör mesajı bir JSON nesnesidir. Ham `0/1` yerine yapılandırılmış veri
kullanılır ki backend tek tip işlesin ve ileride alan eklenebilsin.

##### Hareket (PIR) — `.../hareket`
```json
{ "dugum": "dugum1", "sensor": "hareket", "deger": 1, "zaman": 1730000000 }
```
- `deger`: 1 = hareket algılandı, 0 = yok

##### Duman/gaz (MQ-2) — `.../duman`
```json
{ "dugum": "dugum1", "sensor": "duman", "deger": 512, "zaman": 1730000000 }
```
- `deger`: 0–4095 arası analog okuma (ESP32-S2 ADC ham değeri)

##### Alev (KY-026) — `.../alev`
```json
{ "dugum": "dugum1", "sensor": "alev", "deger": 1, "zaman": 1730000000 }
```
- `deger`: 1 = alev algılandı, 0 = yok

##### Cihaz durumu — `.../durum`
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

#### 4. Eşik ve alarm kuralları

Backend, gelen mesajları bu kurallara göre değerlendirir. Eşikler test
aşamasında güncellenebilir (yapılandırma dosyasından okunur).

| Olay | Kaynak | Kural | Alarm seviyesi | Sistem tepkisi |
|------|--------|-------|---------------|----------------|
| Hareket | PIR | `0 → 1` geçişi, düğüm başına 30 sn bekleme (23.11.2026) | moda göre (§8) | Olay kaydı + panelde göster |
| Duman/gaz | MQ-2 | normal → `deger > ESIK_DUMAN` (1800) geçişi | yuksek | Olay kaydı + alarm konusu + e-posta |
| Duman normale döndü | MQ-2 | alarmda → `deger < ESIK_DUMAN_NORMAL` (1600) geçişi | bilgi | Olay kaydı |
| Alev | KY-026 | `0 → 1` geçişi | kritik | Olay kaydı + alarm konusu + e-posta (öncelikli) |
| Alev söndü | KY-026 | `1 → 0` geçişi | bilgi | Olay kaydı |
| Cihaz çevrimdışı | ESP32 | `durum == "offline"` (LWT veya temiz kapanış), 10 sn içinde `online` gelmezse (23.11.2026) | uyari | Olay kaydı + panelde "çevrimdışı" işareti |

Alarm seviyeleri: `bilgi < uyari < orta < yuksek < kritik`

##### Histerezis (alarm fırtınası önleme)
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
  üretimini etkiler. Hareket olayı yalnızca `0 → 1` geçişinde ve düğüm başına
  `HAREKET_BEKLEME_SN` (30 sn) beklemeyle üretilir (23.11.2026, güncel: docs/SOZLESMELER.md §4).
- Eşikler `.env`: `ESIK_DUMAN` (1800), `ESIK_DUMAN_NORMAL` (1600).
- Sessiz kalan (mesaj göndermeyen) düğüm olay üretmez; panelde `/api/dugumler`
  kuralıyla çevrimdışı görünür (§6).

---

#### 5. Veritabanı şeması (SQLite)

##### Tablo: `olaylar`
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

##### Tablo: `sensor_gecmis`
Ham sensör okumaları (grafik/trend için). Opsiyonel ama trend analizi için faydalı.

| Sütun | Tip | Açıklama |
|-------|-----|----------|
| `id` | INTEGER PK | otomatik artan |
| `dugum` | TEXT | düğüm |
| `sensor` | TEXT | sensör tipi |
| `deger` | INTEGER | okuma |
| `zaman` | INTEGER | Unix zaman damgası |

---

#### 6. Backend API sözleşmesi (React'in kullanacağı)

##### REST uç noktaları
- `GET /api/olaylar?limit=50` → son olaylar (JSON dizi)
- `GET /api/durum` → dugum1 durumu ve duman eşiği (`esik_duman`); eski uç, geriye uyumluluk için
- `GET /api/dugumler` → bilinen tüm düğümler (aşağıda)
- `GET /api/gecmis?sensor=duman&dugum=dugum1&limit=50` → bir sensörün son ham okumaları (eski → yeni)
- `GET /api/saglik` → `{"durum": "calisiyor", "mqtt": "bagli" | "kopuk"}`.
  `mqtt`, backend'in broker bağlantısıdır; paneldeki "Broker" ışığı buna bakar.
  Tek bir düğümün kopması bu değeri etkilemez.

##### `GET /api/dugumler`
Düğüm listesi = `config.DUGUM_KONUMLARI` (hiç veri göndermemiş olsa da) +
`sensor_gecmis`'te görülen diğer düğümler. Konum adı için tek kaynak backend'dir.

```json
[{
  "id": "dugum3", "konum": "Yurt Binası",
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
  `durum=offline` mesajından, 10 sn tolerans içinde `online` gelmezse doğar.
- `son_veri_zamani`: düğümün kendisinden gelen son mesaj (LWT sayılmaz).
- `konum`: tanımsız düğümde `null`.

##### WebSocket
- `WS /ws` → backend, yeni bir olay/alarm oluştuğunda bu kanaldan React'e
  anında JSON gönderir. React canlı güncellenir.

WebSocket mesaj formatı:
```json
{ "tip": "olay", "veri": { ...olay nesnesi... } }
```

---

#### 7. Güvenlik kararları

- MQTT broker'da **kullanıcı adı + parola** zorunlu (anonim erişim kapalı).
- Geliştirme sonrası **TLS** (şifreli MQTT) eklenecek — rapor 2.6 ile uyumlu.
- QoS 1: kritik mesajların en az bir kez ulaşması garanti.
- LWT: kart ani kopunca broker otomatik "offline" yayınlar.

---

#### 8. Bildirim kuralları (e-posta)

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

## 7. Test sonuçları (docs/TEST_SONUCLARI.md)

### Test Sonuçları (Rapor Tablo 6)

Test tarihi: 12 Ekim 2026, 15:39 (otomatik test scripti ile, T1-T8 tek çalıştırma)
Son çalıştırma: 23 Kasım 2026, 18:22 (T1-T12 + T17-T18 tek çalıştırma, hepsi başarılı;
hareket kenarı/bekleme ve çevrimdışı toleransı eklendikten sonra). Önceki: 15 Ekim
2026, 14:49 (T1-T12; 14:37 ve 14:49'da aynı backend açıkken art arda iki kez)
Yöntem: scripts/test_senaryolari.py — her senaryo broker'a kontrollü mesaj
gönderir, backend API'sinden (T9'da ayrıca PATCH ve WebSocket, T11'de mod uçları
ve WebSocket, T12'de giriş/yetki uçları) sonuç doğrulanır. Script başta güvenlik
modunu mesai_disi yapar (hareket = orta) ve sonunda kullanıcının önceki moduna (ve
"değiştiren" kaydına) geri alır. API korumalı olduğundan başta rastgele adlı ve
parolalı geçici bir admin ve operatör oluşturulur; istekler admin token'ıyla, durum
geçişleri operatör token'ıyla yapılır; sonda bu kullanıcılar ve giriş kayıtları silinir.
Ortam: Mosquitto broker + FastAPI backend + SQLite (sahte üreteç kapalı,
e-posta bildirimi açık). Veritabanı 15:38'de scripts/db_sifirla.py ile sıfırlandı
(yedek: backend/yedekler/kampus_20261012_1538.db); olay id'leri bu yüzden küçüktür.
Gerçek donanım testleri (T13-T16): 23 Kasım 2026, 17:31-18:03, elle. Düğüm `dugum1`
= Wemos LOLIN S2 Mini (firmware/), sahte üreteç kapalı, mod otomatik (mesai saati).
Sonuçlar panelden ve veritabanındaki olay kayıtlarından doğrulandı.

| Test | Senaryo | Gönderilen | Beklenen | Sonuç | Durum |
|------|---------|-----------|----------|-------|-------|
| T1 | Hareket algılama (PIR) | hareket=1 (mod: mesai_disi) | orta seviye olay | orta - "Hareket algılandı · mesai dışı" | BAŞARILI |
| T2 | Duman/gaz eşik aşımı (MQ-2) | normal → duman=2500 | yüksek seviye uyarı | yuksek - eşik aşıldı | BAŞARILI |
| T2b | Duman normal (MQ-2) | duman=400 | alarm oluşmamalı | yeni olay yok | BAŞARILI |
| T3 | Alev algılama (KY-026) | alev 0 → 1 | kritik olay | kritik - "ALEV ALGILANDI" (T2'den 1,5 sn sonra geldiği için ek olarak yangin_teyit oluştu) | BAŞARILI |
| T4 | MQTT mesaj iletimi | - | mesaj broker→backend | T1-T3 kanıtlıyor | BAŞARILI |
| T5 | Web arayüzü / API | - | API yanıt veriyor, backend broker'a bağlı | /api/saglik OK, mqtt=bagli | BAŞARILI |
| T6 | Bildirim (e-posta) | alev=1, hareket=1, duman=2500, alev 0→1 (iki kez) | kritik/yüksekte mail, orta/bilgide yok, bekleme süresinde tekrar yok | 8/8 kontrol geçti (SMTP taklit) | BAŞARILI |
| T7 | LWT ile çevrimdışı ve geri gelme | online → socket kapatma (DISCONNECT yok) → yeniden bağlanma | /api/dugumler'de çevrimdışı, sonra çevrimiçi | LWT 0,1 sn'de yansıdı, geri bağlanınca anında çevrimiçi | BAŞARILI |
| T8 | Histerezis (alarm fırtınası önleme) | duman 2100, 2500, 2900, 2300, 1900 → 1700 → 1500; alev 1, 1 → 0 | tek yüksek olay, ölü bantta olay yok, 1600 altında tek bilgi; alev sürerken olay yok, sönünce tek bilgi | 5/5 adım beklenen olay sayısıyla | BAŞARILI |
| T9 | Olay yaşam döngüsü (alarm onaylama) — 15 Ekim 2026, kimlik doğrulamayla uyarlandı | hareket=1 → operatör token'ıyla PATCH goruldu (gövdede sahte onaylayan) → PATCH cozuldu → geri/aynı geçiş, hatalı gövdeler | durum=yeni; ileri geçişler 200; atlanan adım zamanı dolu; kim/onaylayan = token sahibi, gövdedeki onaylayan yok sayılır; geri 409; olmayan id 404; geçersiz durum ve 301 karakter not 422; WS olay_guncelleme; istatistik değer döner | 13/13 kontrol geçti | BAŞARILI |
| T10 | Yangın teyidi (korelasyon) — 15 Ekim 2026 | duman 2500 → 2 sn → alev=1; yangın sürerken duman 2900, alev 1→0→1; normale dönüş → yeniden yangın; ters sıra (alev → 2 sn → duman); kural fonksiyonu birim testi | tek yangin_teyit (kritik), iliskili = [duman, alev]; sürerken yeni teyit yok; normalden sonra yeni teyit; ters sırada teyit; pencere dışında (11 sn) teyit yok; mail konusu "YANGIN TEYİTLİ" | 12/12 kontrol geçti | BAŞARILI |
| T11 | Güvenlik modu ve zamana bağlı hareket kuralı — 15 Ekim 2026 | PUT mesai / mesai_disi / gece + her birinde hareket=1; PUT "tatil" ve boş gövde; hareket_seviyesi("otomatik", t) birim testi | mesai → bilgi (otomatik çözülmüş), mesai_disi → orta, gece → yuksek; WS "mod" mesajı; geçersiz → 422; hafta içi 10:00 bilgi, 20:00 orta, 02:00 yüksek, cumartesi 11:00 orta | 10/10 kontrol geçti (saat eşlemesi 9/9 vaka) | BAŞARILI |
| T12 | Kimlik doğrulama ve yetkilendirme — 15 Ekim 2026 | token'sız / sahte imzalı / süresi dolmuş istek; yanlış parola, olmayan kullanıcı, pasif kullanıcı; 6 hatalı giriş; operatör ve admin ile PUT mod, /api/kullanicilar; admin kendini pasif yapma; operatör PATCH durum; WS token'sız / bozuk / geçerli | 401 (genel mesaj); 429 + Retry-After; operatör 403, admin 200 + degistiren; 409; kim = operatörün adı; WS 4401; /api/saglik 200; hiçbir yanıtta parola özeti yok | 18/18 kontrol geçti | BAŞARILI |
| T13 | Güç ve bağlantı (gerçek donanım) — 23 Kasım 2026 | sensörler VBUS 5 V'tan; MQ-2 AO 2x10k, alev DO 10k+20k gerilim bölücüyle ESP32-S2'ye | Wi-Fi + MQTT bağlantısı, 3 sn yayın aralığı | Wi-Fi ve MQTT bağlandı (192.168.1.9:1883, LWT + online), duman → hareket → alev 3 sn'de bir | BAŞARILI |
| T14 | Hareket algılama (PIR, gerçek donanım) — 23 Kasım 2026 | sensörün önü kapatıldı, sonra önünde el sallandı | kapalıyken olay yok, el sallanınca hareket olayı | kapalıyken 60 sn+ olay yok (17:44:49 → 17:46:18 arası hareket olayı yok); el sallanınca "Hareket algılandı" | BAŞARILI |
| T15 | Alev algılama (KY-026, gerçek donanım) — 23 Kasım 2026 | çakmak, 20-30 cm mesafe | kritik olay | #2382 kritik - "ALEV ALGILANDI" (17:48:56); çakmak çekilince #2393 bilgi - "Alev söndü" | BAŞARILI |
| T16 | Duman/gaz eşik aşımı (MQ-2, gerçek donanım) — 23 Kasım 2026 | ısınma sonrası temiz hava → bütan gazı | temizde alarm yok, gazda 1800 eşiği aşılınca yüksek uyarı | temizde ham ~300; gazda 2831 → #2425 yüksek - "Duman/gaz eşiği aşıldı" (17:51:04); 1292'ye inince #2432 bilgi - "normale döndü" | BAŞARILI |
| T17 | Hareket olay kenarı ve bekleme — 23 Kasım 2026 | hareket 0 → 1; 5 kez 1 → 1; 5 sn sonra 0 → 1; 30 sn sonra 0 → 1; `hareket_gecisi` birim testi | yalnızca 0 → 1'de olay, sürerken olay yok, düğüm başına 30 sn içinde yeni olay yok, seviye moda göre | 6/6 kontrol geçti (orta, tek olay; bekleme içinde 0, sonra 1 olay; birim testi 10/10 adım) | BAŞARILI |
| T18 | Çevrimdışı toleransı — 23 Kasım 2026 | LWT → ~1 sn sonra online; LWT → geri gelmez | 10 sn içinde geri gelirse olay yok; gelmezse süre dolunca tek uyari | 4/4 kontrol geçti (kısa kopmada 12 sn olay yok; gerçek kopmada 10,3 sn'de tek olay) | BAŞARILI |

#### Notlar
- Testler test_dugum düğümü ile yapıldı; çalışma sonunda bu düğümün kayıtları
  silindi (olaylar: 8, sensor_gecmis: 20). Gerçek veri kirlenmedi.
- Olay id'leri artarak oluştu (#6 → #8): gerçekten yeni olay üretildiği doğrulandı.
- Histerezis durumu backend belleğinde tutulduğu için script başta test_dugum'u
  normale çeker (duman=400, alev=0). Aynı backend açıkken art arda iki kez
  çalıştırıldığında da T1-T8 başarılı oldu (14:31 ve 14:33 çalıştırmaları).
- Çalışma sırası T1, T2, T3, T8, T2b, T4-T7'dir: T8, T2/T3'ün açtığı alarmları
  kapatır; T2b (duman=400) normal durumda alarm üretmediğini doğrular.
- T2b: normal değerde yeni olay oluşmadığı doğrulandı (yanlış alarm üretilmiyor).
- T3 sırasında test_dugum için e-posta gönderilmedi (test_dugum bildirimden hariç).
- T6: gerçek mail gönderilmedi; SMTP gönderim fonksiyonu taklit edildi (mock),
  MQTT mesaj işleyicisi süreç içinde sahte DB ile çağrıldı. Doğrulananlar:
  - kritik (alev) olayında mail gönderiliyor, konu "[KRİTİK] Alev algılandı — ..."
  - SMTP 500 ms sürse de MQTT işleyicisi beklemiyor (~1 ms, gönderim ayrı thread'de)
  - orta (hareket) olayında mail gönderilmiyor
  - yüksek (duman eşik aşımı) olayında mail gönderiliyor
  - BILDIRIM_BEKLEME_SN (300 sn) içinde aynı düğüm/sensör/seviye için ikinci mail engelleniyor
  - süre dolunca yeni mail gidiyor ve bastırılan olay "+1 benzer olay" olarak yazılıyor
  - "alev söndü" (bilgi) olayında mail gönderilmiyor
  - Histerezis nedeniyle her yeni alev olayı için önce alev=0 gönderilir.
  - T6 broker/backend gerektirmez.
- T7: sahte üretecin kopma fonksiyonu kullanıldı (scripts/sahte_veri.py:
  istemci_olustur + baglantiyi_kopar). test_dugum için LWT'li client bağlandı →
  socket DISCONNECT gönderilmeden kapatıldı → broker LWT'yi yayınladı →
  /api/dugumler 0,1 sn içinde cevrimici=false, son_durum=offline gösterdi →
  yeni client "online" yayınlayınca tekrar cevrimici=true. Rastgele 3-5 dk'lık
  kopmayı beklememek için kopma hemen tetiklendi.
- T8 ek doğrulama: `python scripts/senaryo.py yangin test_dugum` (90 sn, 80 ölçüm)
  tam 4 olay üretti: yüksek (duman 1875), kritik (alev), bilgi (duman normale
  döndü, 1500), bilgi (alev söndü). Histerezisten önce aynı senaryo 1 kritik +
  24 yüksek olay üretiyordu. Ölçümlerin hepsi sensor_gecmis'e yazıldı.
- Gerçek SMTP gönderimi scripts/eposta_test.py ile ayrıca doğrulandı (12 Ekim 2026,
  Gmail SMTP SSL 465).
- T9 (15 Ekim 2026, 12:51): test_dugum'a hareket=1 gönderildi, #394 orta olay
  `durum=yeni`, `onaylayan=null` geldi. Doğrulananlar:
  - PATCH goruldu (operatör + not) → 200, `goruldu_zaman` dolu, `mudahale_zaman` boş
  - açık bir WebSocket istemcisine `{"tip": "olay_guncelleme"}` mesajı geldi (durum=goruldu)
  - PATCH cozuldu → 200; atlanan `mudahale_zaman` = `cozuldu_zaman`
  - olay_adimlari: [goruldu (T9 Operatör, "Kamera kontrol ediliyor"), cozuldu (T9 Operatör)]
  - cozuldu → goruldu: 409 (`mevcut=cozuldu`); cozuldu → cozuldu: 409
  - olmayan id: 404; durum=xyz, durum=yeni, boş onaylayan, 41 karakter onaylayan,
    301 karakter not: hepsi 422
  - `?durum=acik` listesinde çözülen olay ve çözülmüş kayıt yok
  - T8'in ürettiği 3 bilgi olayı oluşurken `cozuldu` / `onaylayan=sistem`
  - /api/istatistik/mudahale → `{acik_sayisi: 4, ort_gorulme_sn: 2.1, ort_cozum_sn: 2.1,
    cozulen_sayisi: 1}` (açık 4: T1, T2, T3 ve T8'in çözülmemiş alarmları)
  - Temizlik: olaylar 9, olay_adimlari 2, sensor_gecmis 21 kayıt silindi.
- T10 (15 Ekim 2026, 13:55): korelasyon penceresi 10 sn (varsayılan).
  - duman 2500 (#500, yuksek) → 2 sn → alev=1 (#501, kritik) → #502 yangin_teyit,
    kritik, `kural=korelasyon`, `durum=yeni`, `iliskili=[500, 501]`;
    `GET /api/olaylar/502` iliskili alanını liste olarak döndürdü. Orijinal duman ve
    alev olayları `kural=histerezis` ile korundu.
  - Yangın sürerken (duman alarmda) duman 2900, alev 1 → 0 → 1: yalnızca alev bilgi +
    alev kritik oluştu, yeni teyit yok (düğüm kilitli).
  - normale dönüş (duman 400, alev 0) → duman 2500 → 1 sn → alev=1: yeni teyit.
  - Ters sıra: alev=1 (#512) → 2 sn → duman 2500 (#513) → teyit, `iliskili=[512, 513]`.
  - Pencere dışı durum, canlı testte pencereyi düşürmek yerine saf `korelasyon()`
    fonksiyonuyla denendi: 11 sn fark → teyit yok; tam 10 sn → teyit; kilitliyken
    alevin söndüp yanması → teyit yok; ikisi de normale dönünce → yeni teyit.
  - `bildirim.mail_olustur` teyit olayı için konu
    "[KRİTİK] YANGIN TEYİTLİ — dugum1 (Ana Bina · A Kanadı)" ve "İlişkili: #412, #413"
    satırını üretti (gerçek mail gönderilmedi; test_dugum bildirimden hariç).
  - T6 yalnızca tekil olay bildirimini ölçtüğü için süreç içinde korelasyonu kapatır
    ve modu mesai_disi'ye sabitler; teyit maili burada doğrulanır.
- T11 (15 Ekim 2026, 13:55): açık bir WebSocket istemcisi varken PUT mesai → 200 ve
  `{"tip": "mod", "veri": {"mod": "mesai", ...}}` mesajı geldi. Her modda hareket=1:
  - mesai → bilgi, `durum=cozuldu`, `onaylayan=sistem`, `kural=mesai`, "Hareket algılandı · mesai saati"
  - mesai_disi → orta, `durum=yeni`, `kural=mesai_disi`
  - gece → yuksek, `kural=gece_modu`, "Hareket algılandı · gece modu"
  - GET → `{mod: gece, etkin_mod: gece}`; PUT "tatil" ve boş gövde → 422, mod değişmedi.
  - Otomatik mod, `hareket_seviyesi("otomatik", t)` ile (varsayılan saatler sabitlenerek)
    9 an için doğrulandı: hafta içi 10:00 mesai/bilgi, 20:00 mesai dışı/orta,
    02:00 gece/yüksek, cumartesi 11:00 mesai dışı/orta, cumartesi 02:00 gece,
    sınırlar 08:00 mesai, 18:00 mesai dışı, 23:00 gece, 06:00 mesai dışı.
  - Elle seçilen mod saatten bağımsız (mesai/mesai_disi/gece → bilgi/orta/yuksek).
  - Çalışma sonunda mod kullanıcının önceki değerine (otomatik) geri alındı.
  - Temizlik: olaylar 30, olay_adimlari 2, sensor_gecmis 42 kayıt silindi.
- T9 uyarlaması (15 Ekim 2026, kimlik doğrulama): `onaylayan` artık token'dan geldiği
  için "boş onaylayan" ve "41 karakter onaylayan → 422" kontrolleri, "gövdedeki
  onaylayan yok sayılıyor" kontrolüne dönüştü: gövdede "Sahte Kişi" gönderildi,
  `olay_adimlari.kim` ve `onaylayan` = geçici operatörün adı ("Test Operatör …").
  durum=xyz, durum=yeni ve 301 karakter not yine 422.
- T12 (15 Ekim 2026, 14:49): geçici kullanıcılar `t_admin_<6 hex>` / `t_op_<6 hex>`,
  parolalar `secrets.token_urlsafe` ile rastgele. Doğrulananlar:
  - `/api/saglik` token'sız 200; `/api/olaylar` token'sız 401 ("Giriş yapılmamış")
  - başka bir anahtarla imzalanmış ve rolü "admin" yazılmış token → 401
  - yanlış parola ve olmayan kullanıcı → ikisi de 401 ve aynı mesaj
    ("Kullanıcı adı veya parola hatalı")
  - ayrı, rastgele bir kullanıcı adıyla 5 hatalı deneme 401, 6. deneme 429,
    `Retry-After: 60` (test operatörü kilitlenmesin diye ayrı ad)
  - pasif yapılan kullanıcı doğru parolayla 401
  - operatör PUT mod → 403 ve mod değişmedi; admin PUT mod → 200,
    `degistiren` = admin adı; operatörün açık WS bağlantısına gelen `mod` mesajı
    da `degistiren` taşıdı
  - `/api/kullanicilar` operatör 403, admin 200; admin kendini pasif yapamaz 409;
    7 karakterlik parolayla kullanıcı ekleme 422
  - son aktif admin kuralı (operatöre düşürme ve pasif yapma → `son_admin`) geçici
    bir veritabanında birim testle (canlı DB'de başka admin olabileceği için)
  - operatör PATCH cozuldu (gövdede sahte onaylayan) → `olay_adimlari.kim` =
    operatörün adı
  - süresi dolmuş token **canlı backend'e karşı**: `.env`'deki `JWT_GIZLI_ANAHTAR`
    ile süreç içinde imzalanan geçerli token 200 aldı (anahtarın backend'le aynı
    olduğu kanıtı), aynı kullanıcı için `exp` 60 sn önce olan token 401
  - WS token'sız ve bozuk token → kapanış kodu 4401; geçerli token → bağlantı açık
  - testteki 87 API yanıt gövdesinin hiçbirinde `"parola_hash"`, `"tuz"` ya da
    geçici parolalar yok
  - Temizlik: olaylar 31, olay_adimlari 3, sensor_gecmis 43 kayıt; 2 geçici
    kullanıcı ve 3 giriş kaydı silindi; mod ve "değiştiren" kaydı eski haline döndü.
- Not (15 Ekim 2026, 14:35): ilk T1-T12 çalıştırmasında T8 ve T10 başarısız oldu.
  Neden kod değil ortamdı: backend yeniden başlatılırken eski `--reload`
  sürecinin yetim worker'ı açık kalmış, iki backend aynı MQTT client_id
  ("kampus-backend") ile broker'da birbirini düşürüyordu; bellekteki histerezis
  ve korelasyon durumu iki süreç arasında bölündü. Yetim süreç kapatılınca T1-T12
  iki ardışık çalıştırmada da başarılı oldu.
- Göç (15 Ekim 2026, kimlik doğrulama): backend açılışta `kullanicilar` ve
  `giris_kayitlari` tablolarını oluşturdu; mevcut olaylar değişmedi.
- Göç (15 Ekim 2026, akıllı kurallar): backend yeniden yüklenince olaylar tablosuna `kural` ve
  `iliskili` kolonları eklendi (ALTER TABLE, mevcut kayıtlar NULL), `ayarlar` tablosu
  oluşturuldu; mevcut olaylar değişmedi.
- Göç (15 Ekim 2026, 12:50): ilk açılışta olaylar tablosuna 6 kolon eklendi; mevcut
  4 orta (hareket) kayıt `cozuldu` / `sistem (göç)`, 3 uyari kayıt `cozuldu` /
  `sistem` oldu. Göç öncesi yedek: backend/yedekler/kampus_20261015_1238_goconcesi.db.
- T13-T16 (23 Kasım 2026, gerçek donanım): bağlantı şeması ve bölücü hesapları
  firmware/README.md ve RAPOR_VERILERI.md §10'da. Ölçümler (sensor_gecmis, dugum1):
  - MQ-2 temiz hava, ısınma sonrası: 17:40-17:48 arası 156 ölçümde 285-352,
    ortalama 312. Gaz verilince 3 sn'lik turlarda 276 → 383 → 438 → 397 → 319 →
    2831 → 3367 (tepe) → 2779 → 1854 → 2807 → 1722 → 1292. Histerezis sayesinde
    tek yüksek (2831) ve tek bilgi (1292 < 1600) olayı oluştu, aradaki
    dalgalanma yeni alarm üretmedi.
  - Alev: alev yokken DO sürekli HIGH (alev=0); çakmakla kritik olay (17:48:56),
    17:49:27'de "Alev söndü" (bilgi).
  - PIR: mesai saatinde hareket = bilgi seviyesi, otomatik çözülmüş olay
    (kural=mesai). Test süresince sensör çoğu 3 sn'lik turda
    hareket bildirdi (dakikada ~15-20 olay). Çözüm (23.11.2026, 18:17): hareket olayı
    artık yalnızca 0 → 1 geçişinde ve düğüm başına 30 sn beklemeyle (T17); sonraki
    5,5 dk'da kart 65 kez hareket=1 yayınladı, 2 hareket olayı oluştu.
  - Bağlantı: test süresince broker'da 27 kez "Cihaz çevrimdışı" (LWT) olayı
    görüldü; kart her seferinde 1-2 sn içinde yeniden bağlanıp `online` yayınladı
    (broker kaydı: "session taken over" / "connection closed by client"; kart yayın
    zaman aşımında bağlantıyı kendisi yeniliyor). Kopma anındaki yayınlar
    "YAYINLANAMADI" ile düşebiliyor.
    Çözüm (23.11.2026, 18:14): neden firmware'deki 2 sn'lik MQTT komut zaman aşımıydı
    (256dpi/MQTT, PUBACK bu sürede gelmezse bağlantıyı kapatır). 8 sn'ye çıkarıldı
    (QoS 1 aynı, Wi-Fi modem uykusu zaten kapalı: `WiFi.setSleep(false)`).
    Yeni firmware 18:14:21'de bağlandı; 18:14-18:21 arası ~7 dk'da 0 yeniden
    bağlanma, 387 yayının hiçbiri başarısız değil (seri kayıt + broker kaydı).
    `WIFI_DUSUK_GUC` gerekmedi. Ayrıca backend'e 10 sn çevrimdışı toleransı
    eklendi (T18): kısa kopmalar artık "Cihaz çevrimdışı" olayı üretmez.
- T17 (23 Kasım 2026, 18:22): mod mesai_disi. test_dugum'a 0 → 1 → tek orta olay;
  ardından 5 kez hareket=1 (hareket sürüyor) → olay yok; 5 sn sonra 0 → 1 (bekleme
  içinde) → olay yok; bekleme dolunca 0 → 1 → yeni olay. `hareket_gecisi` saf
  fonksiyonu 10 adımlık diziyle (sürme, bekleme içinde/sonunda geçiş, bekleme dolduktan
  sonra süren 1 → olay yok) ve başka düğümün beklemeden etkilenmediğiyle doğrulandı.
  Bekleme canlı backend'de geçerli olduğundan hareket gönderen tüm testler
  (T1, T9, T11, T12, T17) önce 0 gönderir, gerekirse 30 sn bekler (script ~1 dk uzadı).
  T6 süreç içi hareket durumunu da temiz başlatır.
- T18 (23 Kasım 2026, 18:22): tolerans 10 sn. a) LWT'li client socket'i DISCONNECT
  göndermeden kapattı → broker LWT yayınladı (panel çevrimdışı) → ~1 sn sonra yeniden
  bağlanıp online → 12 sn boyunca çevrimdışı olayı yok, panel çevrimiçi. b) aynı kopma,
  geri bağlanmadan: 5 sn'de olay yok, 10,3 sn'de tek "uyari - Cihaz çevrimdışı".
  T7 (LWT'nin panele 0,0 sn'de yansıması) değişmedi.

---

## 8. Akıllı kurallar (15 Ekim 2026 eki)

Bu bölüm 12 Ekim derlemesinden sonra eklenen kural motorunu özetler; ayrıntılı
sözleşme `docs/SOZLESMELER.md` §4, §5 ve §6.2'de, test sonuçları
`docs/TEST_SONUCLARI.md`'de (T10, T11) yer alır. Kod: `backend/app/kurallar.py`.

### Neden gerekli
Eşik tabanlı tekil kurallar iki sorun doğurur:
- **Yanlış alarm:** MQ-2 duman/gaz sensörü yalnız başına sigara dumanı, buhar ya
  da sensör ısınması gibi nedenlerle eşiği aşabilir; alev sensörü de güneş ışığı
  yansımasıyla tetiklenebilir. Tek sensörün alarmı "olası" bir olaydır.
- **Önceliklendirme eksikliği:** aynı PIR hareketi mesai saatinde sıradan,
  gece ise izinsiz giriş belirtisidir. Bağlamı bilmeyen bir kural her hareketi
  aynı seviyede üretir; operatör ya alarm yorgunluğu yaşar ya da gerçek tehdidi
  kaçırır.

### 1) Korelasyon kuralı: yangın teyidi
- Aynı düğümde duman alarm durumuna geçişi ve alev algılaması, sıra fark
  etmeksizin 10 sn (`KORELASYON_PENCERE_SN`) içinde gelirse ayrı bir **kritik**
  bileşik olay üretilir: "Yangın teyitli: duman + alev (<konum>)".
- İki bağımsız fiziksel ilke (gaz/partikül ve kızılötesi alev) aynı anda tetiklendiği
  için olay **teyitli** kabul edilir; tekil olaylar kaybolmaz, teyit onlara eklenir
  ve hangi olaylardan doğduğunu (`iliskili`) taşır.
- Aynı yangın için tek teyit üretilir (iki sensör de normale dönene kadar kilit):
  histerezisle birlikte alarm fırtınasını önler.
- Panelde alarm bandı ve olay akışında "YANGIN TEYİTLİ" etiketi, detayda tetikleyen
  olaylara bağlantı; e-posta konusu "[KRİTİK] YANGIN TEYİTLİ — …".

### 2) Bağlama duyarlı kural: güvenlik modu
- Modlar: otomatik, mesai, mesai dışı, gece. Hareket seviyesi moda göre:
  mesai → bilgi (otomatik çözülür), mesai dışı → orta, gece → yüksek (e-posta).
- Otomatik modda karar **sunucu saatiyle** verilir (hafta içi 08:00–18:00 mesai,
  23:00–06:00 gece, kalanı mesai dışı); cihaz saati kayabileceği için kullanılmaz.
- Mod kalıcıdır (`ayarlar` tablosu), panelden değiştirilir ve WebSocket ile tüm
  açık sekmelere anında yayılır.
- Kural fonksiyonu saftır (`hareket_seviyesi(mod, simdi)`): saat parametreyle
  verildiğinden birim testle her an denenebilir.

### Açıklanabilirlik
Her olay onu üreten kuralın etiketini taşır (`olaylar.kural`: histerezis,
mesai, mesai_disi, gece_modu, korelasyon, baglanti). Panel bunu rozet olarak,
mesaj metni de uygulanan bağlamı ("Hareket algılandı · gece modu") gösterir;
operatör bir alarmın neden o seviyede olduğunu görebilir.

### Yeni arayüzler ve şema
| Tür | Ad | Açıklama |
|---|---|---|
| REST | `GET /api/ayarlar/mod` | `{mod, etkin_mod, aciklama}` |
| REST | `PUT /api/ayarlar/mod` | `{mod}`; geçersiz değer 422; değişince WS yayını |
| WS | `{"tip": "mod", "veri": {...}}` | mod değişti ya da otomatikte etkin mod saatle değişti |
| Kolon | `olaylar.kural` (TEXT) | olayı üreten kural |
| Kolon | `olaylar.iliskili` (TEXT, JSON liste) | bileşik olayın tetikleyen olay id'leri |
| Tablo | `ayarlar (anahtar TEXT PK, deger TEXT)` | kalıcı ayarlar (`guvenlik_modu`) |

Kolonlar ve tablo kayıpsız göçle eklenir (mevcut kayıtlar korunur, alanlar NULL).
MQTT konu/payload sözleşmesi ve histerezis eşikleri değişmedi.

### Doğrulama (15 Ekim 2026)
| Test | Sonuç |
|---|---|
| T10 Yangın teyidi | 12/12 kontrol: duman→alev ve alev→duman sırasında tek teyit, yangın sürerken tekrar yok, normalden sonra yeni teyit; 11 sn fark (pencere dışı) teyit üretmiyor |
| T11 Güvenlik modu | 10/10 kontrol: mesai bilgi, mesai dışı orta, gece yüksek; geçersiz mod 422; otomatik saat eşlemesi 9/9 (hafta içi 10:00, 20:00, 02:00, cumartesi 11:00 ve sınır saatleri) |
| T1–T9 regresyon | Hepsi başarılı (mod test süresince mesai dışı) |

---

## 9. Güvenlik: kimlik doğrulama ve yetkilendirme (15 Ekim 2026 eki)

Bu bölüm 12 Ekim derlemesinden sonra eklenen panel girişini özetler; ayrıntılı
sözleşme `docs/SOZLESMELER.md` §5, §7 ve §9'da, test sonuçları
`docs/TEST_SONUCLARI.md`'de (T12) yer alır. Kod: `backend/app/kimlik.py`,
`backend/app/veritabani.py` (kullanıcı fonksiyonları), `scripts/kullanici_ekle.py`.

> **Kısıt giderildi:** 12 Ekim sürümünde panel ve API kimlik doğrulaması olmadan
> erişilebiliyordu; alarmı çözen operatörün adı serbest metinle girildiği için
> denetlenemiyordu. Bu sürümde `/api/saglik` ve `/api/giris` dışındaki tüm uçlar ve
> WebSocket oturum ister; onaylayan kişi oturumdan gelir.

### Tasarım
| Konu | Karar |
|---|---|
| Parola saklama | `hashlib.scrypt` (n=2¹⁴, r=8, p=1, 32 bayt), kullanıcıya özel 16 baytlık rastgele tuz; sabit zamanlı karşılaştırma (`hmac.compare_digest`). Parola 8–128 karakter (üst sınır, pahalı özet hesabıyla hizmet engellemeyi önler). |
| Oturum | JWT HS256 (PyJWT): `sub`, `rol`, `ad`, `iat`, `exp`; süre `TOKEN_SURE_SAAT` (8 sa). Anahtar `JWT_GIZLI_ANAHTAR` (`.env`); yoksa açılışta rastgele üretilir (yeniden başlatınca oturumlar düşer). |
| Yetkilendirme (RBAC) | İki rol: **operatör** (tüm okuma uçları + alarm durumunu ilerletme) ve **admin** (ek olarak güvenlik modu ve kullanıcı yönetimi). Koruma FastAPI `Depends` ile tek yerde (router düzeyinde); rol her istekte veritabanından okunur, pasif yapılan kullanıcının eski token'ı hemen geçersizleşir. |
| Kaba kuvvet koruması | Aynı kullanıcı adı + IP için 5 hatalı denemeden sonra 60 sn kilit (HTTP 429, `Retry-After`). Hata mesajı geneldir ("Kullanıcı adı veya parola hatalı"); kullanıcı yokken de aynı süren scrypt hesabı yapılır (kullanıcı adı tahmini zorlaşır). |
| Denetim kaydı | `giris_kayitlari` (zaman, kullanıcı adı, IP, başarılı); alarm adımlarında `olay_adimlari.kim` ve modu değiştiren admin (`ayarlar.guvenlik_modu_degistiren`). |
| Taşıma | WebSocket `?token=` ile; geçersizse 4401 kapanış kodu. Token uvicorn loglarında maskelenir. CORS yalnızca panel adresleriyle sınırlı (`*` kaldırıldı). |
| İlk kurulum | `scripts/kullanici_ekle.py` (etkileşimli, `getpass`); koda gömülü kullanıcı/parola yok. Kullanıcı yoksa backend açılışta uyarır. |
| Veri sıfırlama | `scripts/db_sifirla.py` olay/ölçüm verisi ve giriş kayıtlarını siler, `kullanicilar` tablosunu korur. |

### Yetki matrisi
| İşlem | Token'sız | Operatör | Admin |
|---|---|---|---|
| Sağlık kontrolü, giriş | ✓ | ✓ | ✓ |
| Olay, düğüm, geçmiş, istatistik okuma; WebSocket | 401 / 4401 | ✓ | ✓ |
| Alarmı ilerletme (görüldü / müdahale / çözüldü) | 401 | ✓ | ✓ |
| Güvenlik modunu değiştirme | 401 | 403 | ✓ |
| Kullanıcı ekleme / rol / pasif / parola sıfırlama | 401 | 403 | ✓ |

### Panel
Giriş ekranı (kullanıcı adı, parola göster/gizle, "Beni hatırla"), üst barda kullanıcı
adı + rol rozeti + Çıkış; operatörde güvenlik modu seçici kilitli ("Mod yalnızca admin
tarafından değiştirilebilir"); mod kutusunda "değiştiren: <ad>, <saat>". Alarm onay
penceresinde operatör adı alanı kaldırıldı (otomatik). Admin için "Kullanıcılar" penceresi.
Herhangi bir 401 ya da WS 4401 oturumu kapatıp giriş ekranına döner.

### Yeni arayüzler ve şema
| Tür | Ad | Açıklama |
|---|---|---|
| REST | `POST /api/giris` | `{token, kullanici}`; 401 / 429 |
| REST | `GET /api/ben` | token sahibinin bilgisi |
| REST | `GET`, `POST /api/kullanicilar`; `PATCH /api/kullanicilar/{ad}` | admin; 409: kendini pasif yapma, son admini düşürme, alınmış ad |
| Değişiklik | `PATCH /api/olaylar/{id}/durum` | `onaylayan` artık token'dan; gövdedeki alan yok sayılır |
| Değişiklik | `PUT /api/ayarlar/mod` | yalnızca admin (403); yanıt ve WS `mod` mesajı `degistiren`, `degistirme_zaman` taşır |
| Tablo | `kullanicilar` | kullanici_adi (UNIQUE), ad_soyad, rol, parola_hash, tuz, aktif, olusturma, son_giris |
| Tablo | `giris_kayitlari` | zaman, kullanici_adi, ip, basarili |

Tablolar kayıpsız eklenir (`CREATE TABLE IF NOT EXISTS`); mevcut olay verisi değişmez.
MQTT sözleşmesi, kural motoru ve e-posta bildirimi değişmedi.

### Doğrulama (15 Ekim 2026)
| Test | Sonuç |
|---|---|
| T12 Kimlik doğrulama | 18/18 kontrol: token'sız 401, başka anahtarla imzalı token 401, yanlış parola ve olmayan kullanıcı aynı 401 mesajı, 6. hatalı deneme 429, pasif kullanıcı 401, operatör mod 403 / admin 200 (`degistiren` dolu), operatör kullanıcı listesi 403, admin kendini pasif yapamaz 409, kısa parola 422, son admin kuralı, operatörün çözdüğü alarmda `kim` = operatörün adı, canlı backend'e süresi dolmuş token 401, WS token'sız / bozuk 4401, `/api/saglik` token'sız 200, 87 yanıtın hiçbirinde parola özeti/tuz yok |
| T9 uyarlaması | onaylayan token'dan; gövdedeki sahte `onaylayan` yok sayıldı; geçersiz durum ve 301 karakter not yine 422 |
| T1–T11 regresyon | Hepsi başarılı (istekler geçici admin token'ıyla) |

---

## 10. Donanım ve firmware (27 Ekim 2026 eki, 23 Kasım 2026 güncellemesi)

Sahte üretecin yerini alan gerçek sensör düğümü. Ayrıntı ve kurulum: `firmware/README.md`.
Kod: `firmware/src/main.cpp`, pin/ayar: `firmware/include/pinler.h`.

| Bileşen | Seçim |
|---|---|
| Mikrodenetleyici | Wemos LOLIN S2 Mini (ESP32-S2, 240 MHz, 4 MB flash, 2 MB PSRAM, yerel USB CDC) |
| Hareket | HC-SR501 PIR, OUT → GPIO 7 doğrudan (aktif HIGH, iç pull-down; modül çıkışı 3,3 V), besleme VBUS 5 V |
| Duman/gaz | MQ-2, AO → 2×10 kΩ bölücü → GPIO 3 (en fazla 2,5 V; ADC1, 12 bit 0–4095, 11 dB, 10 örnek ortalaması), besleme VBUS 5 V |
| Alev | KY-026, DO → 10 kΩ + 20 kΩ bölücü → GPIO 5 (~3,3 V; alev görünce LOW), besleme VBUS 5 V |
| Durum göstergesi | dahili LED GPIO 15: bağlanırken 1 Hz, bağlıyken sabit, olayda hızlı yanıp söner |
| Geliştirme | PlatformIO Core 6.2.0, `espressif32@6.9.0` (Arduino-ESP32 2.0.17) |
| Kütüphaneler | `256dpi/MQTT@2.5.2` (QoS 1 yayın + LWT; PubSubClient QoS 1 yayınlayamaz), `bblanchon/ArduinoJson@7.2.1` |
| Derleme boyutu | RAM 52 192 / 327 680 bayt (%15,9), Flash 728 038 / 1 310 720 bayt (%55,5) — üç sensör açık |

Sözleşme uyumu (`scripts/sahte_veri.py` ile birebir): konular `kampus/guvenlik/<dugum>/{duman,hareket,alev,durum}`,
JSON alanları `dugum, sensor, deger, zaman`, QoS 1, retain yok, keepalive 60 sn, LWT `.../durum` ←
`{"durum":"offline","zaman":0}`, her bağlanışta `online`, 3 sn'lik turda duman → hareket → alev.
`zaman` NTP'den (Europe/Istanbul; `tr.pool.ntp.org`, `pool.ntp.org`); saat gelmeden 0 gönderilir
ve backend kendi saatini yazar. Backend ve panelde değişiklik gerekmedi.

Dayanıklılık: Wi-Fi koparsa 2 → 60 sn artan beklemeyle, MQTT koparsa 2 → 30 sn artan beklemeyle
yeniden bağlanır; döngü `millis()` tabanlı ve bloklamasızdır. PIR ve MQ-2 ilk 60 sn (ısınma)
yayınlanmaz. Hareket/alev 3 sn'lik tur içinde kilitlenir, kısa darbe kaçmaz.

### Bağlantı şeması (23.11.2026)

| Sensör | Besleme | Çıkış → kart |
|---|---|---|
| PIR (HC-SR501) | VBUS 5 V | OUT → GPIO 7 (doğrudan) |
| MQ-2 | VBUS 5 V | AO → 10 kΩ → GPIO 3; GPIO 3 → 10 kΩ → GND |
| Alev (KY-026) | VBUS 5 V | DO → 10 kΩ → GPIO 5; GPIO 5 → 20 kΩ → GND |

Neden 5 V ve gerilim bölücü: ilk kurulumda MQ-2 ve alev modülü 3V3 hattından
besleniyordu; 3V3 hattı bu sensörleri besleyemedi (MQ-2'nin ısıtıcısı 5 V için
tasarlanmış, ~150 mA çeker). Üç sensör de VBUS'a (USB 5 V) alındı. 5 V'la beslenen
modüllerin çıkışı 5 V'a çıkabildiği, ESP32-S2 pinleri ise en fazla 3,3 V kabul
ettiği için çıkışlar bölündü: MQ-2 AO 5 V × 1/2 = en fazla 2,5 V (11 dB ADC
aralığında), alev DO 5 V × 20/30 ≈ 3,3 V. PIR modülü kendi 3,3 V regülatörüyle
çıkış verdiği için doğrudan bağlı. Firmware'de değişiklik yalnızca derleme
ayarı: `MQ2_AKTIF 1`, `ALEV_AKTIF 1` (pinler 7/3/5 ve `ALEV_AKTIF_DUSUK` aynı).

### Ölçülen değerler (23.11.2026, sensor_gecmis)

| Sensör | Durum | Değer |
|---|---|---|
| MQ-2 | temiz hava, ısınma sonrası | ham 285–352, ortalama ~312 (156 ölçüm) |
| MQ-2 | bütan gazı | 2831 (eşik aşımı anı) – 3367 (tepe); 1800 eşiği aşıldı, 1600 altına inince normale döndü |
| Alev | alev yok / çakmak 20–30 cm | DO HIGH (0) / LOW (1) |
| PIR | önü kapalı / el sallama | 60 sn+ olay yok / "Hareket algılandı" |

### Gerçek donanım testleri (docs/TEST_SONUCLARI.md)

| Test | Senaryo | Sonuç | Durum |
|---|---|---|---|
| T13 | Güç/bağlantı: 5 V besleme + bölücüler, Wi-Fi + MQTT, 3 sn yayın | bağlandı, 3 sn'de bir duman → hareket → alev | BAŞARILI |
| T14 | PIR: önü kapalıyken olay yok, el sallayınca hareket | 17:44:49–17:46:18 olay yok; el sallayınca "Hareket algılandı" | BAŞARILI |
| T15 | Alev: çakmak 20–30 cm | kritik "ALEV ALGILANDI" (#2382, 23.11.2026 17:48) | BAŞARILI |
| T16 | Duman: temizde ~300, bütan gazı | 2831 → yüksek "Duman/gaz eşiği aşıldı" (#2425, 23.11.2026 17:51) | BAŞARILI |

### Bağlantı kararlılığı ve olay azaltma (23.11.2026)

İlk donanım testinde iki sorun görüldü ve aynı gün çözüldü:

| Sorun | Neden | Çözüm | Sonuç |
|---|---|---|---|
| 30 dk'da 27 MQTT yeniden bağlanma ("Cihaz çevrimdışı" olayı) | firmware MQTT komut zaman aşımı 2 sn; PUBACK gecikince kütüphane (256dpi/MQTT) bağlantıyı kapatıyor | `MQTT_ZAMAN_ASIMI_MS` 2000 → 8000 (QoS 1 aynı, `WiFi.setSleep(false)` zaten açık) | ~7 dk'da 0 yeniden bağlanma, 387/387 yayın başarılı; `WIFI_DUSUK_GUC` gerekmedi |
| Kısa kopmalar panelde uyarı olayı | her LWT "offline" anında olay | backend `CEVRIMDISI_TOLERANS_SN` = 10: bu sürede `online` gelirse olay yok | T18 BAŞARILI; gerçek kopma 10 sn sonra yine tek olay |
| PIR dakikada ~15-20 hareket olayı | her `hareket=1` yayını bir olaydı | olay yalnızca 0 → 1 geçişinde, düğüm başına `HAREKET_BEKLEME_SN` = 30 bekleme; seviye moda göre aynı | T17 BAŞARILI; kartta 5,5 dk'da 65 kez hareket=1 → 2 olay |

Durum (23.11.2026): üç sensör açık ve gerçek donanımla doğrulandı. Gerçek kart
`dugum1` iken sahte üreteç `--dugumler dugum2,dugum3` ile çalışır. İlk testte
kart 27 kez bağlantıyı yenileyip 1–2 sn'de geri bağlanıyordu (yayın
zaman aşımı) — aynı gün çözüldü, yukarıdaki tablo. Kablolama sorunları için `TESHIS_MODU`
(ağsız, GPIO 1–14 dijital + GPIO 1–10 analog, 500 ms).
