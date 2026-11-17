// DeltaFiltre — build-time configuration (design values, Phase 6 dossier).
// FIRST IMPLEMENTATION — not bench-tested. Pins avoid ESP32 strapping pins
// (GPIO 0, 2, 12, 15) on the SD interface.
#pragma once

// ---- Measurement cadence -------------------------------------------------
#define DF_BURST_PERIOD_US   60000000ULL  // wake every 60 s for a burst
#define DF_BURST_SAMPLES     8            // conversions per channel per burst
#define DF_WINDOW_MINUTES    5            // logged aggregate = 5-min median

// ---- Alarm defaults (spec EF-11) ----------------------------------------
#define DF_DELTA_DEFAULT_KPA 20.0f        // adjustable 20-40 kPa
#define DF_HYSTERESIS_KPA    5.0f
#define DF_PERSISTENCE       3            // consecutive valid windows
#define DF_ZERO_TOL_KPA      2.0f         // zero-check tolerance

// ---- Transmitter ---------------------------------------------------------
#define DF_TX_FS_KPA         600.0f
#define DF_TX_V_ZERO         0.5f         // V at 0 kPa @ 5.0 V excitation
#define DF_TX_V_FS           4.5f         // V at FS  @ 5.0 V excitation

// ---- Battery thresholds (Phase 6 §2) -------------------------------------
#define DF_VBAT_ALERT_V      3.45f
#define DF_VBAT_SHUTDOWN_V   3.35f

// ---- Pins (ESP32-WROOM-32, bare module) ----------------------------------
// I2C (ADS1115 @ 5 V via BSS138 level shifter; DS3231)
#define DF_PIN_SDA           21
#define DF_PIN_SCL           22
// microSD (SPI, native 3.3 V, switched supply)
#define DF_PIN_SD_CS         5
#define DF_PIN_SD_MOSI       23
#define DF_PIN_SD_MISO       19
#define DF_PIN_SD_SCK        18
#define DF_PIN_SD_PWR        27           // load switch: SD supply
// Switched 5 V boost enable (transmitters + ADS1115 + LCD + buzzer)
#define DF_PIN_5V_EN         26
// DS18B20 water temperature
#define DF_PIN_ONEWIRE       4
// Local signalling
#define DF_PIN_LED_R         32
#define DF_PIN_LED_G         33
#define DF_PIN_LED_B         25
#define DF_PIN_BUZZER        13
// Buttons (commissioning / cleaning confirm / zero check / ack)
#define DF_PIN_BTN_A         34           // input-only pins: external pull-ups
#define DF_PIN_BTN_B         35
// Battery sense (divider to ADC1 — monitoring only, NOT the measurement chain)
#define DF_PIN_VBAT          36

// ---- I2C addresses --------------------------------------------------------
#define DF_ADDR_ADS1115      0x48
#define DF_ADDR_DS3231       0x68
#define DF_ADDR_LCD          0x27         // PCF8574 backpack, if fitted

// ---- Log schema -----------------------------------------------------------
#define DF_LOG_SCHEMA        1
#define DF_FW_VERSION        "0.1.0"
