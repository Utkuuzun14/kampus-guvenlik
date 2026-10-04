# Test Sonuçları (Rapor Tablo 6)

Test tarihi: (otomatik test scripti ile)
Yöntem: scripts/test_senaryolari.py — her senaryo broker'a kontrollü mesaj 
gönderir, backend API'sinden sonuç doğrulanır.
Ortam: Mosquitto broker + FastAPI backend + SQLite (sahte üreteç kapalı).

| Test | Senaryo | Gönderilen | Beklenen | Sonuç | Durum |
|------|---------|-----------|----------|-------|-------|
| T1 | Hareket algılama (PIR) | hareket=1 | orta seviye olay | orta - "Hareket algılandı" | BAŞARILI |
| T2 | Duman/gaz eşik aşımı (MQ-2) | duman=2500 | yüksek seviye uyarı | yuksek - eşik aşıldı | BAŞARILI |
| T2b | Duman normal (MQ-2) | duman=400 | alarm oluşmamalı | yeni olay yok | BAŞARILI |
| T3 | Alev algılama (KY-026) | alev=1 | kritik olay | kritik - "ALEV ALGILANDI" | BAŞARILI |
| T4 | MQTT mesaj iletimi | - | mesaj broker→backend | T1-T3 kanıtlıyor | BAŞARILI |
| T5 | Web arayüzü / API | - | API yanıt veriyor | /api/saglik OK | BAŞARILI |
| T6 | Bildirim (e-posta) | - | kritik olayda mail | e-posta modülü eklenince | BEKLEMEDE |

## Notlar
- Testler test_dugum düğümü ile yapıldı (gerçek veri kirlenmedi).
- Her olayın id'si artarak oluştu (gerçekten yeni olay üretildiği doğrulandı).
- T2b: normal değerde yeni olay oluşmadığı doğrulandı (yanlış alarm üretilmiyor).
- T6: e-posta (SMTP) entegrasyonu tamamlandığında çalıştırılacak.
