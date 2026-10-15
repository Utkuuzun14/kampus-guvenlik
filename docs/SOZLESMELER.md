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
| Hareket | PIR | `deger == 1` | moda göre: bilgi / orta / yuksek (aşağıda) | Olay kaydı + panelde göster (yuksek: e-posta) |
| Duman/gaz | MQ-2 | normal → `deger > ESIK_DUMAN` (1800) geçişi | yuksek | Olay kaydı + alarm konusu + e-posta |
| Duman normale döndü | MQ-2 | alarmda → `deger < ESIK_DUMAN_NORMAL` (1600) geçişi | bilgi | Olay kaydı |
| Alev | KY-026 | `0 → 1` geçişi | kritik | Olay kaydı + alarm konusu + e-posta (öncelikli) |
| Alev söndü | KY-026 | `1 → 0` geçişi | bilgi | Olay kaydı |
| Cihaz çevrimdışı | ESP32 | `durum == "offline"` (LWT veya temiz kapanış) | uyari | Olay kaydı + panelde "çevrimdışı" işareti |
| Yangın teyidi | korelasyon | aynı düğümde duman alarmı + alev, `KORELASYON_PENCERE_SN` içinde | kritik | Ayrı bileşik olay + alarm konusu + e-posta ("YANGIN TEYİTLİ") |

Alarm seviyeleri: `bilgi < uyari < orta < yuksek < kritik`

### Kural tablosu (akıllı kurallar)
Her olay, onu üreten kuralın etiketini `olaylar.kural` kolonunda taşır; panel
bunu rozet olarak gösterir. Kod: `backend/app/kurallar.py`.

| Sensör | Koşul | Güvenlik modu (etkin) | Seviye | `kural` |
|--------|-------|----------------------|--------|---------|
| hareket | `deger == 1` | mesai | bilgi (otomatik çözülür) | `mesai` |
| hareket | `deger == 1` | mesai_disi | orta | `mesai_disi` |
| hareket | `deger == 1` | gece | yuksek | `gece_modu` |
| duman | normal → `> 1800` / alarmda → `< 1600` | — | yuksek / bilgi | `histerezis` |
| alev | `0 → 1` / `1 → 0` | — | kritik / bilgi | `histerezis` |
| durum | `offline` | — | uyari | `baglanti` |
| yangin_teyit | duman alarmı + alev, pencere içinde | — | kritik | `korelasyon` |

Eski kayıtlarda `kural` boştur (NULL); panel rozet göstermez.
Hareket mesajı uygulanan kuralı da yazar: `Hareket algılandı · gece modu`,
`· mesai dışı`, `· mesai saati`; otomatik modda sonuna ` (otomatik)` eklenir.

### Güvenlik modu
- Değerler (ASCII): `otomatik` | `mesai` | `mesai_disi` | `gece`. Varsayılan `otomatik`.
- Mod kalıcıdır: `ayarlar` tablosunda `guvenlik_modu` anahtarı (§5). Backend
  yeniden başlasa da korunur; değiştirmek için `PUT /api/ayarlar/mod` (§6.2) ya
  da paneldeki "Güvenlik modu" seçicisi.
- `otomatik`te etkin mod **sunucu saatine** (Europe/Istanbul) göre seçilir:
  1. `GECE_BASLANGIC`–`GECE_BITIS` (varsayılan 23:00–06:00, her gün) → `gece`
  2. hafta içi `MESAI_BASLANGIC`–`MESAI_BITIS` (varsayılan 08:00–18:00) → `mesai`
  3. geri kalanı ve hafta sonu gündüzü → `mesai_disi`

  Başlangıç saati dahil, bitiş hariç. Gece ve mesai çakışırsa gece kazanır.
  Saatler `.env`'den okunur (`HH:MM`).
- **Neden sunucu saati:** olayın `zaman` alanı cihaz saatidir ve kayabilir
  (NTP yoksa saatler/dakikalar); bir ESP32'nin saati yüzünden gece alarmı mesai
  sayılmasın diye mod kararı daima sunucu saatiyle verilir.
- Windows'ta IANA saat dilimi veritabanı (`tzdata`) yoksa sabit UTC+03:00
  kullanılır; Türkiye 2016'dan beri yaz saati uygulamadığı için sonuç aynıdır.
