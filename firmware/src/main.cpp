/*
 * Kampüs Güvenlik Sistemi — ESP32-S2 sensör düğümü (Wemos LOLIN S2 Mini)
 *
 * scripts/sahte_veri.py'nin MQTT'ye yayınladığı her şeyi aynı biçimde yayınlar
 * (docs/SOZLESMELER.md §2–§3), böylece backend ve panel değişmeden çalışır:
 *   - Konular: kampus/guvenlik/<dugum>/{duman,hareket,alev,durum}
 *   - Ölçüm:  {"dugum","sensor","deger","zaman"}, QoS 1, retain yok
 *   - Durum:  bağlanınca {"dugum","durum":"online","zaman"}, QoS 1
 *   - LWT:    .../durum ← {"dugum","durum":"offline","zaman":0}, QoS 1, retain yok
 *   - keepalive 60 sn, her 3 sn'de bir tur: duman, hareket, alev (bu sırayla)
 *   - zaman: NTP'den epoch saniye; saat gelmeden 0 (backend kendi saatini yazar)
 * Kapalı sensör (pinler.h) hiç okunmaz ve hiç yayınlanmaz.
 * Döngü millis() ile bloklamasız çalışır.
 */
#include <Arduino.h>
#include <WiFi.h>
#include <MQTT.h>
#include <ArduinoJson.h>
#include <time.h>

#include "pinler.h"

#if __has_include("gizli.h")
#include "gizli.h"
#else
#error "include/gizli.h bulunamadi: include/gizli.example.h dosyasini include/gizli.h olarak kopyalayip doldurun (bkz. firmware/README.md)."
#endif

#ifndef DUGUM_ID
#define DUGUM_ID "dugum1"
#endif

// sahte_veri.py'deki "sahte-<dugum>" deseninin gerçek kart karşılığı.
// Önek farklı: sahte üreteç yanlışlıkla aynı düğümle açılırsa iki istemci
// broker'da birbirini sürekli düşürmesin.
#define ISTEMCI_ONEK "esp32-"
#define KONU_ONEK    "kampus/guvenlik/" DUGUM_ID "/"
#define MQTT_KEEPALIVE_SN 60
#define MQTT_ZAMAN_ASIMI_MS 2000

#define NTP_SUNUCU1 "tr.pool.ntp.org"
#define NTP_SUNUCU2 "pool.ntp.org"
#define TZ_ISTANBUL "<+03>-3"        // Europe/Istanbul (UTC+3, yaz saati yok)
#define GECERLI_EPOCH 1700000000L    // bundan küçükse saat henüz gelmemiştir

// ============================================================
// Ortak durum
// ============================================================
static WiFiClient agIstemci;
static MQTTClient mqtt(512);

static const char *KONU_DURUM = KONU_ONEK "durum";
static char lwtYuku[96];
static char istemciId[48];

static bool ntpBasladi = false;
static bool saatGeldi = false;

// ============================================================
// LED: bağlanırken yavaş, bağlıyken sabit, olayda kısa hızlı yanıp söner
// ============================================================
static unsigned long ledFlasBitis = 0;

static void ledFlas() { ledFlasBitis = millis() + 600; }

static void ledGuncelle(bool bagli) {
  unsigned long simdi = millis();
  bool yan;
  if ((long)(ledFlasBitis - simdi) > 0) {
    yan = (simdi / 60) % 2;          // ~8 Hz, 600 ms
  } else if (bagli) {
    yan = true;
  } else {
    yan = (simdi / 500) % 2;         // 1 Hz
  }
  digitalWrite(PIN_LED, yan ? HIGH : LOW);
}

// ============================================================
// Zaman
// ============================================================
static long long zamanDamgasi() {
  time_t t = time(nullptr);
  if (t < GECERLI_EPOCH) return 0;   // SOZLESMELER §3: saat yoksa 0
  if (!saatGeldi) {
    saatGeldi = true;
    struct tm yerel;
    localtime_r(&t, &yerel);
    char metin[32];
    strftime(metin, sizeof(metin), "%d.%m.%Y %H:%M:%S", &yerel);
    Serial.printf("[NTP] Saat eşitlendi: %s (İstanbul), epoch=%ld\n", metin, (long)t);
  }
  return (long long)t;
}

