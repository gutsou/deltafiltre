// DeltaFiltre — 5-minute window aggregation (docs/06-method.md §7).
// Per minute, the firmware takes a burst of conversions and stores one
// per-sample dP. The window aggregate logged to SD is the MEDIAN of the
// per-sample dP values (not the difference of the medians), plus medians
// of P_up / P_down. Validity is decided by the caller (flow state).
#pragma once
#include "median.h"

namespace df {

struct WindowAggregate {
  float p_up_kpa = 0.0f;
  float p_down_kpa = 0.0f;
  float dp_kpa = 0.0f;      // median of per-sample differences
  float t_water_c = 0.0f;   // single conversion per window (slow variable)
  int samples = 0;
};

class Window {
 public:
  static constexpr size_t kMaxSamples = 10;  // 1 per minute over 5 minutes, headroom x2

  void reset() { up_.reset(); down_.reset(); dp_.reset(); }
  void push_sample(float p_up, float p_down) {
    up_.push(p_up);
    down_.push(p_down);
    dp_.push(p_up - p_down);
  }
  bool ready() const { return dp_.size() >= 5; }  // a full 5-minute window
  WindowAggregate aggregate(float t_water_c) const {
    WindowAggregate a;
    a.p_up_kpa = up_.median();
    a.p_down_kpa = down_.median();
    a.dp_kpa = dp_.median();
    a.t_water_c = t_water_c;
    a.samples = static_cast<int>(dp_.size());
    return a;
  }

 private:
  Median<kMaxSamples> up_, down_, dp_;
};

}  // namespace df