- Kural fonksiyonu saftır: `hareket_seviyesi(mod, simdi)` saat parametreyle
  verildiği için testte herhangi bir an denenebilir (T11).

### Yangın teyidi (korelasyon)
- **Tanım:** aynı düğümde duman **alarm durumuna geçişi** (histerezisle
  `> 1800`) ve **alev=1 olayı** (`0 → 1`), sıra fark etmeksizin
  `KORELASYON_PENCERE_SN` (varsayılan 10 sn, `.env`) içinde gerçekleşirse
  ayrı bir bileşik olay üretilir:
  `sensor="yangin_teyit"`, `seviye="kritik"`, `kural="korelasyon"`,
  `mesaj="Yangın teyitli: duman + alev (<düğüm konumu>)"`,
  `deger` = tetikleyen duman değeri, `iliskili=[ilk_olay_id, ikinci_olay_id]`.
- Orijinal duman ve alev olayları aynen kalır; teyit onlara ek bir olaydır.
- **Tekrar yok:** teyitten sonra düğüm kilitlenir. Duman normale (`< 1600`)
  dönüp alev 0 olana kadar (ikisi de normal) yeni teyit üretilmez; yangın
  sürerken alevin söndüp yeniden yanması da teyit üretmez.
- Pencere, mesajların **sunucuya varış zamanıyla** ölçülür (cihaz saati değil).
- Korelasyon durumu histerezis gibi backend belleğinde tutulur; backend yeniden
  başlarsa sıfırlanır.
- Teyit olayı normal akışa girer: durum `yeni` (operatör akışı), WS `olay`
  mesajı, `.../alarm` konusu ve kritik e-posta. Bildirim bekleme anahtarı
  `(düğüm, "yangin_teyit", "kritik")` olduğundan alev mailiyle çakışmaz.

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
| `durum` | TEXT | `yeni` / `goruldu` / `mudahale` / `cozuldu` (varsayılan `yeni`, §6.1) |
| `onaylayan` | TEXT NULL | son durum adımını yapan operatör (`sistem` = otomatik) |
| `goruldu_zaman` | REAL NULL | sunucu saati (epoch, ondalıklı) |
| `mudahale_zaman` | REAL NULL | sunucu saati |
| `cozuldu_zaman` | REAL NULL | sunucu saati |
| `not_metni` | TEXT NULL | son adımın notu |
| `kural` | TEXT NULL | olayı üreten kural (§4 kural tablosu): `histerezis`, `mesai`, `mesai_disi`, `gece_modu`, `korelasyon`, `baglanti` |
| `iliskili` | TEXT NULL | bileşik olayı tetikleyen olay id'leri, JSON liste (ör. `"[412, 413]"`); API'de dizi olarak döner |

`sensor` alanı bileşik olayda `yangin_teyit` olur (§4).