// ============================================================
// Wi-Fi: artan beklemeyle yeniden bağlanma
// ============================================================
enum WifiDurum { WIFI_BOSTA, WIFI_BAGLANIYOR, WIFI_BAGLI, WIFI_BEKLIYOR };
static WifiDurum wifiDurum = WIFI_BOSTA;
static unsigned long wifiZaman = 0;
static unsigned long wifiBekleme = 2000;
static const unsigned long WIFI_DENEME_MS = 15000;
static const unsigned long WIFI_BEKLEME_MAX = 60000;

static const char *wifiDurumMetni(wl_status_t s) {
  switch (s) {
    case WL_IDLE_STATUS:     return "bekliyor";
    case WL_NO_SSID_AVAIL:   return "ağ bulunamadı";
    case WL_CONNECT_FAILED:  return "bağlantı reddedildi (parola?)";
    case WL_CONNECTION_LOST: return "bağlantı kayboldu";
    case WL_DISCONNECTED:    return "bağlı değil";
    case WL_CONNECTED:       return "bağlı";
    default:                 return "bilinmiyor";
  }
}

static void wifiBaslat() {
  Serial.printf("[WiFi] '%s' ağına bağlanılıyor...\n", WIFI_SSID);
  WiFi.disconnect(true);
  WiFi.mode(WIFI_STA);
  WiFi.setHostname("kampus-" DUGUM_ID);
  WiFi.setAutoReconnect(false);      // yeniden bağlanmayı biz yönetiyoruz
  WiFi.setSleep(false);              // MQTT gecikmesi düşük kalsın
  WiFi.begin(WIFI_SSID, WIFI_PAROLA);
#if WIFI_DUSUK_GUC
  WiFi.setTxPower(WIFI_POWER_8_5dBm);
#endif
  wifiDurum = WIFI_BAGLANIYOR;
  wifiZaman = millis();
}

static void wifiDongu() {
  unsigned long simdi = millis();
  wl_status_t s = WiFi.status();

  switch (wifiDurum) {
    case WIFI_BOSTA:
      wifiBaslat();
      break;

    case WIFI_BAGLANIYOR:
      if (s == WL_CONNECTED) {
        wifiDurum = WIFI_BAGLI;
        wifiBekleme = 2000;
        Serial.printf("[WiFi] Bağlandı. IP: %s, sinyal: %d dBm\n",
                      WiFi.localIP().toString().c_str(), WiFi.RSSI());
        if (!ntpBasladi) {
          configTzTime(TZ_ISTANBUL, NTP_SUNUCU1, NTP_SUNUCU2);
          ntpBasladi = true;
          Serial.println("[NTP] Saat isteniyor (tr.pool.ntp.org, pool.ntp.org)...");
        }
      } else if (simdi - wifiZaman >= WIFI_DENEME_MS) {
        Serial.printf("[WiFi] Bağlanamadı (%s). %lu sn sonra tekrar denenecek.\n",
                      wifiDurumMetni(s), wifiBekleme / 1000);
        Serial.println("[WiFi] Hatırlatma: ESP32-S2 yalnızca 2.4 GHz ağlara bağlanır; "
                       "5 GHz, eduroam (kurumsal) ve tarayıcıda giriş isteyen ağlar çalışmaz. "
                       "Telefon hotspot'unu 2.4 GHz'e alıp deneyin.");
        WiFi.disconnect(true);
        wifiDurum = WIFI_BEKLIYOR;
        wifiZaman = simdi;
      }
      break;

    case WIFI_BAGLI:
      if (s != WL_CONNECTED) {
        Serial.printf("[WiFi] Bağlantı koptu (%s). Yeniden bağlanılacak.\n", wifiDurumMetni(s));
        WiFi.disconnect(true);
        wifiDurum = WIFI_BEKLIYOR;
        wifiZaman = simdi;
      }
      break;

    case WIFI_BEKLIYOR:
      if (simdi - wifiZaman >= wifiBekleme) {
        wifiBekleme = min(wifiBekleme * 2, WIFI_BEKLEME_MAX);
        wifiBaslat();
      }
      break;
  }
}

static bool wifiBagli() { return wifiDurum == WIFI_BAGLI; }

