// ============================================================================
// DeltaFiltre — firmware v0.1.0 (ESP32-WROOM-32, Arduino framework)
//
// FIRST IMPLEMENTATION — NOT BENCH-TESTED. No physical prototype exists yet.
// Gate G0 (written supplier confirmation of transmitter overpressure rating)
// must be passed before any hardware is purchased or assembled.
//
// Behaviour (docs/06-method.md, docs/02-architecture.md):
//   - Wake every 60 s, power the switched 5 V rail, burst-sample the two
//     pressure transmitters + the excitation rail through the ADS1115.
//   - Per-minute sample = median of the burst; logged aggregate = median
//     over a 5-minute window of per-sample dP values.
//   - Baseline-relative alarm (delta = 20 kPa default, persistence 3 valid
//     windows, hysteresis 5 kPa). Alarm-only: NO actuation output exists.
//   - Full time series appended to microSD as CSV (schema v1).
//   - Deep sleep between bursts; rails (5 V, SD) are switched off in sleep.
//
// Hardware-independent logic lives in src/core/ and is unit-tested natively
// (firmware/test/test_core.cpp). This file is only wiring + drivers.
// ============================================================================
#include <Arduino.h>
#include <Wire.h>
#include <SPI.h>
#include <SD.h>
#include <Preferences.h>
#include <esp_sleep.h>

#include "config.h"
#include "core/flags.h"
#include "core/median.h"
#include "core/pressure_conv.h"
#include "core/flow_model.h"
#include "core/baseline.h"
#include "core/alarm.h"
#include "core/zero_check.h"
#include "core/window.h"

using namespace df;

// ---------------------------------------------------------------------------
// Persistent state
// ---------------------------------------------------------------------------
static Preferences prefs;
static AlarmConfig alarm_cfg{DF_DELTA_DEFAULT_KPA, DF_HYSTERESIS_KPA, DF_PERSISTENCE};
static AlarmFsm alarm_fsm(alarm_cfg);
static Baseline baseline;
static ZeroCheck zero_check;
static FlowModel flow_model;

// State kept across deep sleep in RTC memory.
RTC_DATA_ATTR static float rtc_up[Window::kMaxSamples];
RTC_DATA_ATTR static float rtc_down[Window::kMaxSamples];
RTC_DATA_ATTR static int rtc_count = 0;
RTC_DATA_ATTR static uint32_t rtc_seq = 0;
RTC_DATA_ATTR static uint32_t rtc_boot = 0;
RTC_DATA_ATTR static int64_t rtc_last_epoch = 0;
RTC_DATA_ATTR static bool rtc_have_pending = false;
RTC_DATA_ATTR static float rtc_pending_dp = 0.0f;  // buffered aggregate if SD failed

// ---------------------------------------------------------------------------
// ADS1115 — minimal register driver (single-shot conversions).
// Powered at 5 V; I2C through a BSS138 level shifter (design §2).
// PGA = +/-6.144 V (design decision: 4.096 V range would saturate).
// ---------------------------------------------------------------------------
static bool ads_write(uint8_t reg, uint16_t val) {
  Wire.beginTransmission(DF_ADDR_ADS1115);
  Wire.write(reg);
  Wire.write((uint8_t)(val >> 8));
  Wire.write((uint8_t)(val & 0xFF));
  return Wire.endTransmission() == 0;
}

static bool ads_read_reg(uint8_t reg, uint16_t& val) {
  Wire.beginTransmission(DF_ADDR_ADS1115);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom(DF_ADDR_ADS1115, 2) != 2) return false;
  val = ((uint16_t)Wire.read() << 8) | Wire.read();
  return true;
}