Durum, `kural` ve `iliskili` kolonları kayıpsız göçle eklenir: backend açılışta `PRAGMA table_info`
ile eksik kolonları bulur ve yalnızca onları `ALTER TABLE ADD COLUMN` ile ekler
(tablo silinmez, idempotent). Kolonlar ilk kez eklendiğinde mevcut kayıtlar bir
kez kapatılır: `bilgi`/`uyari` → `cozuldu` (`onaylayan='sistem'`), `orta+` →
`cozuldu` (`onaylayan='sistem (göç)'`, `olay_adimlari`'na tek bir `cozuldu` adımı).

### Tablo: `olay_adimlari`
Her durum geçişi bir satır; zaman çizelgesindeki kim + not + saat buradan gelir.
`olaylar`'daki `onaylayan` / `not_metni` yalnızca son adımı tutar.

| Sütun | Tip | Açıklama |
|-------|-----|----------|
| `id` | INTEGER PK | otomatik artan |
| `olay_id` | INTEGER | `olaylar.id` |
| `durum` | TEXT | geçilen durum (`goruldu` / `mudahale` / `cozuldu`) |
| `kim` | TEXT | adımı yapan kullanıcı: token sahibinin `ad_soyad`'ı, yoksa `kullanici_adi` (§9) |
| `not_metni` | TEXT NULL | adım notu |
| `zaman` | REAL | sunucu saati |

Ara adım atlanırsa (ör. `yeni → cozuldu`) yalnızca hedef adım için satır yazılır;
atlanan adımın `*_zaman` alanı aynı anla dolar, panel onu "atlandı" gösterir.

### Tablo: `ayarlar`
Kalıcı sistem ayarları (anahtar–değer). Tablo yoksa açılışta oluşturulur;
mevcut veriye dokunulmaz. `scripts/db_sifirla.py` bu tabloyu boşaltmaz.

| Sütun | Tip | Açıklama |
|-------|-----|----------|
| `anahtar` | TEXT PK | ör. `guvenlik_modu` |
| `deger` | TEXT | ör. `otomatik` |

Kullanılan anahtarlar: `guvenlik_modu`, `guvenlik_modu_degistiren` (modu en son
değiştiren adminin görünen adı), `guvenlik_modu_zaman` (epoch, sunucu saati).

### Tablo: `kullanicilar`
Panel kullanıcıları (§9). Tablo yoksa açılışta oluşturulur; `scripts/db_sifirla.py`
bu tabloyu **silmez**.

| Sütun | Tip | Açıklama |
|-------|-----|----------|
| `id` | INTEGER PK | otomatik artan |
| `kullanici_adi` | TEXT UNIQUE | küçük harf, `^[a-z0-9._-]{3,32}$` |
| `ad_soyad` | TEXT NULL | zaman çizelgesinde ve "değiştiren" alanında görünen ad (≤ 60) |
| `rol` | TEXT | `admin` \| `operator` (CHECK) |
| `parola_hash` | TEXT | scrypt özeti (hex); **API'de asla dönmez** |
| `tuz` | TEXT | kullanıcıya özel 16 baytlık rastgele tuz (hex); **API'de asla dönmez** |
| `aktif` | INTEGER | 1/0; pasif kullanıcı giriş yapamaz, eski token'ı da geçersizdir |
| `olusturma` | REAL | sunucu saati |
| `son_giris` | REAL NULL | son başarılı giriş |

### Tablo: `giris_kayitlari`
Giriş denetim kaydı: başarılı ve başarısız her deneme (kilitliyken gelenler dahil).
`scripts/db_sifirla.py` bu tabloyu boşaltır.

| Sütun | Tip | Açıklama |
|-------|-----|----------|
| `id` | INTEGER PK | otomatik artan |
| `zaman` | REAL | sunucu saati |
| `kullanici_adi` | TEXT | denemede yazılan ad (küçük harfe çevrilmiş, ≤ 64) |
| `ip` | TEXT | istemci IP'si |
| `basarili` | INTEGER | 1/0 |

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
`/api/saglik` ve `/api/giris` dışındaki **tüm** uçlar `Authorization: Bearer <token>`
ister; yoksa/bozuksa/süresi dolmuşsa 401, rol yetmiyorsa 403 (§9).

- `POST /api/giris`, `GET /api/ben`, `/api/kullanicilar` → kimlik ve kullanıcı yönetimi (§9)
- `GET /api/olaylar?limit=50` → son olaylar (JSON dizi). `&durum=acik` yalnızca
  çözülmemişleri (`durum != cozuldu`) döndürür; başka değer 422.
- `GET /api/olaylar/{id}` → tek olay + `adimlar` dizisi (eski → yeni); yoksa 404
- `PATCH /api/olaylar/{id}/durum` → durum ilerletme (§6.1)
- `GET /api/istatistik/mudahale` → müdahale istatistiği (§6.1)
- `GET /api/ayarlar/mod`, `PUT /api/ayarlar/mod` → güvenlik modu (§6.2)
- `GET /api/durum` → dugum1 durumu ve duman eşiği (`esik_duman`); eski uç, geriye uyumluluk için
- `GET /api/dugumler` → bilinen tüm düğümler (aşağıda)
- `GET /api/gecmis?sensor=duman&dugum=dugum1&limit=50` → bir sensörün son ham okumaları (eski → yeni)
- `GET /api/saglik` (token istemez) → `{"durum": "calisiyor", "mqtt": "bagli" | "kopuk"}`.
  `mqtt`, backend'in broker bağlantısıdır; paneldeki "Broker" ışığı buna bakar.
  Tek bir düğümün kopması bu değeri etkilemez.

### `GET /api/dugumler`
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

### WebSocket
- `WS /ws?token=<token>` → backend, yeni bir olay/alarm oluştuğunda bu kanaldan React'e
  anında JSON gönderir. React canlı güncellenir. Token yoksa/geçersizse bağlantı
  kabul edilip hemen **4401** koduyla kapatılır (panel giriş ekranına döner, yeniden
  bağlanmayı denemez). Token yalnızca bağlanırken denetlenir. Uvicorn loglarında
  `token=` değeri `***` ile maskelenir.

WebSocket mesaj formatı:
```json
{ "tip": "olay", "veri": { ...olay nesnesi... } }
```
Olay nesnesine durum alanları (`durum`, `onaylayan`, `*_zaman`, `not_metni`)
ve kural alanları (`kural`, `iliskili`) **eklendi**; `tip` ve mevcut alanlar
aynı kaldı, eski istemciler etkilenmez.

Durum değiştiğinde (§6.1) tüm bağlı istemcilere:
```json
{ "tip": "olay_guncelleme", "veri": { ...güncel olay nesnesi, "adimlar": [...] } }
```
Panel, listelerdeki olayı `id` ile bulup yerinde günceller (sayfa yenilemeden,
açık tüm sekmelerde).

Güvenlik modu değiştiğinde (`PUT /api/ayarlar/mod`) ya da otomatik modda etkin
mod saatle değiştiğinde (backend 30 sn'de bir kontrol eder, ör. 23:00'te gece
başlar) tüm bağlı istemcilere:
```json
{ "tip": "mod", "veri": { "mod": "otomatik", "etkin_mod": "gece", "aciklama": "...",
                         "degistiren": "Ayşe K.", "degistirme_zaman": 1792063534.57 } }
```

### 6.1 Olay yaşam döngüsü (alarm onaylama)

Yalnızca `orta`, `yuksek`, `kritik` olaylar operatör akışına girer ve `yeni`
olarak oluşur. `bilgi` ve `uyari` olaylar oluşurken `cozuldu` yazılır
(`onaylayan='sistem'`), listeyi kirletmez.

```
  ┌──────┐     ┌─────────┐     ┌──────────┐     ┌─────────┐
  │ yeni │────▶│ goruldu │────▶│ mudahale │────▶│ cozuldu │
  └──────┘     └─────────┘     └──────────┘     └─────────┘
     │  │           │                 ▲            ▲   ▲
     │  │           └─────────────────┼────────────┘   │   goruldu → cozuldu
     │  └─────────────────────────────┘                │   yeni → mudahale
     └─────────────────────────────────────────────────┘   yeni → cozuldu

  Yalnızca ileri; ara adım atlanabilir. Geri ya da aynı duruma geçiş → 409.
```

**`PATCH /api/olaylar/{id}/durum`** (operatör ve admin, §9)
```json
{ "durum": "goruldu", "not": "Kamera 3 kontrol ediliyor" }
```
- `durum`: `goruldu` | `mudahale` | `cozuldu` (zorunlu)
- `not`: en fazla 300 karakter (isteğe bağlı)
- `onaylayan`: **token'dan gelir** (`ad_soyad`, yoksa `kullanici_adi`); hem
  `olaylar.onaylayan`'a hem `olay_adimlari.kim`'e yazılır. Eski istemciler için
  gövdede `onaylayan` alanı hâlâ kabul edilir ama **yok sayılır** (doğrulanmaz).

| Kod | Ne zaman | Gövde |
|-----|----------|-------|
| 200 | geçiş yapıldı | güncel olay + `adimlar` |
| 404 | olay yok | `{"detail": "Olay bulunamadı"}` |
| 409 | hedef mevcut durumdan ileri değil | `{"detail": "...", "mevcut": "cozuldu"}` |
| 401 | token yok/geçersiz | `{"detail": "..."}` |
| 422 | geçersiz `durum`, uzun `not` | FastAPI doğrulama hatası |

Geçişte hedef duruma kadar boş kalan tüm `*_zaman` alanları **aynı sunucu
anıyla** doldurulur (ör. `yeni → cozuldu`: üçü de aynı an). `onaylayan` ve
`not_metni` son adımı tutar; adımın kendisi `olay_adimlari`'na yazılır.
UPDATE mevcut duruma koşulludur: iki sekme aynı anda basarsa biri 409 alır.
Başarılı geçişten sonra `olay_guncelleme` WS mesajı yayınlanır.

**`GET /api/istatistik/mudahale`**
```json
{ "acik_sayisi": 3, "ort_gorulme_sn": 42.5, "ort_cozum_sn": 380.1, "cozulen_sayisi": 7 }
```
- `acik_sayisi`: zamandan bağımsız **tüm** çözülmemiş `orta+` olaylar
- `ort_gorulme_sn` / `ort_cozum_sn`: son 24 saatte oluşan `orta+` olaylarda
  `goruldu_zaman − zaman` / `cozuldu_zaman − zaman` ortalaması; veri yoksa `null`
- `cozulen_sayisi`: son 24 saatte oluşup çözülen `orta+` olay sayısı
- Göçte kapatılan kayıtlar (`onaylayan='sistem (göç)'`) ortalamaya katılmaz.

> **Saat kayması notu:** olayın `zaman`'ı cihazın (ESP32) saatidir, `*_zaman`
> alanları sunucu saatidir. Cihaz saati kayarsa süreler sapar. Cihaz saati
> ileri giderse süre negatif çıkar; **negatif süreli kayıt ortalamaya katılmaz**
> (sayılarda yer alır). Sahte üreteç ve test scripti sunucu saatini kullandığı
> için bu durum yalnızca gerçek donanımda görülebilir; firmware'de NTP ile saat
> eşitlemesi önerilir.

### 6.2 Güvenlik modu uçları

**`GET /api/ayarlar/mod`**
```json
{ "mod": "otomatik", "etkin_mod": "gece",
  "aciklama": "Otomatik · şu an gece (23:00–06:00) · hareket = yuksek",
  "degistiren": "Ayşe K.", "degistirme_zaman": 1792063534.57 }
```
- `mod`: kayıtlı mod; `etkin_mod`: o an geçerli olan (otomatikte saate göre,
  diğerlerinde `mod` ile aynı); `aciklama`: panel ipucu için kısa metin.
- `degistiren` / `degistirme_zaman`: modu en son değiştiren adminin görünen adı ve
  sunucu saati; mod hiç değiştirilmediyse `null`.

**`PUT /api/ayarlar/mod`** (yalnızca admin)
```json
{ "mod": "gece" }
```
| Kod | Ne zaman | Gövde |
|-----|----------|-------|
| 200 | kaydedildi | GET ile aynı biçim |
| 401 | token yok/geçersiz | `{"detail": "..."}` |
| 403 | kullanıcı admin değil (mod değişmez) | `{"detail": "Bu işlem için admin yetkisi gerekli"}` |
| 422 | `mod` eksik ya da `otomatik/mesai/mesai_disi/gece` dışında | FastAPI doğrulama hatası |

Değer değiştiyse `degistiren`/`degistirme_zaman` güncellenir ve WS `{"tip": "mod"}`
yayınlanır; aynı değer tekrar gönderilirse ikisi de olmaz.

---

## 7. Güvenlik kararları

- MQTT broker'da **kullanıcı adı + parola** zorunlu (anonim erişim kapalı).
- Geliştirme sonrası **TLS** (şifreli MQTT) eklenecek — rapor 2.6 ile uyumlu.
- QoS 1: kritik mesajların en az bir kez ulaşması garanti.
- LWT: kart ani kopunca broker otomatik "offline" yayınlar.
- **Panel girişi (§9):** parolalar `hashlib.scrypt` (n=2¹⁴, r=8, p=1) ve
  kullanıcıya özel 16 baytlık tuzla saklanır; karşılaştırma `hmac.compare_digest`
  ile sabit zamanlıdır. Parola hiçbir yerde loglanmaz, hiçbir yanıtta dönmez.
- **Oturum:** JWT (HS256, PyJWT), anahtar `JWT_GIZLI_ANAHTAR` (`backend/.env`).
  Rol her istekte veritabanından okunur (RBAC: admin / operatör); token'daki rol
  yalnızca bilgi amaçlıdır.
- **Kaba kuvvet koruması:** aynı kullanıcı adı + IP için 5 hatalı denemeden sonra
  60 sn kilit (429); kullanıcı yokken de aynı süren scrypt hesabı yapılır.
  Her deneme `giris_kayitlari`'na yazılır (denetim kaydı).
- **CORS:** yalnızca paneli sunan adresler (`CORS_KAYNAKLAR`; varsayılan
  `localhost`/`127.0.0.1` :5173 ve :5174), `*` kullanılmaz.

---

## 8. Bildirim kuralları (e-posta)

Kod: `backend/app/bildirim.py`, ayarlar: `backend/.env` (şablon: `backend/.env.example`).

- **Hangi olaylar:** seviyesi `BILDIRIM_SEVIYELER` içinde olanlar (varsayılan
  `kritik,yuksek`: alev, yangın teyidi, duman eşik aşımı ve gece modunda hareket).
  Olay DB'ye yazıldıktan sonra tetiklenir.
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
  `[KRİTİK] Alev algılandı — dugum1 (Ana Bina · A Kanadı)`; yangın teyidinde
  `[KRİTİK] YANGIN TEYİTLİ — dugum1 (Ana Bina · A Kanadı)`. Olayda `kural` varsa
  mailde "Kural" satırı, bileşik olayda "İlişkili" satırı (`#412, #413`) yer alır.
  Düğüm konumları `config.DUGUM_KONUMLARI`'ndan gelir (frontend `sabitler.js` ile aynı tutulur).
- **Gizlilik:** parola ve adresler yalnızca `backend/.env`'de durur (git'e girmez).
  Gmail için normal parola değil, 16 haneli **uygulama şifresi** kullanılır.
