// DeltaFiltre — zero-equalization check (docs/06-method.md §5).
// With the equalization valve open, pump stopped, both transmitters see one
// static body of water at the same elevation: true dP at the sensors is 0.
// Any measured dP is the sum of the two transmitters' zero errors.
// This check detects OFFSET only — never span (sensitivity) drift.
#pragma once
#include <cmath>

namespace df {

struct ZeroCheck {
  float tolerance_kpa = 2.0f;  // default, coherent with U(E) ~ +/-1.6 kPa
  bool valid = false;          // a check has been performed at least once
  bool drift_suspected = false;
  float last_dp_zero_kpa = 0.0f;

  // Record a check performed with measured residual dP (median over the
  // equalized window). Returns true when within tolerance.
  bool record(float dp_zero_kpa) {
    last_dp_zero_kpa = dp_zero_kpa;
    valid = true;
    drift_suspected = std::fabs(dp_zero_kpa) > tolerance_kpa;
    return !drift_suspected;
  }
};

}  // namespace df