// Single-shot conversion on mux channel (0..3). Returns volts, or NAN.
static float ads_read_volts(uint8_t channel) {
  // OS=1 (start), MUX=100+channel (AINx vs GND), PGA=000 (+/-6.144 V),
  // MODE=1 (single-shot), DR=100 (128 SPS), comparator disabled.
  uint16_t cfg = 0x8000 | ((uint16_t)(4 + channel) << 12) | 0x0000 | 0x0100 |
                 0x0080 | 0x0003;
  if (!ads_write(0x01, cfg)) return NAN;
  uint16_t status = 0;
  for (int i = 0; i < 20; ++i) {  // wait for OS bit = conversion done
    if (!ads_read_reg(0x01, status)) return NAN;
    if (status & 0x8000) break;
    delay(2);
  }
  uint16_t raw = 0;
  if (!ads_read_reg(0x00, raw)) return NAN;
  return (int16_t)raw * 6.144f / 32768.0f;
}

// ---------------------------------------------------------------------------
// DS3231 RTC — read epoch seconds (UTC). Time is set at commissioning.
// ---------------------------------------------------------------------------
static uint8_t bcd2bin(uint8_t v) { return v - 6 * (v >> 4); }

static bool rtc_read_epoch(int64_t& epoch_out) {
  Wire.beginTransmission(DF_ADDR_DS3231);
  Wire.write(0x00);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom(DF_ADDR_DS3231, 7) != 7) return false;
  int sec = bcd2bin(Wire.read() & 0x7F);
  int min = bcd2bin(Wire.read());
  int hour = bcd2bin(Wire.read() & 0x3F);
  Wire.read();  // day of week
  int day = bcd2bin(Wire.read());
  int month = bcd2bin(Wire.read() & 0x1F);
  int year = 2000 + bcd2bin(Wire.read());
  // Days since 1970-01-01 (civil algorithm, public domain — H. Hinnant).
  int64_t y = year - (month <= 2);
  int64_t era = (y >= 0 ? y : y - 399) / 400;
  int64_t yoe = y - era * 400;
  int64_t doy = (153 * (month + (month > 2 ? -3 : 9)) + 2) / 5 + day - 1;
  int64_t doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
  int64_t days = era * 146097 + doe - 719468;
  epoch_out = days * 86400 + hour * 3600 + min * 60 + sec;
  return true;
}

static void epoch_to_iso(int64_t epoch, char* buf, size_t len) {
  int64_t days = epoch / 86400, rem = epoch % 86400;
  if (rem < 0) { rem += 86400; --days; }
  int64_t z = days + 719468;
  int64_t era = (z >= 0 ? z : z - 146096) / 146097;
  int64_t doe = z - era * 146097;
  int64_t yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
  int64_t y = yoe + era * 400;
  int64_t doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
  int64_t mp = (5 * doy + 2) / 153;
  int d = (int)(doy - (153 * mp + 2) / 5 + 1);
  int m = (int)(mp + (mp < 10 ? 3 : -9));
  int yr = (int)(y + (m <= 2));
  snprintf(buf, len, "%04d-%02d-%02dT%02d:%02d:%02dZ", yr, m, d,
           (int)(rem / 3600), (int)((rem % 3600) / 60), (int)(rem % 60));
}

