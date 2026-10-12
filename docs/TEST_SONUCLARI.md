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
| T5 | Web arayüzü / API | - | API yanıt veriyor, backend broker'a bağlı | /api/saglik OK, mqtt=bagli | BAŞARILI |
| T6 | Bildirim (e-posta) | alev=1, hareket=1, duman=2500, tekrar alev=1 | kritik/yüksekte mail, ortada yok, bekleme süresinde tekrar yok | 7/7 kontrol geçti (SMTP taklit) | BAŞARILI |
| T7 | LWT ile çevrimdışı ve geri gelme | online → socket kapatma (DISCONNECT yok) → yeniden bağlanma | /api/dugumler'de çevrimdışı, sonra çevrimiçi | LWT 0,2 sn'de yansıdı, geri bağlanınca anında çevrimiçi | BAŞARILI |

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
- T7 (12 Ekim 2026, 14:01): sahte üretecin dugum3 kopma fonksiyonu kullanıldı
  (scripts/sahte_veri.py: istemci_olustur + baglantiyi_kopar). test_dugum için
  LWT'li client bağlandı → socket DISCONNECT gönderilmeden kapatıldı → broker
  LWT'yi yayınladı → /api/dugumler 0,2 sn içinde cevrimici=false,
  son_durum=offline gösterdi → yeni client "online" yayınlayınca tekrar
  cevrimici=true. Rastgele 3-5 dk'lık kopmayı beklememek için kopma hemen tetiklendi.
- 14:01 çalıştırmasında yalnızca T5-T7 koşuldu (sahte üreteç açıktı; T5-T7
  üreteçten etkilenmez). T1-T4 sonuçları 13:40 tam çalıştırmasına aittir.
- Bildirim açıkken yapılan T1-T3 canlı testlerinde test_dugum için mail
  gönderilmedi (test_dugum bildirimden hariç; backend logunda [BILDIRIM] satırı yok).
- Gerçek SMTP gönderimi scripts/eposta_test.py ile doğrulandı (12 Ekim 2026):
  Gmail SMTP SSL (465) üzerinden örnek kritik mail başarıyla gönderildi.
