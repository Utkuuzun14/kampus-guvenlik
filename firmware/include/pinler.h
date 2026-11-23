// Pin atamaları ve derleme zamanı ayarları — Wemos LOLIN S2 Mini.
// Bağlantı şeması: firmware/README.md
#pragma once

// --- Sensör pinleri ---
#define PIN_MQ2   3    // MQ-2 AO (ADC1_CH2)
#define PIN_ALEV  5    // Alev sensörü DO
#define PIN_PIR   7    // HC-SR501 OUT (aktif HIGH)
#define PIN_LED   15   // Dahili LED (aktif HIGH)

// Alev modülü alev görünce DO'yu LOW'a çeker.
#define ALEV_AKTIF_DUSUK true

// --- Sensör açma/kapama (0 = hiç okunmaz, hiç yayınlanmaz) ---
// MQ-2 AO 2x10k bölücüyle (maks 2.5 V), alev DO 10k+20k bölücüyle bağlı.
#define PIR_AKTIF   1
#define MQ2_AKTIF   1
#define ALEV_AKTIF  1

// --- ADC (MQ-2) ---
// S2'nin varsayılanı 13 bit; sözleşme 0–4095 (12 bit) bekler.
#define ADC_COZUNURLUK  12
#define ADC_ORNEK_SAYI  10

// --- Zamanlama ---
#define YAYIN_ARALIGI_MS  3000UL   // sahte_veri.py YAYIN_ARALIGI = 3 sn
#define ISINMA_MS         60000UL  // PIR ve MQ-2 ilk 60 sn yayınlanmaz

// Yalnızca LED'in "alarm" yanıp sönmesi için (karar backend'de verilir, §4).
#define LED_ESIK_DUMAN  1800

// --- Teşhis modu ---
// 1: Wi-Fi/MQTT'ye bağlanmaz; her 500 ms GPIO 1–14 dijital ve GPIO 1–10 analog
// değerlerini tek satırda yazar (kablo/besleme kontrolü için).
#define TESHIS_MODU 0

// Bazı S2 Mini kartları tam güçte Wi-Fi'ye bağlanamıyor; bağlanamazsan 1 yap.
#define WIFI_DUSUK_GUC 0