// ---------------------------------------------------------------------------
// DS18B20 — minimal 1-Wire. Conversion is requested at the end of a burst
// and read at the next burst (750 ms conversion fits easily in 60 s), per
// the Phase 6 harmonization: one temperature value per 5-minute aggregate.
// ---------------------------------------------------------------------------
static bool ow_reset() {
  pinMode(DF_PIN_ONEWIRE, OUTPUT);
  digitalWrite(DF_PIN_ONEWIRE, LOW);
  delayMicroseconds(480);
  pinMode(DF_PIN_ONEWIRE, INPUT);
  delayMicroseconds(70);
  bool present = digitalRead(DF_PIN_ONEWIRE) == LOW;
  delayMicroseconds(410);
  return present;
}
static void ow_write_byte(uint8_t b) {
  for (int i = 0; i < 8; ++i) {
    pinMode(DF_PIN_ONEWIRE, OUTPUT);
    digitalWrite(DF_PIN_ONEWIRE, LOW);
    if (b & 1) { delayMicroseconds(6); pinMode(DF_PIN_ONEWIRE, INPUT); delayMicroseconds(64); }
    else { delayMicroseconds(60); pinMode(DF_PIN_ONEWIRE, INPUT); delayMicroseconds(10); }
    b >>= 1;
  }
}
static uint8_t ow_read_byte() {
  uint8_t b = 0;
  for (int i = 0; i < 8; ++i) {
    pinMode(DF_PIN_ONEWIRE, OUTPUT);
    digitalWrite(DF_PIN_ONEWIRE, LOW);
    delayMicroseconds(6);
    pinMode(DF_PIN_ONEWIRE, INPUT);
    delayMicroseconds(9);
    if (digitalRead(DF_PIN_ONEWIRE)) b |= (1u << i);
    delayMicroseconds(55);
  }
  return b;
}
static float ds18b20_read_c() {  // reads the conversion requested last burst
  if (!ow_reset()) return NAN;
  ow_write_byte(0xCC);  // SKIP ROM (single device on the bus)
  ow_write_byte(0xBE);  // READ SCRATCHPAD
  uint8_t lo = ow_read_byte(), hi = ow_read_byte();
  int16_t raw = ((int16_t)hi << 8) | lo;
  return raw * 0.0625f;
}
static void ds18b20_start_conversion() {
  if (!ow_reset()) return;
  ow_write_byte(0xCC);
  ow_write_byte(0x44);  // CONVERT T
}

// ---------------------------------------------------------------------------
// Signalling: tricolor LED + buzzer (local only — the product has no
// actuation output of any kind, spec EF-22).
// ---------------------------------------------------------------------------
static void set_led(bool r, bool g, bool b) {
  digitalWrite(DF_PIN_LED_R, r ? HIGH : LOW);
  digitalWrite(DF_PIN_LED_G, g ? HIGH : LOW);
  digitalWrite(DF_PIN_LED_B, b ? HIGH : LOW);
}
static void signal_state(AlarmState s, bool drift_warn) {
  if (drift_warn) { set_led(true, true, false); return; }   // amber: sensor warning
  switch (s) {
    case AlarmState::ALARM: set_led(true, false, false); break;
    case AlarmState::PENDING: set_led(true, true, false); break;
    default: set_led(false, true, false); break;            // green: normal
  }
}

// ---------------------------------------------------------------------------
// SD logging — open/append/flush/close per record (docs/04-data-format.md).
// ---------------------------------------------------------------------------
static bool sd_append_line(const char* line) {
  digitalWrite(DF_PIN_SD_PWR, HIGH);
  delay(10);
  bool ok = false;
  if (SD.begin(DF_PIN_SD_CS)) {
    char path[24];
    int64_t ep;
    if (rtc_read_epoch(ep)) {
      char iso[24];
      epoch_to_iso(ep, iso, sizeof(iso));
      snprintf(path, sizeof(path), "/DF-%.4s-%.2s.csv", iso, iso + 5);
    } else {
      snprintf(path, sizeof(path), "/DF-unknown.csv");
    }
    File f = SD.open(path, FILE_APPEND);
    if (f) {
      if (f.size() == 0) {
        f.printf("# deltafiltre-log schema=%d fw=%s\n", DF_LOG_SCHEMA, DF_FW_VERSION);
        f.println("seq,boot,ts_iso8601,p_up_kpa,p_down_kpa,dp_kpa,t_water_c,"
                  "dp_norm_kpa,excess_kpa,baseline_kpa,alarm_state,vbat_v,flags");
      }
      f.print(line);
      f.flush();
      f.close();
      ok = true;
    }
    SD.end();
  }
  digitalWrite(DF_PIN_SD_PWR, LOW);
  return ok;
}

