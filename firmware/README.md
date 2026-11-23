# ESP32-S2 Firmware (Wemos LOLIN S2 Mini)

Sensör düğümü firmware'i. `scripts/sahte_veri.py`'nin MQTT'ye yayınladığı her şeyi aynı
biçimde yayınlar (`docs/SOZLESMELER.md` §2–§3); backend ve panel değişmeden gerçek kartla çalışır.

| | |
|---|---|
| Kart | Wemos LOLIN S2 Mini (ESP32-S2, 4 MB flash, 2 MB PSRAM, yerel USB) |
| Platform | PlatformIO, `espressif32@6.9.0` (Arduino-ESP32 2.0.17) |
| Kütüphaneler | `256dpi/MQTT@2.5.2` (QoS 1 yayın + LWT), `bblanchon/ArduinoJson@7.2.1` |
| Kod | `src/main.cpp`, pinler/ayarlar `include/pinler.h`, gizli bilgiler `include/gizli.h` |

## MQTT davranışı (sahte üreteçle aynı)

| Ne | Değer |
|---|---|
| Ölçüm konuları | `kampus/guvenlik/<DUGUM_ID>/duman`, `.../hareket`, `.../alev` |
| Ölçüm yükü | `{"dugum":"dugum1","sensor":"hareket","deger":1,"zaman":1730000000}` |
| Yayın kuralı | her 3 sn'de bir tur, sıra: duman → hareket → alev; QoS 1, retain yok |
| Online | her bağlanışta `.../durum` ← `{"dugum":"dugum1","durum":"online","zaman":<epoch>}` (QoS 1) |
| LWT | `.../durum` ← `{"dugum":"dugum1","durum":"offline","zaman":0}` (QoS 1, retain yok) |
| keepalive | 60 sn, clean session; CONNACK/PUBACK bekleme 8 sn (`MQTT_ZAMAN_ASIMI_MS`), Wi-Fi modem uykusu kapalı |
| client_id | `esp32-<DUGUM_ID>` (sahte üreteç: `sahte-<dugum>`) |
| zaman | NTP'den epoch saniye (`tr.pool.ntp.org`, `pool.ntp.org`, Europe/Istanbul); saat gelmeden `0` → backend kendi saatini yazar |

- **Hareket:** 3 sn'lik turda PIR bir an bile HIGH olduysa `1`, değilse `0`.
- **Alev:** turda alev bir an bile görüldüyse `1` (DO LOW = alev, `ALEV_AKTIF_DUSUK`).
- **Duman:** MQ-2 AO'nun 10 örnek ortalaması, 12 bit (0–4095), 11 dB zayıflatma.
- **Isınma:** PIR ve MQ-2 açılıştan sonraki ilk 60 sn yayınlanmaz (seri çıktıda geri sayım).
  Bu sürede yalnızca `online` gider; panel düğümü 30 sn sonra bir süre "çevrimdışı" gösterebilir, ısınma bitince düzelir.
