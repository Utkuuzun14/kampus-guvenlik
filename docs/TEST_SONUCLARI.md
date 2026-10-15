# Test Sonuçları (Rapor Tablo 6)

Test tarihi: 12 Ekim 2026, 15:39 (otomatik test scripti ile, T1-T8 tek çalıştırma)
Son çalıştırma: 15 Ekim 2026, 14:49 (T1-T12 tek çalıştırma, hepsi başarılı; 14:37 ve
14:49'da aynı backend açıkken art arda iki kez)
Yöntem: scripts/test_senaryolari.py — her senaryo broker'a kontrollü mesaj
gönderir, backend API'sinden (T9'da ayrıca PATCH ve WebSocket, T11'de mod uçları
ve WebSocket, T12'de giriş/yetki uçları) sonuç doğrulanır. Script başta güvenlik
modunu mesai_disi yapar (hareket = orta) ve sonunda kullanıcının önceki moduna (ve
"değiştiren" kaydına) geri alır. API korumalı olduğundan başta rastgele adlı ve
parolalı geçici bir admin ve operatör oluşturulur; istekler admin token'ıyla, durum
geçişleri operatör token'ıyla yapılır; sonda bu kullanıcılar ve giriş kayıtları silinir.
Ortam: Mosquitto broker + FastAPI backend + SQLite (sahte üreteç kapalı,
e-posta bildirimi açık). Veritabanı 15:38'de scripts/db_sifirla.py ile sıfırlandı
(yedek: backend/yedekler/kampus_20261012_1538.db); olay id'leri bu yüzden küçüktür.

| Test | Senaryo | Gönderilen | Beklenen | Sonuç | Durum |
|------|---------|-----------|----------|-------|-------|
| T1 | Hareket algılama (PIR) | hareket=1 (mod: mesai_disi) | orta seviye olay | orta - "Hareket algılandı · mesai dışı" | BAŞARILI |
| T2 | Duman/gaz eşik aşımı (MQ-2) | normal → duman=2500 | yüksek seviye uyarı | yuksek - eşik aşıldı | BAŞARILI |
| T2b | Duman normal (MQ-2) | duman=400 | alarm oluşmamalı | yeni olay yok | BAŞARILI |
| T3 | Alev algılama (KY-026) | alev 0 → 1 | kritik olay | kritik - "ALEV ALGILANDI" (T2'den 1,5 sn sonra geldiği için ek olarak yangin_teyit oluştu) | BAŞARILI |
| T4 | MQTT mesaj iletimi | - | mesaj broker→backend | T1-T3 kanıtlıyor | BAŞARILI |
| T5 | Web arayüzü / API | - | API yanıt veriyor, backend broker'a bağlı | /api/saglik OK, mqtt=bagli | BAŞARILI |
| T6 | Bildirim (e-posta) | alev=1, hareket=1, duman=2500, alev 0→1 (iki kez) | kritik/yüksekte mail, orta/bilgide yok, bekleme süresinde tekrar yok | 8/8 kontrol geçti (SMTP taklit) | BAŞARILI |
| T7 | LWT ile çevrimdışı ve geri gelme | online → socket kapatma (DISCONNECT yok) → yeniden bağlanma | /api/dugumler'de çevrimdışı, sonra çevrimiçi | LWT 0,1 sn'de yansıdı, geri bağlanınca anında çevrimiçi | BAŞARILI |
| T8 | Histerezis (alarm fırtınası önleme) | duman 2100, 2500, 2900, 2300, 1900 → 1700 → 1500; alev 1, 1 → 0 | tek yüksek olay, ölü bantta olay yok, 1600 altında tek bilgi; alev sürerken olay yok, sönünce tek bilgi | 5/5 adım beklenen olay sayısıyla | BAŞARILI |
| T9 | Olay yaşam döngüsü (alarm onaylama) — 15 Ekim 2026, kimlik doğrulamayla uyarlandı | hareket=1 → operatör token'ıyla PATCH goruldu (gövdede sahte onaylayan) → PATCH cozuldu → geri/aynı geçiş, hatalı gövdeler | durum=yeni; ileri geçişler 200; atlanan adım zamanı dolu; kim/onaylayan = token sahibi, gövdedeki onaylayan yok sayılır; geri 409; olmayan id 404; geçersiz durum ve 301 karakter not 422; WS olay_guncelleme; istatistik değer döner | 13/13 kontrol geçti | BAŞARILI |
| T10 | Yangın teyidi (korelasyon) — 15 Ekim 2026 | duman 2500 → 2 sn → alev=1; yangın sürerken duman 2900, alev 1→0→1; normale dönüş → yeniden yangın; ters sıra (alev → 2 sn → duman); kural fonksiyonu birim testi | tek yangin_teyit (kritik), iliskili = [duman, alev]; sürerken yeni teyit yok; normalden sonra yeni teyit; ters sırada teyit; pencere dışında (11 sn) teyit yok; mail konusu "YANGIN TEYİTLİ" | 12/12 kontrol geçti | BAŞARILI |
| T11 | Güvenlik modu ve zamana bağlı hareket kuralı — 15 Ekim 2026 | PUT mesai / mesai_disi / gece + her birinde hareket=1; PUT "tatil" ve boş gövde; hareket_seviyesi("otomatik", t) birim testi | mesai → bilgi (otomatik çözülmüş), mesai_disi → orta, gece → yuksek; WS "mod" mesajı; geçersiz → 422; hafta içi 10:00 bilgi, 20:00 orta, 02:00 yüksek, cumartesi 11:00 orta | 10/10 kontrol geçti (saat eşlemesi 9/9 vaka) | BAŞARILI |
| T12 | Kimlik doğrulama ve yetkilendirme — 15 Ekim 2026 | token'sız / sahte imzalı / süresi dolmuş istek; yanlış parola, olmayan kullanıcı, pasif kullanıcı; 6 hatalı giriş; operatör ve admin ile PUT mod, /api/kullanicilar; admin kendini pasif yapma; operatör PATCH durum; WS token'sız / bozuk / geçerli | 401 (genel mesaj); 429 + Retry-After; operatör 403, admin 200 + degistiren; 409; kim = operatörün adı; WS 4401; /api/saglik 200; hiçbir yanıtta parola özeti yok | 18/18 kontrol geçti | BAŞARILI |

## Notlar
- Testler test_dugum düğümü ile yapıldı; çalışma sonunda bu düğümün kayıtları
  silindi (olaylar: 8, sensor_gecmis: 20). Gerçek veri kirlenmedi.
- Olay id'leri artarak oluştu (#6 → #8): gerçekten yeni olay üretildiği doğrulandı.
- Histerezis durumu backend belleğinde tutulduğu için script başta test_dugum'u
  normale çeker (duman=400, alev=0). Aynı backend açıkken art arda iki kez
  çalıştırıldığında da T1-T8 başarılı oldu (14:31 ve 14:33 çalıştırmaları).
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
  /api/dugumler 0,1 sn içinde cevrimici=false, son_durum=offline gösterdi →
  yeni client "online" yayınlayınca tekrar cevrimici=true. Rastgele 3-5 dk'lık
  kopmayı beklememek için kopma hemen tetiklendi.
- T8 ek doğrulama: `python scripts/senaryo.py yangin test_dugum` (90 sn, 80 ölçüm)
  tam 4 olay üretti: yüksek (duman 1875), kritik (alev), bilgi (duman normale
  döndü, 1500), bilgi (alev söndü). Histerezisten önce aynı senaryo 1 kritik +
  24 yüksek olay üretiyordu. Ölçümlerin hepsi sensor_gecmis'e yazıldı.
- Gerçek SMTP gönderimi scripts/eposta_test.py ile ayrıca doğrulandı (12 Ekim 2026,
  Gmail SMTP SSL 465).
- T9 (15 Ekim 2026, 12:51): test_dugum'a hareket=1 gönderildi, #394 orta olay
  `durum=yeni`, `onaylayan=null` geldi. Doğrulananlar:
  - PATCH goruldu (operatör + not) → 200, `goruldu_zaman` dolu, `mudahale_zaman` boş
  - açık bir WebSocket istemcisine `{"tip": "olay_guncelleme"}` mesajı geldi (durum=goruldu)
  - PATCH cozuldu → 200; atlanan `mudahale_zaman` = `cozuldu_zaman`
  - olay_adimlari: [goruldu (T9 Operatör, "Kamera kontrol ediliyor"), cozuldu (T9 Operatör)]
  - cozuldu → goruldu: 409 (`mevcut=cozuldu`); cozuldu → cozuldu: 409
  - olmayan id: 404; durum=xyz, durum=yeni, boş onaylayan, 41 karakter onaylayan,
    301 karakter not: hepsi 422
  - `?durum=acik` listesinde çözülen olay ve çözülmüş kayıt yok
  - T8'in ürettiği 3 bilgi olayı oluşurken `cozuldu` / `onaylayan=sistem`
  - /api/istatistik/mudahale → `{acik_sayisi: 4, ort_gorulme_sn: 2.1, ort_cozum_sn: 2.1,
    cozulen_sayisi: 1}` (açık 4: T1, T2, T3 ve T8'in çözülmemiş alarmları)
  - Temizlik: olaylar 9, olay_adimlari 2, sensor_gecmis 21 kayıt silindi.
- T10 (15 Ekim 2026, 13:55): korelasyon penceresi 10 sn (varsayılan).
  - duman 2500 (#500, yuksek) → 2 sn → alev=1 (#501, kritik) → #502 yangin_teyit,
    kritik, `kural=korelasyon`, `durum=yeni`, `iliskili=[500, 501]`;
    `GET /api/olaylar/502` iliskili alanını liste olarak döndürdü. Orijinal duman ve
    alev olayları `kural=histerezis` ile korundu.
  - Yangın sürerken (duman alarmda) duman 2900, alev 1 → 0 → 1: yalnızca alev bilgi +
    alev kritik oluştu, yeni teyit yok (düğüm kilitli).
  - normale dönüş (duman 400, alev 0) → duman 2500 → 1 sn → alev=1: yeni teyit.
  - Ters sıra: alev=1 (#512) → 2 sn → duman 2500 (#513) → teyit, `iliskili=[512, 513]`.
  - Pencere dışı durum, canlı testte pencereyi düşürmek yerine saf `korelasyon()`
    fonksiyonuyla denendi: 11 sn fark → teyit yok; tam 10 sn → teyit; kilitliyken
    alevin söndüp yanması → teyit yok; ikisi de normale dönünce → yeni teyit.
  - `bildirim.mail_olustur` teyit olayı için konu
    "[KRİTİK] YANGIN TEYİTLİ — dugum1 (Ana Bina · A Kanadı)" ve "İlişkili: #412, #413"
    satırını üretti (gerçek mail gönderilmedi; test_dugum bildirimden hariç).
  - T6 yalnızca tekil olay bildirimini ölçtüğü için süreç içinde korelasyonu kapatır
    ve modu mesai_disi'ye sabitler; teyit maili burada doğrulanır.
- T11 (15 Ekim 2026, 13:55): açık bir WebSocket istemcisi varken PUT mesai → 200 ve
  `{"tip": "mod", "veri": {"mod": "mesai", ...}}` mesajı geldi. Her modda hareket=1:
  - mesai → bilgi, `durum=cozuldu`, `onaylayan=sistem`, `kural=mesai`, "Hareket algılandı · mesai saati"
  - mesai_disi → orta, `durum=yeni`, `kural=mesai_disi`
  - gece → yuksek, `kural=gece_modu`, "Hareket algılandı · gece modu"
  - GET → `{mod: gece, etkin_mod: gece}`; PUT "tatil" ve boş gövde → 422, mod değişmedi.
  - Otomatik mod, `hareket_seviyesi("otomatik", t)` ile (varsayılan saatler sabitlenerek)
    9 an için doğrulandı: hafta içi 10:00 mesai/bilgi, 20:00 mesai dışı/orta,
    02:00 gece/yüksek, cumartesi 11:00 mesai dışı/orta, cumartesi 02:00 gece,
    sınırlar 08:00 mesai, 18:00 mesai dışı, 23:00 gece, 06:00 mesai dışı.
  - Elle seçilen mod saatten bağımsız (mesai/mesai_disi/gece → bilgi/orta/yuksek).
  - Çalışma sonunda mod kullanıcının önceki değerine (otomatik) geri alındı.
  - Temizlik: olaylar 30, olay_adimlari 2, sensor_gecmis 42 kayıt silindi.
- T9 uyarlaması (15 Ekim 2026, kimlik doğrulama): `onaylayan` artık token'dan geldiği
  için "boş onaylayan" ve "41 karakter onaylayan → 422" kontrolleri, "gövdedeki
  onaylayan yok sayılıyor" kontrolüne dönüştü: gövdede "Sahte Kişi" gönderildi,
  `olay_adimlari.kim` ve `onaylayan` = geçici operatörün adı ("Test Operatör …").
  durum=xyz, durum=yeni ve 301 karakter not yine 422.
- T12 (15 Ekim 2026, 14:49): geçici kullanıcılar `t_admin_<6 hex>` / `t_op_<6 hex>`,
  parolalar `secrets.token_urlsafe` ile rastgele. Doğrulananlar:
  - `/api/saglik` token'sız 200; `/api/olaylar` token'sız 401 ("Giriş yapılmamış")
  - başka bir anahtarla imzalanmış ve rolü "admin" yazılmış token → 401
  - yanlış parola ve olmayan kullanıcı → ikisi de 401 ve aynı mesaj
    ("Kullanıcı adı veya parola hatalı")
  - ayrı, rastgele bir kullanıcı adıyla 5 hatalı deneme 401, 6. deneme 429,
    `Retry-After: 60` (test operatörü kilitlenmesin diye ayrı ad)
  - pasif yapılan kullanıcı doğru parolayla 401
  - operatör PUT mod → 403 ve mod değişmedi; admin PUT mod → 200,
    `degistiren` = admin adı; operatörün açık WS bağlantısına gelen `mod` mesajı
    da `degistiren` taşıdı
  - `/api/kullanicilar` operatör 403, admin 200; admin kendini pasif yapamaz 409;
    7 karakterlik parolayla kullanıcı ekleme 422
  - son aktif admin kuralı (operatöre düşürme ve pasif yapma → `son_admin`) geçici
    bir veritabanında birim testle (canlı DB'de başka admin olabileceği için)
  - operatör PATCH cozuldu (gövdede sahte onaylayan) → `olay_adimlari.kim` =
    operatörün adı
  - süresi dolmuş token **canlı backend'e karşı**: `.env`'deki `JWT_GIZLI_ANAHTAR`
    ile süreç içinde imzalanan geçerli token 200 aldı (anahtarın backend'le aynı
    olduğu kanıtı), aynı kullanıcı için `exp` 60 sn önce olan token 401
  - WS token'sız ve bozuk token → kapanış kodu 4401; geçerli token → bağlantı açık
  - testteki 87 API yanıt gövdesinin hiçbirinde `"parola_hash"`, `"tuz"` ya da
    geçici parolalar yok
  - Temizlik: olaylar 31, olay_adimlari 3, sensor_gecmis 43 kayıt; 2 geçici
    kullanıcı ve 3 giriş kaydı silindi; mod ve "değiştiren" kaydı eski haline döndü.
- Not (15 Ekim 2026, 14:35): ilk T1-T12 çalıştırmasında T8 ve T10 başarısız oldu.
  Neden kod değil ortamdı: backend yeniden başlatılırken eski `--reload`
  sürecinin yetim worker'ı açık kalmış, iki backend aynı MQTT client_id
  ("kampus-backend") ile broker'da birbirini düşürüyordu; bellekteki histerezis
  ve korelasyon durumu iki süreç arasında bölündü. Yetim süreç kapatılınca T1-T12
  iki ardışık çalıştırmada da başarılı oldu.
- Göç (15 Ekim 2026, kimlik doğrulama): backend açılışta `kullanicilar` ve
  `giris_kayitlari` tablolarını oluşturdu; mevcut olaylar değişmedi.
- Göç (15 Ekim 2026, akıllı kurallar): backend yeniden yüklenince olaylar tablosuna `kural` ve
  `iliskili` kolonları eklendi (ALTER TABLE, mevcut kayıtlar NULL), `ayarlar` tablosu
  oluşturuldu; mevcut olaylar değişmedi.
- Göç (15 Ekim 2026, 12:50): ilk açılışta olaylar tablosuna 6 kolon eklendi; mevcut
  4 orta (hareket) kayıt `cozuldu` / `sistem (göç)`, 3 uyari kayıt `cozuldu` /
  `sistem` oldu. Göç öncesi yedek: backend/yedekler/kampus_20261015_1238_goconcesi.db.
