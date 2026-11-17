// DeltaFiltre — fixed-size median over a sliding set of samples.
// No dynamic allocation. Used for: burst median (per minute) and the
// 5-minute window median of per-sample differences (docs/06-method.md §7).
#pragma once
#include <cstddef>
#include <cstdint>

namespace df {

template <size_t N>
class Median {
 public:
  void reset() { count_ = 0; }
  void push(float v) {
    if (count_ < N) values_[count_++] = v;
    // Window code guarantees count never exceeds N; extra pushes are dropped
    // deliberately rather than silently overwriting history.
  }
  size_t size() const { return count_; }
  bool empty() const { return count_ == 0; }

  // Median of the pushed values. For even counts, returns the lower-middle
  // value (documented choice: avoids inventing an interpolated sample).
  float median() const {
    if (count_ == 0) return 0.0f;
    float tmp[N];
    for (size_t i = 0; i < count_; ++i) tmp[i] = values_[i];
    // Insertion sort: N is small (<= 30) and this runs once per window.
    for (size_t i = 1; i < count_; ++i) {
      float key = tmp[i];
      size_t j = i;
      while (j > 0 && tmp[j - 1] > key) { tmp[j] = tmp[j - 1]; --j; }
      tmp[j] = key;
    }
    return tmp[(count_ - 1) / 2];
  }

 private:
  float values_[N];
  size_t count_ = 0;
};

}  // namespace df