// ============================================================
// MQTT
// ============================================================
static bool mqttBagliydi = false;
static unsigned long mqttSonDeneme = 0;
static unsigned long mqttBekleme = 0;    // ilk deneme hemen
static const unsigned long MQTT_BEKLEME_MAX = 30000;

static const char *mqttHataMetni(lwmqtt_err_t hata, lwmqtt_return_code_t kod) {
  switch (kod) {
    case LWMQTT_UNACCEPTABLE_PROTOCOL: return "protokol kabul edilmedi";
    case LWMQTT_IDENTIFIER_REJECTED:   return "istemci kimliği reddedildi";
    case LWMQTT_SERVER_UNAVAILABLE:    return "broker hizmet vermiyor";
    case LWMQTT_BAD_USERNAME_OR_PASSWORD: return "kullanıcı adı/parola hatalı";
    case LWMQTT_NOT_AUTHORIZED:        return "yetkisiz (kullanıcı adı/parola?)";
    default: break;
  }
  switch (hata) {
    case LWMQTT_NETWORK_FAILED_CONNECT:
      return "broker'a ulaşılamadı (IP/port, Mosquitto çalışıyor mu, güvenlik duvarı 1883?)";
    case LWMQTT_NETWORK_TIMEOUT:       return "zaman aşımı";
    case LWMQTT_PONG_TIMEOUT:          return "ping yanıtı gelmedi";
    case LWMQTT_CONNECTION_DENIED:     return "bağlantı reddedildi";
    default:                           return "bilinmeyen hata";
  }
}

static bool yayinla(const char *konu, JsonDocument &doc) {
  char yuk[160];
  serializeJson(doc, yuk, sizeof(yuk));
  bool ok = mqtt.publish(konu, yuk, false, 1);   // retain yok, QoS 1
  Serial.printf("[MQTT] %s %s %s\n", ok ? "->" : "!! YAYINLANAMADI", konu, yuk);
  return ok;
}

static void durumYayinla() {
  JsonDocument doc;
  doc["dugum"] = DUGUM_ID;
  doc["durum"] = "online";
  doc["zaman"] = zamanDamgasi();
  yayinla(KONU_DURUM, doc);
}

static void olcumYayinla(const char *sensor, int deger) {
  char konu[64];
  snprintf(konu, sizeof(konu), KONU_ONEK "%s", sensor);
  JsonDocument doc;
  doc["dugum"] = DUGUM_ID;
  doc["sensor"] = sensor;
  doc["deger"] = deger;
  doc["zaman"] = zamanDamgasi();
  yayinla(konu, doc);
}

static void mqttHazirla() {
  snprintf(istemciId, sizeof(istemciId), ISTEMCI_ONEK "%s", DUGUM_ID);
  JsonDocument lwt;
  lwt["dugum"] = DUGUM_ID;
  lwt["durum"] = "offline";
  lwt["zaman"] = 0;                  // yük bağlanırken sabitlenir (SOZLESMELER §3)
  serializeJson(lwt, lwtYuku, sizeof(lwtYuku));

  mqtt.begin(MQTT_HOST, MQTT_PORT, agIstemci);
  mqtt.setKeepAlive(MQTT_KEEPALIVE_SN);
  mqtt.setCleanSession(true);
  mqtt.setTimeout(MQTT_ZAMAN_ASIMI_MS);
  mqtt.setWill(KONU_DURUM, lwtYuku, false, 1);
}