// ---------------------------------------------------------------------------
// Config persistence (NVS): baseline, flow model, alarm delta, zero state.
// ---------------------------------------------------------------------------
static void load_state() {
  prefs.begin("deltafiltre", true);
  baseline.b0_kpa = prefs.getFloat("b0", 0.0f);
  baseline.bn_kpa = prefs.getFloat("bn", 0.0f);
  baseline.cleaning_count = prefs.getInt("nclean", 0);
  baseline.captured = prefs.getBool("bcapt", false);
  flow_model.k = prefs.getFloat("fk", 0.0f);
  flow_model.n = prefs.getFloat("fn", 0.0f);
  flow_model.q_ref = prefs.getFloat("fqref", 0.0f);
  flow_model.valid = prefs.getBool("fvalid", false);
  alarm_cfg.delta_kpa = prefs.getFloat("delta", DF_DELTA_DEFAULT_KPA);
  zero_check.valid = prefs.getBool("zvalid", false);
  zero_check.drift_suspected = prefs.getBool("zdrift", false);
  zero_check.last_dp_zero_kpa = prefs.getFloat("zdp", 0.0f);
  prefs.end();
  alarm_fsm = AlarmFsm(alarm_cfg);
}
static void save_state() {
  prefs.begin("deltafiltre", false);
  prefs.putFloat("b0", baseline.b0_kpa);
  prefs.putFloat("bn", baseline.bn_kpa);
  prefs.putInt("nclean", baseline.cleaning_count);
  prefs.putBool("bcapt", baseline.captured);
  prefs.putFloat("fk", flow_model.k);
  prefs.putFloat("fn", flow_model.n);
  prefs.putFloat("fqref", flow_model.q_ref);
  prefs.putBool("fvalid", flow_model.valid);
  prefs.putFloat("delta", alarm_cfg.delta_kpa);
  prefs.putBool("zvalid", zero_check.valid);
  prefs.putBool("zdrift", zero_check.drift_suspected);
  prefs.putFloat("zdp", zero_check.last_dp_zero_kpa);
  prefs.end();
}

