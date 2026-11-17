// DeltaFiltre — transmitter voltage -> pressure, ratiometric.
// Transmitter: 0.5-4.5 V output for 0-600 kPa at a nominal 5.0 V excitation.
// The ADS1115 has an internal reference, so readings are NOT ratiometric by
// themselves: the firmware measures the actual excitation rail on AIN3 and
// corrects (docs/02-architecture.md §2). Plausibility band 4-96% of span
// flags a suspected broken wire (FLAG_SENSOR_OOR).
#pragma once
#include <cstdint>
#include "flags.h"

namespace df {

struct TransmitterSpec {
  float v_at_zero = 0.5f;    // V at 0 kPa, at nominal excitation
  float v_at_fs = 4.5f;      // V at full scale, at nominal excitation
  float fs_kpa = 600.0f;     // full-scale pressure
  float v_exc_nominal = 5.0f;
};

// Convert one channel. `v_sig` and `v_exc` are ADS1115 readings in volts.
// Returns pressure in kPa; sets FLAG_SENSOR_OOR in `flags` when the raw
// signal sits outside the plausible 4-96% band of the output span.
inline float voltage_to_kpa(const TransmitterSpec& spec, float v_sig, float v_exc,
                            uint16_t& flags) {
  const float exc = (v_exc > 0.1f) ? v_exc : spec.v_exc_nominal;
  const float ratio = exc / spec.v_exc_nominal;      // excitation deviation
  const float v0 = spec.v_at_zero * ratio;           // ratiometric zero
  const float vfs = spec.v_at_fs * ratio;            // ratiometric full scale
  const float frac = (v_sig - v0) / (vfs - v0);
  if (frac < 0.04f || frac > 0.96f) flags |= FLAG_SENSOR_OOR;
  return frac * spec.fs_kpa;
}

}  // namespace df
