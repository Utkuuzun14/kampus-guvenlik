# Proje İlerleme Notu

Son güncelleme: Oturum 2 sonu

## Tamamlananlar
- [x] Mimari: ESP32-S2 → Mosquitto → FastAPI → React + e-posta bildirim
- [x] Ortak sözleşmeler (docs/SOZLESMELER.md): MQTT konuları, JSON şeması, kurallar, DB şeması, API sözleşmesi
- [x] Proje iskeleti + README
- [x] Mosquitto broker kuruldu ve test edildi (v2.1.2, auth aktif)
- [x] Backend TAMAMEN ÇALIŞIYOR:
      - config.py (ayarlar, .env)
      - veritabani.py (SQLite: olaylar + sensor_gecmis)
      - kurallar.py (eşik/alarm motoru, test edildi)
      - mqtt_dinleyici.py (broker abone + JSON çöz + kural + DB)
      - main.py (FastAPI: REST /api/olaylar, /api/durum, /api/saglik + WebSocket /ws)
- [x] Backend web'de doğrulandı (saglik, olaylar, docs 200 OK)
- [x] Sahte veri üreteci (scripts/sahte_veri.py) — kartsız uçtan uca test
- [x] UÇTAN UCA TEST BAŞARILI: üreteç → broker → backend → kural → DB zinciri canlı çalışıyor
- [x] Git repo + GitHub: https://github.com/Utkuuzun14/kampus-guvenlik

## Sıradaki adım
- [ ] React dashboard (frontend/):
      - Canlı olay akışı (WebSocket /ws)
      - Olay geçmişi tablosu (GET /api/olaylar)
      - Sensör/alarm durumu göstergesi
      - Alarm seviyelerine göre renk kodu

## Sonraki adımlar
- [ ] E-posta bildirim (SMTP) — kritik olayda mail
- [ ] ESP32-S2 firmware (firmware/) — kart Ankara'dan gelince
- [ ] Uçtan uca test + rapor Tablo 6 senaryolarını gerçek sonuçlarla doldurma
- [ ] TLS (opsiyonel, güvenlik iyileştirmesi)

## Her oturum başında sistemi başlatma
1. Broker (yönetici cmd):
   cd "C:\Program Files\mosquitto"
   mosquitto -c "C:\Program Files\mosquitto\mosquitto.conf" -v
2. Backend (yeni cmd):
   cd C:\Users\utkuu\Desktop\kampus-guvenlik\backend
   venv\Scripts\activate
   uvicorn app.main:app --host 127.0.0.1 --port 8000
3. Sahte üreteç (test için, yeni cmd):
   cd C:\Users\utkuu\Desktop\kampus-guvenlik\backend
   venv\Scripts\activate
   python ..\scripts\sahte_veri.py

## Notlar
- Mosquitto servisi (net start) STOPPED'a düşüyor; elle başlatma çalışıyor. Servis sorunu sonra çözülecek.
- Parola .env'de, git'e girmiyor. Broker parolası mosquitto_passwd ile ayrı.
- Kart gelince: sahte_veri.py kapatılır, firmware aynı konulara aynı JSON'u basar, gerisi değişmez.
