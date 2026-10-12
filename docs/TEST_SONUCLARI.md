# Test Sonuçları (Rapor Tablo 6)

Test tarihi: 12 Ekim 2026, 14:31 (otomatik test scripti ile, T1-T8 tek çalıştırma)
Yöntem: scripts/test_senaryolari.py — her senaryo broker'a kontrollü mesaj
gönderir, backend API'sinden sonuç doğrulanır.
Ortam: Mosquitto broker + FastAPI backend + SQLite (sahte üreteç kapalı,
e-posta bildirimi açık).

| Test | Senaryo | Gönderilen | Beklenen | Sonuç | Durum |
|------|---------|-----------|----------|-------|-------|
| T1 | Hareket algılama (PIR) | hareket=1 | orta seviye olay | orta - "Hareket algılandı" | BAŞARILI |
| T2 | Duman/gaz eşik aşımı (MQ-2) | normal → duman=2500 | yüksek seviye uyarı | yuksek - eşik aşıldı | BAŞARILI |
| T2b | Duman normal (MQ-2) | duman=400 | alarm oluşmamalı | yeni olay yok | BAŞARILI |
| T3 | Alev algılama (KY-026) | alev 0 → 1 | kritik olay | kritik - "ALEV ALGILANDI" | BAŞARILI |
| T4 | MQTT mesaj iletimi | - | mesaj broker→backend | T1-T3 kanıtlıyor | BAŞARILI |
| T5 | Web arayüzü / API | - | API yanıt veriyor, backend broker'a bağlı | /api/saglik OK, mqtt=bagli | BAŞARILI |
| T6 | Bildirim (e-posta) | alev=1, hareket=1, duman=2500, alev 0→1 (iki kez) | kritik/yüksekte mail, orta/bilgide yok, bekleme süresinde tekrar yok | 8/8 kontrol geçti (SMTP taklit) | BAŞARILI |
| T7 | LWT ile çevrimdışı ve geri gelme | online → socket kapatma (DISCONNECT yok) → yeniden bağlanma | /api/dugumler'de çevrimdışı, sonra çevrimiçi | LWT ilk yoklamada (<0,2 sn) yansıdı, geri bağlanınca anında çevrimiçi | BAŞARILI |
| T8 | Histerezis (alarm fırtınası önleme) | duman 2100, 2500, 2900, 2300, 1900 → 1700 → 1500; alev 1, 1 → 0 | tek yüksek olay, ölü bantta olay yok, 1600 altında tek bilgi; alev sürerken olay yok, sönünce tek bilgi | 5/5 adım beklenen olay sayısıyla | BAŞARILI |

## Notlar
- Testler test_dugum düğümü ile yapıldı; çalışma sonunda bu düğümün kayıtları
  silindi (olaylar: 8, sensor_gecmis: 20). Gerçek veri kirlenmedi.
- Olay id'leri artarak oluştu (#1441 → #1443): gerçekten yeni olay üretildiği doğrulandı.
- Histerezis durumu backend belleğinde tutulduğu için script başta test_dugum'u
  normale çeker (duman=400, alev=0). Aynı backend açıkken ikinci kez çalıştırıldığında
  da T1-T8 başarılı oldu.
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
  /api/dugumler 0,2 sn içinde cevrimici=false, son_durum=offline gösterdi →
  yeni client "online" yayınlayınca tekrar cevrimici=true. Rastgele 3-5 dk'lık
  kopmayı beklememek için kopma hemen tetiklendi.
- T8 ek doğrulama: `python scripts/senaryo.py yangin test_dugum` (90 sn, 80 ölçüm)
  tam 4 olay üretti: yüksek (duman 1875), kritik (alev), bilgi (duman normale
  döndü, 1500), bilgi (alev söndü). Histerezisten önce aynı senaryo 1 kritik +
  24 yüksek olay üretiyordu. Ölçümlerin hepsi sensor_gecmis'e yazıldı.
- Gerçek SMTP gönderimi scripts/eposta_test.py ile ayrıca doğrulandı (12 Ekim 2026,
  Gmail SMTP SSL 465).
