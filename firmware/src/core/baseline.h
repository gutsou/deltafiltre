// DeltaFiltre — clean-filter baseline bookkeeping (docs/06-method.md §3).
// B_0 is captured at commissioning on the clean filter; B_n is re-captured
// after each user-confirmed cleaning. r_n = B_n / B_0 is a drift INDICATOR
// under validation — never a diagnosis (spec EF-15).
#pragma once

namespace df {

struct Baseline {
  float b0_kpa = 0.0f;   // initial clean baseline
  float bn_kpa = 0.0f;   // current baseline in force
  int cleaning_count = 0;
  bool captured = false;

  // Capture the commissioning baseline.
  void capture_initial(float dp_clean_kpa) {
    b0_kpa = dp_clean_kpa;
    bn_kpa = dp_clean_kpa;
    cleaning_count = 0;
    captured = true;
  }

  // Re-capture after a confirmed cleaning. Returns r_n (1.0 on first capture).
  float capture_after_cleaning(float dp_clean_kpa) {
    if (!captured) { capture_initial(dp_clean_kpa); return 1.0f; }
    bn_kpa = dp_clean_kpa;
    ++cleaning_count;
    return recovery_ratio();
  }

  float recovery_ratio() const {
    if (!captured || b0_kpa <= 0.0f) return 1.0f;
    return bn_kpa / b0_kpa;
  }

  // Excess of a normalized dP against the current baseline.
  float excess(float dp_norm_kpa) const { return dp_norm_kpa - bn_kpa; }
};

}  // namespace df
