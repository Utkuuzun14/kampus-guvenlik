# Mosquitto Broker Kurulum ve Test Rehberi (Windows)

Bu rehber, MQTT broker'ı Windows'a kurup kimlik doğrulamalı olarak
çalıştırmayı ve test etmeyi anlatır. Komutlar yönetici (administrator)
yetkili PowerShell / cmd üzerinde çalıştırılır.

---

## 1. İndirme ve kurulum
1. https://mosquitto.org/download adresine git.
2. Windows bölümünden 64-bit installer'ı indir (mosquitto-2.x.x-install-windows-x64.exe).
3. İndirilen .exe'yi çalıştır. Kurulum sırasında "Service" seçeneği işaretliyse bırak.
4. Varsayılan kurulum yolu: C:\Program Files\mosquitto

## 2. Kurulumu doğrulama
Yönetici cmd/PowerShell aç ve:
```
cd "C:\Program Files\mosquitto"
mosquitto -h
```
Versiyon ve yardım metni görünüyorsa kurulum başarılı.

## 3. Servisi durdurma (ayar öncesi)
Kurulum broker'ı otomatik başlatmış olabilir. Ayarları uygulamadan önce durdur:
```
net stop mosquitto
```
"Servis çalışmıyor" hatası alırsan sorun yok, zaten duruktur.

## 4. Parola dosyası oluşturma
Anonim erişim kapalı olduğu için kullanıcı adı/parola gerekir.
"kampus" adlı kullanıcı oluştur:
```
cd "C:\Program Files\mosquitto"
mosquitto_passwd -c "C:\Program Files\mosquitto\passwd" kampus
```
Komut bir parola soracak (örn. kampus123 — sonra değiştirilebilir). İki kez gir.
Bu, passwd adlı şifreli parola dosyasını oluşturur.

## 5. Yapılandırma dosyasını yerleştirme
Projedeki backend/mosquitto.conf dosyasını Mosquitto klasörüne kopyala:
```
Copy-Item "C:\Users\utkuu\Desktop\kampus-guvenlik\backend\mosquitto.conf" "C:\Program Files\mosquitto\mosquitto.conf"
```
(Yönetici izni ister, onayla.)

## 6. Broker'ı elle (test modunda) başlatma
Servis yerine önce elle başlatıp logları canlı görelim:
```
cd "C:\Program Files\mosquitto"
mosquitto -c "C:\Program Files\mosquitto\mosquitto.conf" -v
```
-v = ayrıntılı (verbose) log. Bu pencere açık kalmalı; broker burada çalışır.
"Opening ipv4 listen socket on port 1883" benzeri satır görürsen broker ayakta.

## 7. Test: yayınla-abone ol (iki ayrı terminal)
Broker çalışırken İKİ yeni terminal aç.

Terminal A (abone ol):
```
cd "C:\Program Files\mosquitto"
mosquitto_sub -h localhost -p 1883 -u kampus -P kampus123 -t "kampus/guvenlik/#" -v
```

Terminal B (mesaj yayınla):
```
cd "C:\Program Files\mosquitto"
mosquitto_pub -h localhost -p 1883 -u kampus -P kampus123 -t "kampus/guvenlik/dugum1/alev" -m "{\"dugum\":\"dugum1\",\"sensor\":\"alev\",\"deger\":1,\"zaman\":0}"
```

Terminal A'da mesaj anında görünürse: broker + kimlik doğrulama + konu yapısı ÇALIŞIYOR demektir.

## 8. Sık karşılaşılan hatalar
- "Connection refused": broker çalışmıyor (adım 6'yı kontrol et).
- "not authorised" / "Connection Refused: not authorised": kullanıcı adı/parola yanlış veya passwd dosyası yolu conf'ta yanlış.
- Türkçe karakter/log sorunları: cmd yerine PowerShell dene.
- Servis başlamıyor: passwd dosyası yok veya conf'taki password_file yolu hatalı.

## 9. Test sonrası: servis olarak çalıştırma
Elle test bittiğinde broker'ı servis olarak başlatabilirsin:
```
net start mosquitto
```
Servis, mosquitto.conf ayarlarını otomatik kullanır ve arka planda çalışır.