- **Elle doğrulama:** `python scripts/eposta_test.py` örnek bir kritik mail gönderir.

---

## 9. Kimlik doğrulama ve yetkilendirme

Kod: `backend/app/kimlik.py` (token + FastAPI bağımlılıkları), kullanıcı tabloları §5.
İlk admin: `python scripts/kullanici_ekle.py` (etkileşimli; koda gömülü kullanıcı/parola yok).
Kullanıcı yoksa backend açılışta `Henüz kullanıcı yok: python scripts/kullanici_ekle.py` uyarısı basar.

### Roller ve yetki matrisi

| Uç / işlem | Token'sız | Operatör | Admin |
|---|---|---|---|
| `GET /api/saglik`, `POST /api/giris` | ✓ | ✓ | ✓ |
| `GET /api/ben` | 401 | ✓ | ✓ |
| Tüm okuma uçları (`/api/olaylar*`, `/api/dugumler`, `/api/gecmis`, `/api/durum`, `/api/istatistik/mudahale`, `GET /api/ayarlar/mod`) | 401 | ✓ | ✓ |
| `PATCH /api/olaylar/{id}/durum` (alarm ilerletme) | 401 | ✓ | ✓ |
| `WS /ws?token=` | 4401 | ✓ | ✓ |
| `PUT /api/ayarlar/mod` (güvenlik modu) | 401 | **403** | ✓ |
| `GET/POST /api/kullanicilar`, `PATCH /api/kullanicilar/{ad}` | 401 | **403** | ✓ |