static void mqttDongu() {
  if (!wifiBagli()) {
    if (mqttBagliydi) {
      Serial.println("[MQTT] Wi-Fi gittiği için MQTT bağlantısı düştü.");
      mqttBagliydi = false;
      mqttBekleme = 0;
    }
    return;
  }

  if (mqtt.connected()) {
    mqtt.loop();
    return;
  }

  if (mqttBagliydi) {
    Serial.printf("[MQTT] Broker bağlantısı koptu (%s). Yeniden bağlanılacak.\n",
                  mqttHataMetni(mqtt.lastError(), mqtt.returnCode()));
    mqttBagliydi = false;
    mqttBekleme = 0;
    mqttSonDeneme = millis();
  }

  if (millis() - mqttSonDeneme < mqttBekleme) return;
  mqttSonDeneme = millis();

  // Tek deneme en fazla ~3 sn sürer (TCP bağlantısı + CONNACK); döngü
  // bunun dışında hiç beklemez, denemeler arası bekleme millis() ile.
  Serial.printf("[MQTT] %s:%d adresine bağlanılıyor (istemci: %s)...\n",
                MQTT_HOST, MQTT_PORT, istemciId);
  if (mqtt.connect(istemciId, MQTT_KULLANICI, MQTT_PAROLA)) {
    mqttBagliydi = true;
    mqttBekleme = 0;
    Serial.println("[MQTT] Bağlandı (LWT kuruldu: offline, QoS 1).");
    durumYayinla();
  } else {
    mqttBekleme = mqttBekleme == 0 ? 2000 : min(mqttBekleme * 2, MQTT_BEKLEME_MAX);
    Serial.printf("[MQTT] Bağlanamadı: %s. %lu sn sonra tekrar.\n",
                  mqttHataMetni(mqtt.lastError(), mqtt.returnCode()), mqttBekleme / 1000);
  }
}

// ============================================================
// Sensörler
// ============================================================
// Tur içinde görülen hareket/alev bir sonraki yayına kadar tutulur: 3 sn'lik
// pencerede kısa bir darbe kaçmasın (sahte üreteç de turda 0/1 yayınlar).
static bool hareketTur = false;
static bool alevTur = false;
static bool pirOnceki = false;
static bool alevOnceki = false;
static bool dumanOnceki = false;

static bool isinmaBitti() { return millis() >= ISINMA_MS; }

#if MQ2_AKTIF
static int mq2Oku() {
  uint32_t toplam = 0;
  for (int i = 0; i < ADC_ORNEK_SAYI; i++) toplam += analogRead(PIN_MQ2);
  return (int)(toplam / ADC_ORNEK_SAYI);
}
#endif

#if ALEV_AKTIF
static bool alevVar() {
  bool seviye = digitalRead(PIN_ALEV);
  return ALEV_AKTIF_DUSUK ? !seviye : seviye;
}
#endif

static void sensorHazirla() {
#if PIR_AKTIF
  pinMode(PIN_PIR, INPUT_PULLDOWN);
#endif
#if ALEV_AKTIF
  pinMode(PIN_ALEV, INPUT);
#endif
#if MQ2_AKTIF
  analogReadResolution(ADC_COZUNURLUK);
  analogSetPinAttenuation(PIN_MQ2, ADC_11db);   // ~0–2.5 V ölçüm aralığı
#endif
  Serial.printf("[SENSOR] PIR (GPIO %d): %s | MQ-2 (GPIO %d): %s | Alev (GPIO %d): %s\n",
                PIN_PIR, PIR_AKTIF ? "açık" : "KAPALI",
                PIN_MQ2, MQ2_AKTIF ? "açık" : "KAPALI",
                PIN_ALEV, ALEV_AKTIF ? "açık" : "KAPALI");
}

// Her döngüde: anlık olayları yakala (tur bayrağı + LED)
static void sensorTara() {
  if (!isinmaBitti()) return;
#if PIR_AKTIF
  bool pir = digitalRead(PIN_PIR) == HIGH;
  if (pir) hareketTur = true;
  if (pir && !pirOnceki) {
    Serial.println("[SENSOR] Hareket algılandı (PIR HIGH)");
    ledFlas();
  }
  pirOnceki = pir;
#endif
#if ALEV_AKTIF
  bool alev = alevVar();
  if (alev) alevTur = true;
  if (alev && !alevOnceki) {
    Serial.println("[SENSOR] ALEV algılandı");
    ledFlas();
  }
  alevOnceki = alev;
#endif
}

static unsigned long sonTur = 0;
static unsigned long sonGeriSayim = 0;

