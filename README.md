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
- **Arayüz:** React (canlı dashboard)
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

## Sunum senaryosu
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
   → Lojmanlar düğümü DISCONNECT göndermeden düşer, broker LWT yayınlar: "Aktif düğüm
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
