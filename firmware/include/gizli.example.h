// Gizli bilgiler ŞABLONU — repoya bu dosya girer.
// Kullanım: bu dosyayı aynı klasöre gizli.h adıyla kopyala ve değerleri doldur.
//   copy include\gizli.example.h include\gizli.h
// gizli.h .gitignore'dadır; asla commit edilmez.
#pragma once

// Wi-Fi (ESP32-S2 yalnızca 2.4 GHz ağlara bağlanabilir). Kart açılışta tarar,
// görünen ağlardan sıradakine bağlanır; o ağda broker'ı bulamazsa diğerine geçer.
// Ağ 1 (ör. ev)
#define WIFI_SSID      "ag-adi"
#define WIFI_PAROLA    "ag-parolasi"
// Ağ 2 (ör. iPhone Kişisel Erişim Noktası; SSID = Ayarlar > Genel > Hakkında > Ad).
// Kullanılmayacaksa "" bırakın.
#define WIFI2_SSID     ""
#define WIFI2_PAROLA   ""

// MQTT broker = Mosquitto'nun çalıştığı bilgisayar.
// MQTT_MDNS: bilgisayarın adı (PowerShell: hostname), ".local" olmadan. Kart her
// bağlanışta <ad>.local'ı mDNS ile çözer; IP ağdan ağa değişse de yeniden yükleme
// gerekmez. "" = mDNS kapalı.
#define MQTT_MDNS      "bilgisayar-adi"
// Yedek: mDNS çözülemezse bağlı ağın sabit IP'si (ipconfig). "" = yedek yok.
#define MQTT_HOST      "192.168.1.100"   // ağ 1
#define MQTT_HOST2     ""                // ağ 2
#define MQTT_PORT      1883
#define MQTT_KULLANICI "kampus"
#define MQTT_PAROLA    "mqtt-parolasi"

// Düğüm kimliği: topic'lerde ve JSON'da kullanılır (kampus/guvenlik/<DUGUM_ID>/...)
#define DUGUM_ID       "dugum1"