// ---------------------------------------------------------------------------
// One burst: sample, accumulate, and every 5th burst close the window.
// ---------------------------------------------------------------------------
static void run_burst() {
  // Power the measurement rail; respect transmitter warm-up.
  digitalWrite(DF_PIN_5V_EN, HIGH);
  delay(120);

  TransmitterSpec spec{DF_TX_V_ZERO, DF_TX_V_FS, DF_TX_FS_KPA, 5.0f};
  Median<DF_BURST_SAMPLES> b_up, b_down;
  uint16_t flags = FLAG_NONE;
  float v_exc = ads_read_volts(3);  // AIN3: excitation rail (ratiometric ref)
  for (int i = 0; i < DF_BURST_SAMPLES; ++i) {
    float v_up = ads_read_volts(0);
    float v_dn = ads_read_volts(1);
    if (!isnan(v_up)) b_up.push(voltage_to_kpa(spec, v_up, v_exc, flags));
    if (!isnan(v_dn)) b_down.push(voltage_to_kpa(spec, v_dn, v_exc, flags));
  }
  float t_water = ds18b20_read_c();   // conversion requested at previous burst
  ds18b20_start_conversion();         // start the next one
  digitalWrite(DF_PIN_5V_EN, LOW);

  if (b_up.empty() || b_down.empty()) return;  // sensor read failure: skip
  if (rtc_count < (int)Window::kMaxSamples) {
    rtc_up[rtc_count] = b_up.median();
    rtc_down[rtc_count] = b_down.median();
    ++rtc_count;
  }
  if (rtc_count < DF_WINDOW_MINUTES) return;  // window not complete yet

  // ---- Close the 5-minute window ------------------------------------------
  Window w;
  for (int i = 0; i < rtc_count; ++i) w.push_sample(rtc_up[i], rtc_down[i]);
  rtc_count = 0;
  WindowAggregate agg = w.aggregate(isnan(t_water) ? 0.0f : t_water);

  int64_t epoch = 0;
  bool have_time = rtc_read_epoch(epoch);
  if (have_time && rtc_last_epoch > 0 && epoch < rtc_last_epoch) flags |= FLAG_TIME_JUMP;
  if (have_time) rtc_last_epoch = epoch;

  // Flow-state proxy (v1 limitation, documented in docs/06-method.md §2):
  // with no flow sensor, a window counts as flowing when the downstream
  // pressure is meaningfully above static-zero. Invalid windows never feed
  // the alarm persistence counter.
  bool valid = agg.p_down_kpa > 5.0f;
  if (!valid) flags |= FLAG_NO_FLOW;
  if (!zero_check.valid || zero_check.drift_suspected) flags |= FLAG_ZERO_UNVERIFIED;
  if (zero_check.drift_suspected) flags |= FLAG_SENSOR_DRIFT;

  float dp_norm = agg.dp_kpa;  // no live Q estimate in v1: regime-windowed compare
  float excess = baseline.captured ? baseline.excess(dp_norm) : 0.0f;
  AlarmState st = baseline.captured ? alarm_fsm.update(excess, valid)
                                    : AlarmState::OK;

  float vbat = analogRead(DF_PIN_VBAT) * (3.3f / 4095.0f) * 2.0f;  // divider x2
  if (vbat > 0.5f && vbat < DF_VBAT_ALERT_V) flags |= FLAG_LOW_BATT;

  char iso[24] = "";
  if (have_time) epoch_to_iso(epoch, iso, sizeof(iso));
  const char* st_txt = st == AlarmState::ALARM ? "ALARM"
                       : st == AlarmState::PENDING ? "PENDING" : "OK";
  char line[256];
  snprintf(line, sizeof(line),
           "%lu,%lu,%s,%.2f,%.2f,%.2f,%.1f,%.2f,%.2f,%.2f,%s,%.2f,%u\n",
           (unsigned long)++rtc_seq, (unsigned long)rtc_boot, iso,
           agg.p_up_kpa, agg.p_down_kpa, agg.dp_kpa, agg.t_water_c, dp_norm,
           excess, baseline.bn_kpa, st_txt, vbat, (unsigned)flags);
  if (!sd_append_line(line)) {
    rtc_have_pending = true;   // keep last dP for the FAULT indication
    rtc_pending_dp = agg.dp_kpa;
  }
  signal_state(st, zero_check.drift_suspected);
  if (st == AlarmState::ALARM) {  // short audible signal at alarm onset windows
    digitalWrite(DF_PIN_BUZZER, HIGH);
    delay(150);
    digitalWrite(DF_PIN_BUZZER, LOW);
  }
  if (vbat > 0.5f && vbat < DF_VBAT_SHUTDOWN_V) {
    // Clean shutdown above the protection board's last-resort cutoff.
    esp_sleep_disable_wakeup_source(ESP_SLEEP_WAKEUP_ALL);
    esp_deep_sleep_start();
  }
}

void setup() {
  ++rtc_boot;
  pinMode(DF_PIN_5V_EN, OUTPUT);
  pinMode(DF_PIN_SD_PWR, OUTPUT);
  pinMode(DF_PIN_LED_R, OUTPUT);
  pinMode(DF_PIN_LED_G, OUTPUT);
  pinMode(DF_PIN_LED_B, OUTPUT);
  pinMode(DF_PIN_BUZZER, OUTPUT);
  digitalWrite(DF_PIN_5V_EN, LOW);
  digitalWrite(DF_PIN_SD_PWR, LOW);
  Wire.begin(DF_PIN_SDA, DF_PIN_SCL);
  SPI.begin(DF_PIN_SD_SCK, DF_PIN_SD_MISO, DF_PIN_SD_MOSI, DF_PIN_SD_CS);
  load_state();
  run_burst();
  // Sleep until the next minute boundary burst.
  esp_sleep_enable_timer_wakeup(DF_BURST_PERIOD_US);
  esp_light_sleep_start();   // light sleep in v0.1; deep-sleep current work
                             // is a Phase 6 power-budget item (bare module,
                             // switched rails) before any autonomy claim.
  esp_sleep_disable_wakeup_source(ESP_SLEEP_WAKEUP_TIMER);
}

void loop() {
  run_burst();
  esp_sleep_enable_timer_wakeup(DF_BURST_PERIOD_US);
  esp_light_sleep_start();
  esp_sleep_disable_wakeup_source(ESP_SLEEP_WAKEUP_TIMER);
}
