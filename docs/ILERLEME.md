# Proje İlerleme Notu

Son güncelleme: Oturum 3 sonu

## Tamamlananlar
- [x] Mimari: ESP32-S2 → Mosquitto → FastAPI → React + e-posta bildirim
- [x] Ortak sözleşmeler (docs/SOZLESMELER.md): MQTT konuları, JSON şeması, kurallar, DB şeması, API sözleşmesi
- [x] Proje iskeleti + README
- [x] Mosquitto broker kuruldu ve test edildi (v2.1.2, auth aktif)
- [x] Backend TAMAMEN ÇALIŞIYOR:
      - config.py (ayarlar, .env)
      - veritabani.py (SQLite: olaylar + sensor_gecmis, + sensor_gecmis_getir)
      - kurallar.py (eşik/alarm motoru)
      - mqtt_dinleyici.py (broker abone + JSON çöz + kural + DB)
      - main.py (FastAPI: /api/olaylar, /api/durum, /api/saglik, /api/gecmis + WebSocket /ws)
- [x] Sahte veri üreteci (scripts/sahte_veri.py) — kartsız uçtan uca test
- [x] Uçtan uca test başarılı: üreteç → broker → backend → kural → DB → API → panel
- [x] React DASHBOARD ÇALIŞIYOR (frontend/):
      - Olay tablosu (renkli seviye rozetleri)
      - Özet kartları (toplam / kritik / yüksek / son olay)
      - Gerçek zamanlı WebSocket (olaylar anında düşüyor) + CANLI göstergesi
      - Canlı duman/gaz grafiği (recharts, eşik çizgili) — /api/gecmis
- [x] Git repo + GitHub (5 commit): https://github.com/Utkuuzun14/kampus-guvenlik

## Sıradaki adımlar (kartsız yapılabilir)
- [ ] Test senaryoları (rapor Tablo 6, T1-T6) — çalışan sistemle test + ekran görüntüsü
- [ ] Rapor güncelleme — "planlanmıştır" -> "gerçekleştirilmiştir", ekran görüntüleri
- [ ] E-posta bildirim (SMTP) — kritik olayda mail (Gmail uygulama parolası gerekli)
- [ ] (Opsiyonel) Panele düğüm durum göstergesi + olay filtreleme
- [ ] (Opsiyonel) Tek tıkla başlatma .bat script'i

## Kart gelince (Ankara'dan sonra)
- [ ] ESP32-S2 firmware (firmware/) — PlatformIO, sensörsüz Wi-Fi/MQTT testi, sonra sensörler
- [ ] sahte_veri.py kapatılır; firmware aynı konulara aynı JSON'u basar, gerisi değişmez
- [ ] Gerçek sensör testleri + rapor Tablo 6 gerçek sonuçlar

## Sistemi başlatma (her oturum başında)
1. Broker (yönetici cmd):
   cd "C:\Program Files\mosquitto"
   mosquitto -c "C:\Program Files\mosquitto\mosquitto.conf" -v
2. Backend (yeni cmd):
   cd C:\Users\utkuu\Desktop\kampus-guvenlik\backend
   venv\Scripts\activate
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
3. Sahte üreteç (test için, yeni cmd):
   cd C:\Users\utkuu\Desktop\kampus-guvenlik\backend
   venv\Scripts\activate
   python ..\scripts\sahte_veri.py
4. React panel (yeni cmd):
   cd C:\Users\utkuu\Desktop\kampus-guvenlik\frontend
   npm run dev
   -> tarayıcı: http://localhost:5173 (veya 5174)

## Notlar
- Mosquitto servisi (net start) STOPPED'a düşüyor; elle başlatma çalışıyor. Servis sorunu sonra çözülecek.
- Parolalar .env'de, git'e girmiyor. node_modules/venv/*.db de ignore.
- Backend --reload ile başlatılırsa kod değişince otomatik yenilenir.