static void turDongu() {
  unsigned long simdi = millis();

  // Isınma geri sayımı (alev ısınma beklemez)
  if (!isinmaBitti()) {
    if ((PIR_AKTIF || MQ2_AKTIF) && simdi - sonGeriSayim >= 5000) {
      sonGeriSayim = simdi;
      Serial.printf("[ISINMA] PIR/MQ-2 ısınıyor: %lu sn kaldı (bu sürede yayınlanmaz)\n",
                    (ISINMA_MS - simdi + 999) / 1000);
    }
  }

  if (simdi - sonTur < YAYIN_ARALIGI_MS) return;
  sonTur = simdi;

  bool yayin = mqtt.connected();
  bool isindi = isinmaBitti();

  // sahte_veri.py ile aynı sıra: duman, hareket, alev
#if MQ2_AKTIF
  if (isindi) {
    int duman = mq2Oku();
    Serial.printf("[SENSOR] MQ-2 ham=%d (%d örnek ort.)%s\n", duman, ADC_ORNEK_SAYI,
                  duman > LED_ESIK_DUMAN ? " (eşik üstü)" : "");
    bool dumanAlarm = duman > LED_ESIK_DUMAN;
    if (dumanAlarm && !dumanOnceki) ledFlas();
    dumanOnceki = dumanAlarm;
    if (yayin) olcumYayinla("duman", duman);
  }
#endif
#if PIR_AKTIF
  if (isindi) {
    int hareket = (hareketTur || digitalRead(PIN_PIR) == HIGH) ? 1 : 0;
    hareketTur = false;
    Serial.printf("[SENSOR] PIR pin=%s -> hareket=%d\n",
                  digitalRead(PIN_PIR) ? "HIGH" : "LOW", hareket);
    if (yayin) olcumYayinla("hareket", hareket);
  }
#endif
#if ALEV_AKTIF
  {
    int alev = (alevTur || alevVar()) ? 1 : 0;
    alevTur = false;
    Serial.printf("[SENSOR] Alev DO=%s -> alev=%d\n",
                  digitalRead(PIN_ALEV) ? "HIGH" : "LOW", alev);
    if (yayin) olcumYayinla("alev", alev);
  }
#endif
  if (!yayin && (isindi || ALEV_AKTIF)) {
    Serial.println("[MQTT] Bağlı değil, bu tur yayınlanmadı.");
  }
}

// ============================================================
// Teşhis modu: ağsız, ham pin seviyeleri
// ============================================================
#if TESHIS_MODU
static void teshisDongu() {
  static unsigned long son = 0;
  if (millis() - son < 500) return;
  son = millis();

  char satir[256];
  int n = snprintf(satir, sizeof(satir), "[TESHIS] D:");
  for (int p = 1; p <= 14; p++) {
    pinMode(p, p == PIN_PIR ? INPUT_PULLDOWN : INPUT);
    n += snprintf(satir + n, sizeof(satir) - n, " %d=%d", p, digitalRead(p));
  }
  n += snprintf(satir + n, sizeof(satir) - n, " | A:");
  for (int p = 1; p <= 10; p++) {
    n += snprintf(satir + n, sizeof(satir) - n, " %d=%d", p, analogRead(p));
  }
  Serial.println(satir);
  digitalWrite(PIN_LED, (millis() / 500) % 2);
}
#endif

// ============================================================
void setup() {
  Serial.begin(115200);
  Serial.setTxTimeoutMs(0);          // seri monitör açık değilse yazma beklemesin
  // USB CDC'nin bilgisayarda açılması için en fazla 2 sn (yalnızca açılışta)
  unsigned long bas = millis();
  while (!Serial && millis() - bas < 2000) delay(10);

  pinMode(PIN_LED, OUTPUT);
  digitalWrite(PIN_LED, LOW);

  Serial.println();
  Serial.println("==============================================");
  Serial.println(" Kampüs Güvenlik — ESP32-S2 düğümü: " DUGUM_ID);
  Serial.println("==============================================");

#if TESHIS_MODU
  analogReadResolution(ADC_COZUNURLUK);
  analogSetAttenuation(ADC_11db);
  Serial.println("[TESHIS] Teşhis modu: Wi-Fi/MQTT kapalı. Her 500 ms GPIO 1-14 dijital, 1-10 analog.");
#else
  sensorHazirla();
  mqttHazirla();
  if (PIR_AKTIF || MQ2_AKTIF) {
    Serial.printf("[ISINMA] PIR/MQ-2 ilk %lu sn yayınlanmayacak.\n", ISINMA_MS / 1000);
  }
#endif
}

void loop() {
#if TESHIS_MODU
  teshisDongu();
#else
  wifiDongu();
  mqttDongu();
  sensorTara();
  turDongu();
  ledGuncelle(wifiBagli() && mqtt.connected());
#endif
}
