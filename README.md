# IoT Tabanlı Kampüs Güvenlik Sistemi

Samsun Üniversitesi — Yazılım Mühendisliği Bitirme Projesi
Öğrenci: Utku Uzun

Kampüs ortamında hareket, duman/gaz ve alev olaylarını algılayıp merkezi olarak
izleyen, düşük maliyetli ve açık kaynaklı bir IoT güvenlik sistemi.

## Teknoloji yığını
- **Donanım:** ESP32-S2 (Wemos S2 Mini) + PIR, MQ-2, KY-026 sensörleri
- **Haberleşme:** MQTT (Mosquitto broker), JSON mesaj, QoS 1, LWT
- **Backend:** Python + FastAPI (MQTT abone, kural motoru, REST + WebSocket)
- **Veritabanı:** SQLite
- **Arayüz:** React (canlı dashboard), kullanıcı girişi ve rol tabanlı yetki (admin / operatör)
- **Bildirim:** E-posta (SMTP), kritik olaylarda

## Klasör yapısı
```
kampus-guvenlik/
├── README.md              → bu dosya
├── docs/
│   └── SOZLESMELER.md      → MQTT konuları, JSON şeması, kurallar, DB şeması (ÖNCE OKU)
├── backend/               → FastAPI + MQTT + SQLite
│   └── app/
├── frontend/              → React dashboard
├── firmware/              → ESP32-S2 kodu (PlatformIO)
├── scripts/               → yardımcı araçlar (sahte veri üreteci vb.)
└── ...
```

## Kurulum sırası (geliştirme planı)
1. Ortak sözleşmeler — `docs/SOZLESMELER.md`
2. Mosquitto broker kurulumu (Windows)
3. FastAPI backend
4. React dashboard
5. Sahte veri üreteci (donanım gelene kadar test)
6. ESP32-S2 firmware (donanım gelince)
7. E-posta bildirim + uçtan uca test

