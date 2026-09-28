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