### Token akışı

```
 Panel                         Backend                              SQLite
   │  POST /api/giris            │                                    │
   │  {kullanici_adi, parola} ──▶│ kilit? (ad+IP, 5 hata → 60 sn) ─429│
   │                             │ scrypt(parola, tuz) == parola_hash?│◀── kullanicilar
   │                             │ giris_kayitlari'na yaz ───────────▶│
   │◀── {token, kullanici} ──────│ JWT HS256 {sub, rol, ad, iat, exp} │
   │                             │                                    │
   │  GET /api/... + Bearer ────▶│ imza + exp doğrula → kullanıcıyı   │
   │                             │ DB'den oku (aktif? rol?) ─────────▶│
   │◀── 200 / 401 / 403 ─────────│                                    │
   │  WS /ws?token=... ─────────▶│ aynı doğrulama; geçersizse 4401    │
```

- **İçerik:** `sub` (kullanici_adi), `rol`, `ad` (görünen ad), `iat`, `exp`.
  Süre `TOKEN_SURE_SAAT` (varsayılan 8 saat).
- **Anahtar:** `JWT_GIZLI_ANAHTAR` (`backend/.env`). Yoksa açılışta rastgele üretilir
  ve uyarı basılır: backend her yeniden başladığında (`--reload` dahil) tüm oturumlar düşer.
