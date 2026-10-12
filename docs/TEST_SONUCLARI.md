# Test Sonuçları (Rapor Tablo 6)

Test tarihi: 12 Ekim 2026, 13:40 (otomatik test scripti ile; ilk çalıştırma 4 Ekim 2026)
Yöntem: scripts/test_senaryolari.py — her senaryo broker'a kontrollü mesaj 
gönderir, backend API'sinden sonuç doğrulanır.
Ortam: Mosquitto broker + FastAPI backend + SQLite (sahte üreteç kapalı,
e-posta bildirimi açık).

| Test | Senaryo | Gönderilen | Beklenen | Sonuç | Durum |
|------|---------|-----------|----------|-------|-------|
| T1 | Hareket algılama (PIR) | hareket=1 | orta seviye olay | orta - "Hareket algılandı" | BAŞARILI |
| T2 | Duman/gaz eşik aşımı (MQ-2) | duman=2500 | yüksek seviye uyarı | yuksek - eşik aşıldı | BAŞARILI |
| T2b | Duman normal (MQ-2) | duman=400 | alarm oluşmamalı | yeni olay yok | BAŞARILI |
| T3 | Alev algılama (KY-026) | alev=1 | kritik olay | kritik - "ALEV ALGILANDI" | BAŞARILI |
| T4 | MQTT mesaj iletimi | - | mesaj broker→backend | T1-T3 kanıtlıyor | BAŞARILI |
| T5 | Web arayüzü / API | - | API yanıt veriyor | /api/saglik OK | BAŞARILI |
| T6 | Bildirim (e-posta) | alev=1, hareket=1, duman=2500, tekrar alev=1 | kritik/yüksekte mail, ortada yok, bekleme süresinde tekrar yok | 7/7 kontrol geçti (SMTP taklit) | BAŞARILI |

## Notlar
- Testler test_dugum düğümü ile yapıldı (gerçek veri kirlenmedi).
- Her olayın id'si artarak oluştu (gerçekten yeni olay üretildiği doğrulandı).
- T2b: normal değerde yeni olay oluşmadığı doğrulandı (yanlış alarm üretilmiyor).
- T6: gerçek mail gönderilmedi; SMTP gönderim fonksiyonu taklit
  edildi (mock), MQTT mesaj işleyicisi süreç içinde sahte DB ile çağrıldı.
  Doğrulananlar:
  - kritik (alev) olayında mail gönderiliyor, konu "[KRİTİK] Alev algılandı — ..."
  - SMTP 500 ms sürse de MQTT işleyicisi beklemiyor (~1 ms, gönderim ayrı thread'de)
  - orta (hareket) olayında mail gönderilmiyor
  - yüksek (duman eşik aşımı) olayında mail gönderiliyor
  - BILDIRIM_BEKLEME_SN (300 sn) içinde aynı düğüm/sensör/seviye için ikinci mail engelleniyor
  - süre dolunca yeni mail gidiyor ve bastırılan olay "+1 benzer olay" olarak yazılıyor
- T6 broker/backend gerektirmez.
- Bildirim açıkken yapılan T1-T3 canlı testlerinde test_dugum için mail
  gönderilmedi (test_dugum bildirimden hariç; backend logunda [BILDIRIM] satırı yok).
- Gerçek SMTP gönderimi scripts/eposta_test.py ile doğrulandı (12 Ekim 2026):
  Gmail SMTP SSL (465) üzerinden örnek kritik mail başarıyla gönderildi.