- **Kapalı sensör** (`pinler.h`'de `*_AKTIF 0`) hiç okunmaz, hiç yayınlanmaz. Şu an:
  `PIR_AKTIF 1`, `MQ2_AKTIF 1`, `ALEV_AKTIF 1` (üçü de 5 V besleme + gerilim bölücüyle, 23.11.2026).
- Sahte üretecin demo kontrol konusu (`kampus/demo/...`) gerçek kartta yoktur (sözleşme §2).
- Fark: sahte üreteç MQTT 5 ile bağlanır, kart MQTT 3.1.1 ile; JSON'da boşluk yoktur
  (Python `json.dumps` boşluklu yazar). Backend her ikisini aynı işler.

## Bağlantı şeması

| Sensör | Pin | Kart pini |
|---|---|---|
|| **MQ-2** | VCC | VBUS (5 V) |
| | GND | GND |
| | AO | 10 kΩ → GPIO 3 (ADC1), GPIO 3 → 10 kΩ → GND |
| **Alev (KY-026)** | VCC | VBUS (5 V) |
| | GND | GND |
| | DO | 10 kΩ → GPIO 5, GPIO 5 → 20 kΩ → GND |
| **PIR (HC-SR501)** | VCC | VBUS (5 V) |
| | GND | GND |
| | OUT | GPIO 7 (doğrudan) |
| Dahili LED | — | GPIO 15 (aktif HIGH) |

Kartın arkasındaki çift sıra pinlerde **DIŞ sıra** kullanılıyor.

**Neden 5 V ve bölücü:** 3V3 hattı MQ-2'yi (ısıtıcısı 5 V için tasarlanmış, ~150 mA)
ve alev modülünü besleyemedi; üç sensör de VBUS'tan (USB 5 V) beslenir. 5 V'la
beslenen modüllerin çıkışı 5 V'a çıkabildiği, ESP32-S2 pinleri ise en fazla 3,3 V
kabul ettiği için çıkışlar bölünür:
- MQ-2 AO: 2×10 kΩ → 5 V × 1/2 = en fazla **2,5 V** (11 dB ADC aralığı içinde).
  Backend'in duman eşiği (1800) bu ölçekteki ham değerdir.
- Alev DO: 10 kΩ + 20 kΩ → 5 V × 20/30 ≈ **3,3 V** (HIGH = alev yok, LOW = alev).
- PIR OUT: HC-SR501 kart üstü 3,3 V regülatörüyle çıkış verir, bölücü gerekmez.

```
        LOLIN S2 Mini
     ┌──────────────────┐
     │  VBUS (5V) ──────┼── MQ-2 VCC, Alev VCC, PIR VCC
     │  GND ────────────┼── MQ-2 GND, Alev GND, PIR GND
     │  GPIO 3 ◄──┬─────┼── 10k ── MQ-2 AO
     │            └─────┼── 10k ── GND
     │  GPIO 5 ◄──┬─────┼── 10k ── Alev DO
     │            └─────┼── 20k ── GND
     │  GPIO 7 ◄────────┼── PIR OUT
     │  GPIO 15 (LED)   │
     └──────────────────┘
```

**Ölçülen değerler (23.11.2026):** MQ-2 temiz havada, ısınma sonrası ham ~300
(285–352); bütan gazında 2831–3367. Alev DO alev yokken HIGH, çakmakla (20–30 cm)
LOW. Testler: docs/TEST_SONUCLARI.md T13–T16.

*LED:** bağlanırken yavaş yanıp söner (1 Hz), Wi-Fi + MQTT bağlıyken sabit yanar,
hareket/alev/duman eşiği anında kısa hızlı yanıp söner.

## 1. PlatformIO Core kurulumu

```bash
python -m pip install --user platformio
```

`pio` komutu `%APPDATA%\Python\Python312\Scripts` klasörüne kurulur. Bu klasör PATH'te
değilse ya PATH'e ekleyin ya da `pio` yerine `python -m platformio` yazın.

## 2. gizli.h doldurma

```bash
copy firmware\include\gizli.example.h firmware\include\gizli.h
```

`firmware/include/gizli.h` içindeki değerleri doldurun (dosya `.gitignore`'da, repoya girmez):

| Alan | Ne yazılır |
|---|---|
| `WIFI_SSID`, `WIFI_PAROLA` | Ağ 1, ör. ev ağı (**2.4 GHz**, aşağıdaki Wi-Fi notu) |
| `WIFI2_SSID`, `WIFI2_PAROLA` | Ağ 2, ör. iPhone Kişisel Erişim Noktası; kullanılmıyorsa `""` |
| `MQTT_MDNS` | Bilgisayarın adı (`hostname` komutu), `.local` olmadan; `""` = mDNS kapalı |
| `MQTT_HOST`, `MQTT_HOST2` | Yedek: mDNS çözülemezse ağ 1 / ağ 2'deki bilgisayar IP'si (adım 3); `""` = yedek yok |
| `MQTT_PORT` | `1883` |
| `MQTT_KULLANICI`, `MQTT_PAROLA` | Mosquitto `passwd` kullanıcısı (backend'in kullandığı kullanıcı) |
| `DUGUM_ID` | `"dugum1"` |

`gizli.h` yoksa derleme şu hatayla durur: `include/gizli.h bulunamadi: ...`.
Eski bir `gizli.h`'de `WIFI2_*`, `MQTT_HOST2`, `MQTT_MDNS` yoksa boş sayılır (tek ağ, sabit IP).

**SSID birebir aynı olmalı** (büyük/küçük harf, boşluk, kesme işareti). iPhone'da erişim
noktasının adı Ayarlar > Genel > Hakkında > Ad'dır; emin olmak için bilgisayar o ağa
bağlıyken `netsh wlan show interfaces` çıktısındaki `SSID` satırına bakın.

## 3. Broker adresi: mDNS, yedek olarak sabit IP

Kart her MQTT bağlantısından önce `<MQTT_MDNS>.local`'ı mDNS ile çözer. Windows 10/11
bilgisayar adına mDNS ile kendiliğinden cevap verir (DNS İstemcisi hizmeti, "mDNS (UDP-Gelen)"
güvenlik duvarı kuralı Ortak profilde de açık). Böylece bilgisayarın IP'si ağdan ağa değişse de
yeniden yükleme gerekmez. Denendi (23.11.2026): ev ağında `Utku.local -> 192.168.1.9`, iPhone
erişim noktasında `Utku.local -> 172.20.10.3`.

mDNS çözülemezse bağlı ağın `MQTT_HOST` / `MQTT_HOST2`'si kullanılır. IP'yi bulmak için
bilgisayar o ağa bağlıyken:

```bash
ipconfig
```

"Kablosuz LAN bağdaştırıcısı Wi-Fi" altındaki **IPv4 Adresi** (ör. `192.168.1.9`).

## 4. Windows Güvenlik Duvarı: 1883'e gelen bağlantı izni

TCP 1883 kuralı **tüm profillerde** (Etki alanı, Özel, Ortak) geçerli olmalı: telefon erişim
noktası Windows'ta genelde "Ortak" profilde açılır. Kontrol (yönetici gerekmez):

```powershell
Get-NetFirewallRule -Direction Inbound -Enabled True | Where-Object { ($_ | Get-NetFirewallPortFilter).LocalPort -contains '1883' } | Select-Object DisplayName,Profile,Action
```

`Profile` sütunu `Any` olmalı. Kural yoksa yönetici PowerShell/cmd'de bir kez:

```bash
netsh advfirewall firewall add rule name="Mosquitto 1883" dir=in action=allow protocol=TCP localport=1883 profile=any
```

Mosquitto'nun ağdan dinlediğini (`listener 1883 0.0.0.0`) `backend/mosquitto.conf`'ta kontrol edin.

## 5. Derleme ve yükleme

Komutlar `firmware/` klasöründen:

```bash
pio run
```

```bash
pio run -t upload --upload-port COM5
```

`COM5` yerine kartın portunu yazın (Aygıt Yöneticisi → Bağlantı noktaları, ya da `pio device list`).

**Port görünmüyor / yükleme başlamıyor:** kartı indirme moduna alın: **0** düğmesini basılı
tutun, **RST**'ye basıp bırakın, sonra 0'ı bırakın. Yeni bir COM portu belirir; o portla
yükleyin. **Yüklemeden sonra RST'ye basın** (S2 indirme modundan kendiliğinden çıkmaz).
RST sonrası COM port numarası değişebilir.

## 6. Seri izleme

```bash
pio device monitor
```

115200 baud, USB CDC. Örnek çıktı:

```
[SENSOR] PIR (GPIO 7): açık | MQ-2 (GPIO 3): açık | Alev (GPIO 5): açık
[WiFi] Ağlar taranıyor...
[WiFi] Tarama bitti: 9 ağ, 7017 ms.
[WiFi] Bilinen ağ 1 görünüyor: 'ev-agi' (-68 dBm)
[WiFi] Ağ 1 'ev-agi' ağına bağlanılıyor...
[WiFi] Bağlandı (ağ 1). IP: 192.168.1.18, sinyal: -67 dBm
[MQTT] mDNS: Utku.local -> 192.168.1.9
[MQTT] 192.168.1.9:1883 adresine bağlanılıyor (istemci: esp32-dugum1)...
[MQTT] Bağlandı (LWT kuruldu: offline, QoS 1).
[MQTT] -> kampus/guvenlik/dugum1/durum {"dugum":"dugum1","durum":"online","zaman":0}
[ISINMA] PIR/MQ-2 ısınıyor: 45 sn kaldı (bu sürede yayınlanmaz)
[NTP] Saat eşitlendi: 27.10.2026 14:03:11 (İstanbul), epoch=1792926191
[SENSOR] PIR pin=LOW -> hareket=0
[MQTT] -> kampus/guvenlik/dugum1/hareket {"dugum":"dugum1","sensor":"hareket","deger":0,"zaman":1792926194}
```

Kart açılışta seri monitörü en fazla 2 sn bekler; ilk satırları kaçırırsanız monitör açıkken RST'ye basın.

## 7. Gerçek dugum1 + sahte dugum2, dugum3

Kart `dugum1` olarak yayın yaparken sahte üreteci yalnızca diğer iki düğüm için çalıştırın
(proje kökünden, backend venv aktifken):

```bash
python scripts/sahte_veri.py --dugumler dugum2,dugum3
```

`scripts\baslat.bat` üç düğümü birden başlatır; kart takılıyken onun "Sahte Veri" penceresini
kapatıp yukarıdaki komutu kullanın, yoksa dugum1 için iki kaynak karışır.

## 8. Okulda kurulum (iPhone erişim noktası, yeniden yükleme yok)

Kart evde ve okulda aynı firmware'le çalışır; `gizli.h`'de iki ağ ve `MQTT_MDNS` dolu olmalı.

1. **iPhone:** Ayarlar > Kişisel Erişim Noktası > "Başkalarının Katılmasına İzin Ver" açık,
   **"Uyumluluğu En Üst Düzeye Çıkar" açık** (2.4 GHz; kapalıysa kart ağı göremez). Kurulum
   sırasında bu ekranı açık tutun: iPhone ağı ancak o ekran açıkken ya da bir cihaz bağlıyken
   yayınlar.
2. **Bilgisayar:** Wi-Fi'dan iPhone erişim noktasına bağlanın (okul ağına değil).
3. **Mosquitto, backend, panel:** her zamanki gibi başlatın (`scripts\baslat.bat` ya da elle).
   Panel ve backend `localhost` kullandığı için ağ değişince ayar gerekmez.
4. **Kartı** USB'den (bilgisayar ya da powerbank) besleyin. Açılışta ağları tarar (~7 sn),
   erişim noktasına bağlanır, `<MQTT_MDNS>.local`'ı çözer ve MQTT'ye bağlanır. LED sabit
   yanınca hazırdır; panelde dugum1 çevrimiçi olur (PIR/MQ-2 verisi 60 sn ısınmadan sonra).
5. Olmazsa `pio device monitor` ile seri çıktıya bakın:
   - `Denenecek bilinen ağ yok` → SSID yanlış ya da erişim noktası 2.4 GHz değil (adım 1, adım 2'deki SSID notu).
   - `Bağlanamadı (bağlantı reddedildi (parola?))` → `WIFI2_PAROLA` yanlış.
   - `mDNS: ... çözülemedi` ve `broker adresi yok` → `MQTT_HOST2`'ye bilgisayarın erişim
     noktasındaki IP'sini yazıp (ipconfig, genelde `172.20.10.x`) yeniden yükleyin.
   - `Görünen bilinen ağların hepsi bu tur denendi` → bilgisayar aynı ağda değil ya da
     Mosquitto kapalı / 1883 güvenlik duvarında kapalı (adım 4).

**Ağ seçimi nasıl çalışır:** kart görünen bilinen ağlardan, son MQTT'ye bağlandığı ağı
önce dener (açılışta ağ 1). O ağda broker'a 3 denemede (~15 sn) ulaşamazsa (bilgisayar başka
ağda) ağı bırakıp diğer bilinen ağa geçer; hiçbiri olmazsa artan beklemeyle baştan tarar.
Böylece evde iki ağ birden görünse de bilgisayarın bağlı olduğu ağı bulur. Denendi
(23.11.2026): bilgisayar erişim noktasındayken kart ev ağından erişim noktasına, bilgisayar
eve dönünce erişim noktasından ev ağına kendiliğinden geçti (her biri ~20–30 sn).

## Wi-Fi notu

- ESP32-S2 **yalnızca 2.4 GHz** destekler. 5 GHz ağlar listede bile görünmez.
- **eduroam** (WPA2-Enterprise) ve yurt ağları (tarayıcıdan giriş/captive portal, istemciler arası
  engelleme) çalışmaz. Bunun yerine **telefon erişim noktası** kullanın, bant ayarını **2.4 GHz**
  yapın (iPhone: "Uyumluluğu En Üst Düzeye Çıkar").
- **Bilgisayar ve kart aynı ağda olmalı** (bilgisayar da erişim noktasına bağlanır).
- Kart bağlanamazsa seri çıktıda durumu ve 2.4 GHz hatırlatmasını yazar, artan beklemeyle
  (2 → 4 → … → 60 sn) yeniden tarar. Bazı S2 Mini kartlar tam güçte bağlanamıyor:
  `pinler.h`'de `WIFI_DUSUK_GUC 1` yapıp deneyin.

## Teşhis modu

`pinler.h`'de `TESHIS_MODU 1` yapıp yükleyin: kart Wi-Fi/MQTT'ye bağlanmaz, her 500 ms tek satırda
GPIO 1–14 dijital seviyelerini ve GPIO 1–10 analog (12 bit) değerlerini yazar:

```
[TESHIS] D: 1=0 2=0 3=1 4=0 5=1 6=0 7=0 ... | A: 1=0 2=12 3=1830 4=0 ...
```

Kablonun hangi pine gittiğini ve sensörün tepki verip vermediğini görmek için kullanılır
(PIR'in önünde el sallayın → `7=1`; MQ-2'ye çakmak gazı → `A: 3=` yükselir).
Boşta (bağlantısız) pinler rastgele 0/1 gösterebilir. İşiniz bitince `TESHIS_MODU 0` yapın.