- **Rol kaynağı:** her istekte veritabanı. Pasif yapılan ya da rolü değişen
  kullanıcının mevcut token'ı bir sonraki istekte buna göre değerlendirilir.
- **Panel:** token `sessionStorage`'da, "Beni hatırla" işaretliyse `localStorage`'da
  (`kg_oturum`). Herhangi bir 401 ya da WS 4401 oturumu temizler ve giriş ekranına döner.

### Uçlar

**`POST /api/giris`**
```json
{ "kullanici_adi": "ayse", "parola": "••••••••" }
```
```json
{ "token": "eyJhbGciOi...", "kullanici": { "kullanici_adi": "ayse", "ad_soyad": "Ayşe K.", "rol": "operator" } }
```
Kullanıcı adı büyük/küçük harf ve baştaki/sondaki boşluklardan bağımsızdır.

**`GET /api/ben`** → `{ "kullanici_adi", "ad_soyad", "rol" }` (rol veritabanından).

**`GET /api/kullanicilar`** (admin) → `[{ id, kullanici_adi, ad_soyad, rol, aktif, olusturma, son_giris }]`
— `parola_hash` ve `tuz` hiçbir yanıtta yer almaz.

**`POST /api/kullanicilar`** (admin) → 201 + kullanıcı
```json
{ "kullanici_adi": "mehmet", "ad_soyad": "Mehmet Y.", "rol": "operator", "parola": "en-az-8-karakter" }
```