## İlk kurulum: `.env` ve ilk admin
1. `backend/.env.example` dosyasını `backend/.env` olarak kopyalayıp doldur. Kimlik
   doğrulama için:
   - `JWT_GIZLI_ANAHTAR` — uzun rastgele bir değer:
     `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
     Boş bırakılırsa backend her açılışta rastgele üretir ve yeniden başlayınca
     (`--reload` ile her kod değişikliğinde de) tüm oturumlar düşer.
   - `TOKEN_SURE_SAAT` — oturum süresi (varsayılan 8 saat)
   - `CORS_KAYNAKLAR` — panel başka bir adresten açılacaksa (varsayılan
     localhost/127.0.0.1, 5173 ve 5174)
   - `SENARYO_KULLANICI` / `SENARYO_PAROLA` — yalnızca `senaryo.py --mod` için,
     admin rolünde bir kullanıcı
2. İlk admini oluştur (backend venv aktifken, proje kökünden):
   `python scripts/kullanici_ekle.py` → kullanıcı adı, ad soyad, rol ve iki kez
   parola sorar (en az 8 karakter; parola ekranda görünmez). İlk kullanıcı
   varsayılan olarak admin olur. Kullanıcı yoksa backend açılışta
   "Henüz kullanıcı yok" uyarısı basar.
3. Diğer kullanıcılar panelden eklenir: admin olarak giriş → sol menüde
   **Kullanıcılar** (dişli simgesi) → ekle, rol değiştir, pasif yap, parola sıfırla.
   Operatör alarmları ilerletir; güvenlik modunu ve kullanıcıları yalnızca admin değiştirir.

## Sunum senaryosu
Ön koşul: `backend/.env` dolu (e-posta için `SMTP_KULLANICI` / `SMTP_PAROLA`).
Komutlar proje kökünden, backend venv aktifken çalıştırılır.

0. **Veritabanını sıfırla:** `python scripts/db_sifirla.py`
   → önce `backend/yedekler/kampus_YYYYMMDD_HHMM.db` yedeği alınır, kayıt sayıları
   gösterilir ve "EVET" onayı istenir (sorusuz: `--evet`). olaylar, olay_adimlari,
   sensor_gecmis ve giris_kayitlari boşaltılır, tablo yapısı korunur; kullanıcılar
   ve güvenlik modu **silinmez**. Backend açıkken de çalışır; ardından backend'i
   yeniden başlatmak bellekteki alarm durumunu da sıfırlar.
1. **Sistemi başlat:** `scripts\baslat.bat` → Broker, Backend, Sahte Veri (üç düğüm)
   ve React paneli ayrı pencerelerde açılır. Panel: http://localhost:5173 →
   giriş ekranı. İki sekme hazırla: birinde **admin**, diğerinde (gizli pencerede ya
   da başka tarayıcıda) **operatör** ile giriş yap. Üst barda ad + rol rozeti görünür.
2. **Sakin durum (~1 dk):** panelde "Aktif düğüm 3/3", haritada üç düğüm yeşil çizgiyle
   Mosquitto'ya bağlı. Üreteç varsayılan olarak sakindir: alev üretmez, duman eşiği
   düğüm başına ~10-15 dk'da bir kısa süre aşılır.
3. **Güvenlik modu + izinsiz giriş:** **admin** sekmesinde üst bardaki **Güvenlik modu**
   seçicisinden **Gece**'yi seç (kutu turuncu vurgulanır, altında "değiştiren: <ad>, <saat>").
   Operatör sekmesi de anında Gece olur; orada seçici kilitlidir (kilit simgesi, ipucu:
   "Mod yalnızca admin tarafından değiştirilebilir"). Sonra
   `python scripts/senaryo.py hareket dugum2`
   → Spor Kompleksi'nde ~25 sn art arda hareket. Gece kuralı gereği her hareket
   **yüksek** alarmdır: alarm bandı açılır, olaylarda "Gece kuralı" rozeti ve
   "Hareket algılandı · gece modu" mesajı, e-posta gider. Aynı senaryoyu modu
   **Mesai**'ye alıp tekrarla: hareketler bilgi seviyesinde, otomatik çözülmüş
   düşer (karşılaştırma için). Seçiciye dokunmadan da çalıştırılabilir:
   `python scripts/senaryo.py hareket dugum2 --mod gece` (sonunda eski moda döner;
   `backend/.env`'de `SENARYO_KULLANICI` / `SENARYO_PAROLA` admin hesabı gerekir).
   Sunumdan sonra modu **Otomatik**'e geri al (saat 23:00–06:00 gece, hafta içi
   08:00–18:00 mesai, kalanı mesai dışı; "şu an: …" etiketi o anki modu gösterir).
4. **Yangın:** haritada dugum1'e tıkla (gösterge "MQ-2 · dugum1"), sonra
   `python scripts/senaryo.py yangin dugum1`
   → duman 30 sn'de kademeli yükselip eşiği (1800) aşar, 3 sn sonra alev = kritik.
   Duman ve alev 10 sn içinde geldiği için korelasyon kuralı **YANGIN TEYİTLİ**
   bileşik olayını üretir: alarm bandında "● YANGIN TEYİTLİ", tehdit seviyesi
   KRİTİK, kırmızı harita halesi ve konusu "[KRİTİK] YANGIN TEYİTLİ" olan e-posta.
   Bandın başlığına tıkla: detayda "İlişkili olaylar" altında duman ve alev
   olayları var; tıklayınca o olayın detayı açılır.
   Histerezis sayesinde olay akışında yalnızca 5 olay görünür: duman eşiği aşıldı
   (yüksek), alev (kritik), yangın teyitli (kritik, "Korelasyon" rozeti), duman
   normale döndü ve alev söndü (bilgi).
   60 sn sonra duman düşer, alev "Yok" olur.
   **Alarmı panelden çözme (operatör):** **operatör** sekmesinde alarm bandında
   "Görüldü"ye bas, isteğe bağlı notu yazıp onayla (operatör adı sorulmaz, oturumdan
   gelir): rozet "Görüldü" olur, tehdit seviyesi İZLENİYOR'a döner. Ardından
   "Müdahale" ve "Çöz" (ya da doğrudan "Çöz"): teyit bandı kaybolur, sıradaki açık
   kritik (alev) ve ardından yüksek alarm (duman) banda gelir; onları da çöz. "Açık alarm" kartı ve ortalama
   görülme/çözüm süresi güncellenir, ikinci sekme de sayfa yenilemeden aynı anda
   değişir. Olay başlığına tıklayınca zaman çizelgesi (oluştu → görüldü → müdahale
   → çözüldü, her adımda saat + giriş yapan operatörün adı + not) açılır.
5. **Bağlantı kopması (LWT):** `python scripts/senaryo.py kopma dugum3`
   → Yurt Binası düğümü DISCONNECT göndermeden düşer, broker LWT yayınlar: "Aktif düğüm
   2/3", dugum3 çizgisi sönük gri. 30 sn sonra geri gelir ve 3/3 olur.
6. **Testler (isteğe bağlı):** üreteci kapatıp `python scripts/test_senaryolari.py`
   (T1-T12, sonuçlar `docs/TEST_SONUCLARI.md`). Script kendi geçici admin ve
   operatörünü oluşturup sonda siler; test süresince modu mesai_disi yapar ve sonunda
   senin seçtiğin moda geri alır. `scripts/olcum.py` de aynı şekilde geçici bir
   operatör kullanır.

Notlar:
- Senaryo süresince üreteç ilgili düğümün ölçümlerini duraklatır, değerler karışmaz.
  Yangın ve hareket senaryoları üreteç kapalıyken de çalışır; kopma senaryosu için
  üretecin o düğümü çalıştırıyor olması gerekir.
- Bekleme kuralı gereği aynı düğüm/sensör/seviye için 5 dk'da en fazla bir e-posta
  gider. Yangın senaryosunu 5 dk içinde tekrarlarsan ikinci mail gelmez.
- Sahte üreteç her düğümde arada bir rastgele hareket gönderir. Mod **Gece** iken
  (ya da Otomatik modda 23:00–06:00 arası) bunlar da yüksek alarm üretir ve düğüm
  başına 5 dk'da bir e-posta gidebilir; bu gerçekçi davranıştır. Sunum gündüz
  yapılıyorsa modu senaryo bitince Otomatik'e almak yeterli.
- Üreteç ayrıca dugum3'ü kendiliğinden 3-5 dk'da bir düşürür; sunum sırasında bu da
  olabilir. Yalnızca seçili düğümler için: `python scripts/sahte_veri.py --dugumler dugum1,dugum2`.
