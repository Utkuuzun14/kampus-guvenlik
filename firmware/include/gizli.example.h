// Gizli bilgiler ŞABLONU — repoya bu dosya girer.
// Kullanım: bu dosyayı aynı klasöre gizli.h adıyla kopyala ve değerleri doldur.
//   copy include\gizli.example.h include\gizli.h
// gizli.h .gitignore'dadır; asla commit edilmez.
#pragma once

// Wi-Fi (ESP32-S2 yalnızca 2.4 GHz ağlara bağlanabilir)
#define WIFI_SSID      "ag-adi"
#define WIFI_PAROLA    "ag-parolasi"

// MQTT broker = Mosquitto'nun çalıştığı bilgisayarın yerel IP'si (ipconfig)
#define MQTT_HOST      "192.168.1.100"
#define MQTT_PORT      1883
#define MQTT_KULLANICI "kampus"
#define MQTT_PAROLA    "mqtt-parolasi"

// Düğüm kimliği: topic'lerde ve JSON'da kullanılır (kampus/guvenlik/<DUGUM_ID>/...)
#define DUGUM_ID       "dugum1"
