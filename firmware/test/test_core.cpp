// DeltaFiltre — native unit tests for the hardware-independent core.
// These tests exercise LOGIC ONLY, on synthetic values. They say nothing
// about measurement performance (no physical test has been performed).
// Build & run without PlatformIO:
//   g++ -std=c++17 -I firmware/src firmware/test/test_core.cpp -o /tmp/df_test && /tmp/df_test
#include <cassert>
#include <cmath>
#include <cstdio>

#include "core/median.h"
#include "core/flow_model.h"
#include "core/alarm.h"
#include "core/baseline.h"
#include "core/zero_check.h"
#include "core/pressure_conv.h"
#include "core/window.h"

static bool near(float a, float b, float eps) { return std::fabs(a - b) <= eps; }

int main() {
  using namespace df;

  // --- Median: transients are rejected -------------------------------------
  {
    Median<8> m;
    m.push(100.0f); m.push(101.0f); m.push(250.0f);  // 250 = hydraulic spike
    m.push(99.0f);  m.push(100.5f);
    assert(near(m.median(), 100.5f, 0.01f));  // sorted {99,100,100.5,101,250}: spike rejected
  }

  // --- Pressure conversion: ratiometric correction --------------------------
  {
    TransmitterSpec spec;  // 0.5-4.5 V over 0-600 kPa @ 5.0 V
    uint16_t flags = 0;
    // At nominal excitation, 2.5 V -> (2.5-0.5)/4 * 600 = 300 kPa
    assert(near(voltage_to_kpa(spec, 2.5f, 5.0f, flags), 300.0f, 0.5f));
    assert(!(flags & FLAG_SENSOR_OOR));
    // Excitation sags to 4.5 V: same physical 300 kPa now reads 2.25 V raw;
    // the ratiometric correction must still return ~300 kPa.
    flags = 0;
    assert(near(voltage_to_kpa(spec, 2.25f, 4.5f, flags), 300.0f, 0.5f));
    // Broken wire: signal at rail bottom -> out-of-range flag.
    flags = 0;
    (void)voltage_to_kpa(spec, 0.02f, 5.0f, flags);
    assert(flags & FLAG_SENSOR_OOR);
  }

  // --- Flow model: exact synthetic law dP = 2.0 * Q^1.8 ---------------------
  {
    const float q[3] = {10.0f, 20.0f, 30.0f};
    float dp[3];
    for (int i = 0; i < 3; ++i) dp[i] = 2.0f * std::pow(q[i], 1.8f);
    FlowModel model;
    assert(fit_flow_model(q, dp, 3, model));
    assert(near(model.n, 1.8f, 0.01f));
    assert(near(model.k, 2.0f, 0.05f));
    model.q_ref = 20.0f;
    // A measurement at Q=30 normalized back to Q_ref=20 must equal the
    // clean-filter dP at 20.
    assert(near(normalize_dp(model, dp[2], 30.0f), dp[1], 0.5f));
    // Degenerate input: identical flows cannot identify n.
    const float qbad[2] = {15.0f, 15.0f};
    const float dpbad[2] = {100.0f, 101.0f};
    FlowModel bad;
    assert(!fit_flow_model(qbad, dpbad, 2, bad));
  }

  // --- Alarm FSM: persistence + hysteresis + invalid windows ----------------
  {
    AlarmConfig cfg;  // delta 20, h 5, persistence 3
    AlarmFsm fsm(cfg);
    assert(fsm.update(10.0f, true) == AlarmState::OK);
    assert(fsm.update(25.0f, true) == AlarmState::PENDING);
    assert(fsm.update(25.0f, false) == AlarmState::PENDING);  // invalid: frozen
    assert(fsm.update(25.0f, true) == AlarmState::PENDING);
    assert(fsm.update(25.0f, true) == AlarmState::ALARM);     // 3rd valid window
    assert(fsm.update(18.0f, true) == AlarmState::ALARM);     // inside hysteresis band
    assert(fsm.update(14.9f, true) == AlarmState::OK);        // below delta - h
  }

  // --- Baseline: recovery ratio ---------------------------------------------
  {
    Baseline b;
    b.capture_initial(50.0f);
    assert(near(b.excess(70.0f), 20.0f, 0.01f));
    float rn = b.capture_after_cleaning(55.0f);
    assert(near(rn, 1.10f, 0.001f));  // cleaning recovered less than new: r_n > 1
    assert(b.cleaning_count == 1);
  }

  // --- Zero check -------------------------------------------------------------
  {
    ZeroCheck z;  // tolerance 2 kPa
    assert(z.record(1.2f));           // within tolerance
    assert(!z.drift_suspected);
    assert(!z.record(3.5f));          // exceeds tolerance
    assert(z.drift_suspected);
  }

  // --- Window: median of per-sample differences -------------------------------
  {
    Window w;
    for (int i = 0; i < 5; ++i) w.push_sample(300.0f + i, 250.0f);
    assert(w.ready());
    WindowAggregate a = w.aggregate(21.5f);
    assert(near(a.dp_kpa, 52.0f, 0.01f));  // median of {50,51,52,53,54}
  }

  std::printf("ALL CORE TESTS PASSED\n");
  return 0;
}
