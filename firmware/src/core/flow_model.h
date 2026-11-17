// DeltaFiltre — clean-filter law dP = k * Q^n and flow normalization.
// Fit at commissioning from volumetric points (graduated container +
// stopwatch), by least squares in log-log space (docs/06-method.md §2).
#pragma once
#include <cmath>
#include <cstddef>

namespace df {

struct FlowModel {
  float k = 0.0f;      // dP = k * Q^n   (dP in kPa, Q in the user's units)
  float n = 0.0f;      // exponent, typically ~1.7-2.0 for filter heads
  float q_ref = 0.0f;  // reference flow fixed at commissioning
  bool valid = false;
};

// Fit (k, n) from m >= 2 points (Q_i, dP_i), all strictly positive.
// Returns false (and leaves `out` invalid) on degenerate input.
inline bool fit_flow_model(const float* q, const float* dp, size_t m, FlowModel& out) {
  out = FlowModel{};
  if (m < 2) return false;
  double sx = 0, sy = 0, sxx = 0, sxy = 0;
  for (size_t i = 0; i < m; ++i) {
    if (q[i] <= 0.0f || dp[i] <= 0.0f) return false;
    const double x = std::log(static_cast<double>(q[i]));
    const double y = std::log(static_cast<double>(dp[i]));
    sx += x; sy += y; sxx += x * x; sxy += x * y;
  }
  const double denom = static_cast<double>(m) * sxx - sx * sx;
  if (denom == 0.0) return false;  // all Q identical: n is not identifiable
  const double n = (static_cast<double>(m) * sxy - sx * sy) / denom;
  const double lnk = (sy - n * sx) / static_cast<double>(m);
  out.n = static_cast<float>(n);
  out.k = static_cast<float>(std::exp(lnk));
  out.valid = true;
  return true;
}

// Normalize a measured dP taken at flow q_meas to the reference flow.
inline float normalize_dp(const FlowModel& model, float dp_meas, float q_meas) {
  if (!model.valid || q_meas <= 0.0f || model.q_ref <= 0.0f) return dp_meas;
  return dp_meas * std::pow(model.q_ref / q_meas, model.n);
}

// Predicted clean-filter dP at a given flow (used at baseline capture).
inline float predict_dp(const FlowModel& model, float q) {
  if (!model.valid || q <= 0.0f) return 0.0f;
  return model.k * std::pow(q, model.n);
}

}  // namespace df
