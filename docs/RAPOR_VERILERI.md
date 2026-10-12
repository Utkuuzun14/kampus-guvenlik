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
| starlette | 1.7.0 | FastAPI altyapısı |
| uvicorn | 0.54.0 | ASGI sunucusu |
| watchfiles | 1.3.0 | geliştirmede otomatik yeniden yükleme (--reload) |
| websockets | 17.1 | WebSocket (uvicorn) ve ölçüm istemcisi |

Standart kütüphane: `sqlite3` (veritabanı), `smtplib` + `ssl` + `email` (e-posta), `threading`.
`requirements.txt` toplam 19 sabitlenmiş paket içerir (dolaylı bağımlılıklar dahil).

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
| Hareket | PIR | `deger == 1` | orta | Olay kaydı + panelde göster |
| Duman/gaz | MQ-2 | normal → `deger > ESIK_DUMAN` (1800) geçişi | yuksek | Olay kaydı + alarm konusu + e-posta |
| Duman normale döndü | MQ-2 | alarmda → `deger < ESIK_DUMAN_NORMAL` (1600) geçişi | bilgi | Olay kaydı |
| Alev | KY-026 | `0 → 1` geçişi | kritik | Olay kaydı + alarm konusu + e-posta (öncelikli) |
| Alev söndü | KY-026 | `1 → 0` geçişi | bilgi | Olay kaydı |
| Cihaz çevrimdışı | ESP32 | `durum == "offline"` (LWT veya temiz kapanış) | uyari | Olay kaydı + panelde "çevrimdışı" işareti |

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
  üretimini etkiler. Hareket olayları histerezissiz (her `deger == 1` bir olay).
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
  `durum=offline` mesajından doğar.
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
Yöntem: scripts/test_senaryolari.py — her senaryo broker'a kontrollü mesaj
gönderir, backend API'sinden sonuç doğrulanır.
Ortam: Mosquitto broker + FastAPI backend + SQLite (sahte üreteç kapalı,
e-posta bildirimi açık). Veritabanı 15:38'de scripts/db_sifirla.py ile sıfırlandı
(yedek: backend/yedekler/kampus_20261012_1538.db); olay id'leri bu yüzden küçüktür.

| Test | Senaryo | Gönderilen | Beklenen | Sonuç | Durum |
|------|---------|-----------|----------|-------|-------|
| T1 | Hareket algılama (PIR) | hareket=1 | orta seviye olay | orta - "Hareket algılandı" | BAŞARILI |
| T2 | Duman/gaz eşik aşımı (MQ-2) | normal → duman=2500 | yüksek seviye uyarı | yuksek - eşik aşıldı | BAŞARILI |
| T2b | Duman normal (MQ-2) | duman=400 | alarm oluşmamalı | yeni olay yok | BAŞARILI |
| T3 | Alev algılama (KY-026) | alev 0 → 1 | kritik olay | kritik - "ALEV ALGILANDI" | BAŞARILI |
| T4 | MQTT mesaj iletimi | - | mesaj broker→backend | T1-T3 kanıtlıyor | BAŞARILI |
| T5 | Web arayüzü / API | - | API yanıt veriyor, backend broker'a bağlı | /api/saglik OK, mqtt=bagli | BAŞARILI |
| T6 | Bildirim (e-posta) | alev=1, hareket=1, duman=2500, alev 0→1 (iki kez) | kritik/yüksekte mail, orta/bilgide yok, bekleme süresinde tekrar yok | 8/8 kontrol geçti (SMTP taklit) | BAŞARILI |
| T7 | LWT ile çevrimdışı ve geri gelme | online → socket kapatma (DISCONNECT yok) → yeniden bağlanma | /api/dugumler'de çevrimdışı, sonra çevrimiçi | LWT 0,1 sn'de yansıdı, geri bağlanınca anında çevrimiçi | BAŞARILI |
| T8 | Histerezis (alarm fırtınası önleme) | duman 2100, 2500, 2900, 2300, 1900 → 1700 → 1500; alev 1, 1 → 0 | tek yüksek olay, ölü bantta olay yok, 1600 altında tek bilgi; alev sürerken olay yok, sönünce tek bilgi | 5/5 adım beklenen olay sayısıyla | BAŞARILI |

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