**`PATCH /api/kullanicilar/{ad}`** (admin) — verilen alanlar güncellenir:
```json
{ "rol": "admin", "ad_soyad": "Mehmet Y.", "aktif": false, "yeni_parola": "..." }
```

### Hata kodları

| Kod | Ne zaman | Gövde |
|-----|----------|-------|
| 401 | Token yok / bozuk / imzası yanlış / süresi dolmuş / kullanıcı pasif. `POST /api/giris`'te: kullanıcı yok, parola yanlış ya da kullanıcı pasif — **hangisi olduğu söylenmez** | `{"detail": "Kullanıcı adı veya parola hatalı"}` (girişte), `WWW-Authenticate: Bearer` |
| 403 | Geçerli token ama rol yetmiyor (operatör → mod / kullanıcı yönetimi) | `{"detail": "Bu işlem için admin yetkisi gerekli"}` |
| 404 | `PATCH /api/kullanicilar/{ad}`: kullanıcı yok | `{"detail": "Kullanıcı bulunamadı"}` |
| 409 | Kullanıcı adı alınmış; admin kendini pasif yapmaya çalışıyor; son aktif admin pasif yapılmak ya da operatöre düşürülmek isteniyor | `{"detail": "..."}` |
| 422 | Kullanıcı adı `^[a-z0-9._-]{3,32}$`'e uymuyor, parola 8–128 karakter değil, geçersiz rol | `{"detail": "..."}` |
| 429 | Aynı kullanıcı adı + IP'den 5 hatalı denemeden sonra 60 sn (kilit sürerken parola doğru olsa da) | `{"detail": "Çok fazla hatalı deneme. N sn sonra tekrar deneyin.", "kalan_sn": N}`, `Retry-After: N` |
| WS 4401 | `/ws` token'sız ya da geçersiz token'la açıldı | kapanış nedeni `Oturum geçersiz` |

Kaba kuvvet sayacı bellektedir (backend yeniden başlayınca sıfırlanır); başarılı giriş
sayacı sıfırlar. Kilit, kullanıcı adı + IP çiftine özeldir: aynı IP'den başka bir
kullanıcı adıyla giriş etkilenmez.
